"""YouTube access for the truth pipeline. Runs on the server only, so the API key never
reaches the browser or the mobile app."""
import logging
import random
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set
from urllib.parse import parse_qs, urlparse

import httpx

from app.core import config

logger = logging.getLogger(__name__)

API = "https://www.googleapis.com/youtube/v3"
_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


class YouTubeError(Exception):
    pass


@dataclass
class TranscriptSegment:
    start: float
    text: str


@dataclass
class VideoMeta:
    video_id: str
    title: str
    channel_title: str
    published_at: str = ""
    duration_seconds: int = 0
    view_count: Optional[int] = None
    thumbnail_url: str = ""
    description: str = ""


@dataclass
class Transcript:
    source: str  # YOUTUBE_CAPTIONS | WHISPER | MANUAL
    segments: List[TranscriptSegment] = field(default_factory=list)


def parse_video_id(url_or_id: str) -> str:
    """Accepts watch URLs, youtu.be links, shorts/embed/live URLs or a bare 11-char ID."""
    value = (url_or_id or "").strip()
    if _ID_RE.match(value):
        return value
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = (parsed.hostname or "").lower()
    if host.endswith("youtu.be"):
        candidate = parsed.path.lstrip("/").split("/")[0]
    elif "youtube" in host:
        candidate = parse_qs(parsed.query).get("v", [""])[0]
        if not candidate:
            parts = [p for p in parsed.path.split("/") if p]
            if len(parts) >= 2 and parts[0] in ("shorts", "embed", "live", "v"):
                candidate = parts[1]
    else:
        candidate = ""
    if not _ID_RE.match(candidate or ""):
        raise YouTubeError("That doesn't look like a YouTube video link.")
    return candidate


def _iso_duration_to_seconds(value: str) -> int:
    m = re.match(r"P(?:(\d+)D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", value or "")
    if not m:
        return 0
    d, h, mi, s = (int(x) if x else 0 for x in m.groups())
    return d * 86400 + h * 3600 + mi * 60 + s


def has_api_key() -> bool:
    return bool(config.YOUTUBE_API_KEY)


def fetch_metadata(video_id: str) -> Optional[VideoMeta]:
    if not has_api_key():
        return None
    res = httpx.get(f"{API}/videos", params={
        "part": "snippet,contentDetails,statistics", "id": video_id, "key": config.YOUTUBE_API_KEY,
    }, timeout=15)
    if res.status_code != 200:
        raise YouTubeError(f"YouTube API error {res.status_code}: {res.text[:200]}")
    items = res.json().get("items", [])
    if not items:
        raise YouTubeError("Video not found or it is private.")
    item = items[0]
    sn, stats = item["snippet"], item.get("statistics", {})
    thumbs = sn.get("thumbnails", {})
    thumb = (thumbs.get("high") or thumbs.get("medium") or thumbs.get("default") or {}).get("url", "")
    return VideoMeta(
        video_id=video_id,
        title=sn.get("title", ""),
        channel_title=sn.get("channelTitle", ""),
        published_at=sn.get("publishedAt", ""),
        duration_seconds=_iso_duration_to_seconds(item.get("contentDetails", {}).get("duration", "")),
        view_count=int(stats["viewCount"]) if stats.get("viewCount") else None,
        thumbnail_url=thumb,
        description=sn.get("description", ""),
    )


def sample_comments(video_id: str, limit: int, pool_max: int, seed: Optional[str] = None) -> List[Dict]:
    """A cross-section over time: 40% newest, 40% oldest, 20% random from the middle.

    Reads up to `pool_max` comments newest-first to reach the oldest ones. If the video has more than
    that, "oldest" means the oldest within the pool. The middle pick is random on every run
    (pass a seed to make it repeatable, e.g. in tests).
    """
    pool = fetch_comments(video_id, max(limit, pool_max), order="time")
    return pick_spread(pool, limit, seed)


def pick_spread(pool: List[Dict], limit: int, seed: Optional[str] = None) -> List[Dict]:
    """pool is newest first. Returns up to `limit` comments: newest, oldest and a random middle."""
    if len(pool) <= limit:
        return pool
    n_new = n_old = round(limit * 0.4)
    n_mid = limit - n_new - n_old
    newest, oldest, middle = pool[:n_new], pool[-n_old:], pool[n_new:-n_old]
    picked = random.Random(seed).sample(middle, min(n_mid, len(middle)))
    return newest + picked + oldest


def fetch_new_comments(video_id: str, known_ids: Set[str], limit: int) -> List[Dict]:
    """Comments posted since the last fetch, newest first. Pages through newest-first and stops at the
    first comment already stored, so a check costs one API unit per 100 comments."""
    return fetch_comments(video_id, limit, order="time", stop=lambda c: c["comment_id"] in known_ids)


def fetch_comments(video_id: str, limit: int, order: str = "relevance",
                   stop: Optional[Callable[[Dict], bool]] = None) -> List[Dict]:
    """Top-level comments, most relevant (or newest, order="time") first. Returns [] without an API key.
    `stop(comment)` returning True ends the read before that comment."""
    if not has_api_key():
        return []
    out: List[Dict] = []
    page_token = None
    while len(out) < limit:
        params = {"part": "snippet", "videoId": video_id, "maxResults": 100, "order": order,
                  "textFormat": "plainText", "key": config.YOUTUBE_API_KEY}
        if page_token:
            params["pageToken"] = page_token
        res = httpx.get(f"{API}/commentThreads", params=params, timeout=20)
        if res.status_code == 403 and "commentsDisabled" in res.text:
            break
        if res.status_code != 200:
            raise YouTubeError(f"YouTube comments error {res.status_code}: {res.text[:200]}")
        body = res.json()
        for item in body.get("items", []):
            top = item["snippet"]["topLevelComment"]
            sn = top["snippet"]
            comment = {
                "comment_id": top["id"],
                "author_channel_id": (sn.get("authorChannelId") or {}).get("value", sn.get("authorDisplayName", "")),
                "text": sn.get("textOriginal") or sn.get("textDisplay", ""),
                "likes": sn.get("likeCount", 0),
                "replies": item["snippet"].get("totalReplyCount", 0),
                "published_at": sn.get("publishedAt"),
            }
            if stop and stop(comment):
                return out[:limit]
            out.append(comment)
        page_token = body.get("nextPageToken")
        if not page_token:
            break
    return out[:limit]


def fetch_thread_replies(parent_comment_id: str, limit: int = 50) -> List[Dict]:
    """Replies under a comment. Used by the turnaround outcome check."""
    if not has_api_key():
        return []
    res = httpx.get(f"{API}/comments", params={
        "part": "snippet", "parentId": parent_comment_id, "maxResults": min(limit, 100),
        "textFormat": "plainText", "key": config.YOUTUBE_API_KEY,
    }, timeout=15)
    if res.status_code != 200:
        return []
    return [{
        "comment_id": it["id"],
        "author_channel_id": (it["snippet"].get("authorChannelId") or {}).get("value", ""),
        "text": it["snippet"].get("textOriginal", ""),
        "published_at": it["snippet"].get("publishedAt"),
    } for it in res.json().get("items", [])]


def fetch_transcript(video_id: str) -> Optional[Transcript]:
    """Captions first (fast, free). Falls back to Whisper when installed. None if neither works."""
    captions = _fetch_captions(video_id)
    if captions:
        return captions
    return _whisper_transcribe(video_id)


def _fetch_captions(video_id: str) -> Optional[Transcript]:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi  # type: ignore
    except ImportError:
        logger.info("youtube-transcript-api not installed; skipping captions")
        return None
    try:
        fetched = YouTubeTranscriptApi().fetch(video_id, languages=["en", "en-US", "en-GB", "hi"])
        segments = [TranscriptSegment(start=float(s.start), text=s.text.replace("\n", " ").strip())
                    for s in fetched if s.text.strip()]
        return Transcript(source="YOUTUBE_CAPTIONS", segments=segments) if segments else None
    except Exception as e:
        logger.info("No captions for %s: %s", video_id, e)
        return None


def _whisper_transcribe(video_id: str) -> Optional[Transcript]:
    """Optional: needs `yt-dlp` on PATH and the `faster-whisper` package."""
    if not shutil.which("yt-dlp"):
        return None
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except ImportError:
        return None
    with tempfile.TemporaryDirectory() as tmp:
        target = Path(tmp) / "audio.m4a"
        cmd = ["yt-dlp", "-f", "bestaudio[ext=m4a]/bestaudio", "-o", str(target), "--no-playlist",
               f"https://www.youtube.com/watch?v={video_id}"]
        if subprocess.run(cmd, capture_output=True, timeout=600).returncode != 0 or not target.exists():
            return None
        model = WhisperModel(config.WHISPER_MODEL, device="auto", compute_type="int8")
        segs, _ = model.transcribe(str(target), vad_filter=True)
        segments = [TranscriptSegment(start=float(s.start), text=s.text.strip()) for s in segs if s.text.strip()]
    return Transcript(source="WHISPER", segments=segments) if segments else None


def parse_manual_transcript(text: str) -> Transcript:
    """Pasted transcript. Lines may start with [mm:ss] / mm:ss / h:mm:ss timestamps."""
    segments: List[TranscriptSegment] = []
    ts_re = re.compile(r"^\[?(\d{1,2}:)?(\d{1,2}):(\d{2})\]?\s*[-–:]?\s*(.*)$")
    last = 0.0
    for raw in (text or "").splitlines():
        line = raw.strip()
        if not line:
            continue
        m = ts_re.match(line)
        if m:
            h = int(m.group(1)[:-1]) if m.group(1) else 0
            last = h * 3600 + int(m.group(2)) * 60 + int(m.group(3))
            line = m.group(4).strip()
            if not line:
                continue
        segments.append(TranscriptSegment(start=last, text=line))
    return Transcript(source="MANUAL", segments=segments)
