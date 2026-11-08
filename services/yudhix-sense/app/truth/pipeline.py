"""The "Analyze a video" job: the truth-first pipeline.

  1. FETCHING_VIDEO     video metadata (YouTube API, or oEmbed without a key)
  2. TRANSCRIBING       captions -> Whisper -> pasted transcript
  3. EXTRACTING_CLAIMS  atomic, timestamped claims
  4. FACT_CHECKING      retrieve brand knowledge + verdict per claim
  5. INGESTING_COMMENTS pull comments, mask PII, pseudonymize authors, classify
  6. UNDERSTANDING      sentiment, topics and claim reference per comment (AI first, rules fallback)
  7. ATTRIBUTING        link comments to claims, re-score impact and priority
  8. COMPLETED

Runs in a worker thread (FastAPI BackgroundTasks) and writes progress to
video_analysis_job, which the UI polls.

A "FACTS" job re-runs only step 4 on the stored claims against the current knowledge base
(after facts are added or removed), then re-links.

A second, quicker job kind ("COMMENTS") only fetches comments posted since the last check,
reads them with AI and re-links: the "Fetch new comments" button and the schedule use it.
"""
import hashlib
import hmac
import json
import logging
from collections import Counter
from datetime import datetime, timezone
from typing import Dict, List, Optional

import httpx

from app.core import config, llm
from app.core.database import append_audit, cursor, fetch_all, fetch_one
from app.core.text import format_timestamp
from app.db import DEFAULT_PRODUCT_ID, DEFAULT_SOURCE_ID, persist_comment_and_analysis
from app.pipeline.classifier import FastSentimentClassifier
from app.pipeline.masker import PiiMasker
from app.platform import billing
from app.platform.notifications import notify
from app.truth import attribution, audience, youtube
from app.truth.claims import extract_claims
from app.truth.retrieval import KnowledgeIndex
from app.truth.scoring import impact_score, priority_band
from app.truth.verifier import MISINFO_VERDICTS, verify

logger = logging.getLogger(__name__)
_masker = PiiMasker()
_classifier = FastSentimentClassifier()
CLASSIFIER_VERSION = "yudhix-sense/keyword-v2"


class PipelineError(Exception):
    """An error with a message that is safe and useful to show the user."""


# ----------------------------------------------------------------------------- jobs

STALE_JOB_MINUTES = 30  # a RUNNING job older than this was cut off by a restart


def create_job(tenant_id: str, video_url: str, product_id: Optional[str], actor: str,
               kind: str = "ANALYZE", trigger: str = "USER") -> Dict:
    video_id = youtube.parse_video_id(video_url)
    with cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO video_analysis_job (tenant_id, video_url, video_id, product_id, created_by, message,
                   kind, trigger)
               VALUES (%s, %s, %s, %s, %s, 'Waiting to start', %s, %s) RETURNING *""",
            (tenant_id, video_url, video_id, product_id, actor, kind, trigger))
        return _job_dict(cur.fetchone())


def active_job(tenant_id: str, video_id: str) -> Optional[Dict]:
    """A job for this video that is still queued or running, if any."""
    row = fetch_one(
        """SELECT * FROM video_analysis_job WHERE tenant_id = %s AND video_id = %s
             AND status IN ('QUEUED', 'RUNNING') AND updated_at > now() - make_interval(mins => %s)
           ORDER BY created_at DESC LIMIT 1""", (tenant_id, video_id, STALE_JOB_MINUTES))
    return _job_dict(row) if row else None


def start_comment_check(tenant_id: str, video_id: str, actor: str, trigger: str = "USER") -> Dict:
    """Queue a "fetch new comments" job, or return the job already working on this video."""
    return start_video_job(tenant_id, video_id, actor, "COMMENTS", trigger)


def start_video_job(tenant_id: str, video_id: str, actor: str, kind: str, trigger: str = "USER") -> Dict:
    """Queue a COMMENTS or FACTS job for an analyzed video, or return the job already working on it."""
    running = active_job(tenant_id, video_id)
    if running:
        return running
    video = fetch_one("SELECT video_url, product_id FROM video_truth_analysis WHERE tenant_id = %s AND video_id = %s",
                      (tenant_id, video_id))
    if not video:
        raise PipelineError("This video hasn't been analyzed yet.")
    return create_job(tenant_id, video["video_url"], str(video["product_id"]) if video.get("product_id") else None,
                      actor, kind=kind, trigger=trigger)


def get_job(tenant_id: str, job_id: str) -> Optional[Dict]:
    row = fetch_one("SELECT * FROM video_analysis_job WHERE tenant_id = %s AND id = %s", (tenant_id, job_id))
    return _job_dict(row) if row else None


def list_jobs(tenant_id: str, limit: int = 20) -> List[Dict]:
    # Scheduled checks run in the background; they'd crowd out the jobs people started.
    rows = fetch_all("""SELECT * FROM video_analysis_job WHERE tenant_id = %s AND trigger = 'USER'
                        ORDER BY created_at DESC LIMIT %s""", (tenant_id, limit))
    return [_job_dict(r) for r in rows]


def _job_dict(r: Dict) -> Dict:
    return {
        "id": str(r["id"]), "videoUrl": r["video_url"], "videoId": r["video_id"],
        "productId": str(r["product_id"]) if r.get("product_id") else None,
        "status": r["status"], "stage": r["stage"], "progress": r["progress"],
        "message": r.get("message"), "error": r.get("error"),
        "kind": r.get("kind") or "ANALYZE", "trigger": r.get("trigger") or "USER", "result": r.get("result"),
        "createdAt": r["created_at"].isoformat() if r.get("created_at") else None,
        "finishedAt": r["finished_at"].isoformat() if r.get("finished_at") else None,
    }


def _update(job_id: str, stage: str, progress: int, message: str, status: str = "RUNNING",
            error: Optional[str] = None, result: Optional[Dict] = None) -> None:
    with cursor(commit=True) as cur:
        cur.execute(
            """UPDATE video_analysis_job SET status = %s, stage = %s, progress = %s, message = %s, error = %s,
                      updated_at = now(), result = COALESCE(%s::jsonb, result),
                      finished_at = CASE WHEN %s IN ('COMPLETED', 'FAILED') THEN now() ELSE finished_at END
               WHERE id = %s""",
            (status, stage, progress, message, error, json.dumps(result) if result else None, status, job_id))


def run_job(job_id: str, tenant_id: str, manual_transcript: Optional[str] = None) -> None:
    job = get_job(tenant_id, job_id)
    if not job:
        return
    creator = (fetch_one("SELECT created_by FROM video_analysis_job WHERE id = %s", (job_id,)) or {}).get("created_by")
    if job["kind"] == "COMMENTS":
        return _run_comment_check(job_id, tenant_id, job, creator)
    if job["kind"] == "FACTS":
        return _run_fact_check(job_id, tenant_id, job, creator)
    try:
        result = analyze_video(tenant_id, job["videoId"], job["videoUrl"], job.get("productId"), manual_transcript,
                               progress=lambda stage, pct, msg: _update(job_id, stage, pct, msg))
        _update(job_id, "COMPLETED", 100, "Analysis complete", status="COMPLETED")
        billing.record(tenant_id, "COMMENT_INGESTED", result.get("commentsIngested", 0), key=f"job:{job_id}")
        notify(tenant_id, "analysis", "Truth report ready",
               f"{result.get('misleadingClaims', 0)} of {result.get('claims', 0)} claims disputed.",
               f"/videos/{job['videoId']}", user_ids=[creator])
    except (PipelineError, youtube.YouTubeError) as e:
        _update(job_id, "FAILED", 100, str(e), status="FAILED", error=str(e))
        notify(tenant_id, "analysis", "Video analysis failed", str(e), "/analyze", user_ids=[creator])
    except Exception as e:  # unexpected: log the detail, show a generic message
        logger.exception("Video analysis job %s failed", job_id)
        _update(job_id, "FAILED", 100, "Something went wrong while analyzing this video.", status="FAILED",
                error=f"{type(e).__name__}: {e}")
        notify(tenant_id, "analysis", "Video analysis failed", "Something went wrong. Try again.", "/analyze",
               user_ids=[creator])


def _run_comment_check(job_id: str, tenant_id: str, job: Dict, creator: Optional[str]) -> None:
    scheduled = job["trigger"] == "SCHEDULE"
    try:
        r = check_new_comments(tenant_id, job["videoId"],
                               progress=lambda stage, pct, msg: _update(job_id, stage, pct, msg))
        n = r["newComments"]
        message = (f"{n} new comment{'s' if n != 1 else ''}" if n else "No new comments since the last check")
        _update(job_id, "COMPLETED", 100, message, status="COMPLETED", result=r)
        if n:
            billing.record(tenant_id, "COMMENT_INGESTED", n, key=f"job:{job_id}")
        if n and (not scheduled or r["negative"] or r["ideas"]):
            parts = [f"{r['negative']} negative"] if r["negative"] else []
            if r["ideas"]:
                parts.append(f"{r['ideas']} product idea{'s' if r['ideas'] != 1 else ''}")
            body = f"{n} new on \"{r['videoTitle']}\"" + (f": {', '.join(parts)}." if parts else ".")
            link = f"/inbox?video={job['videoId']}&fresh=1"
            if scheduled:  # everyone who acts on comments
                notify(tenant_id, "comments", "New comments", body, link, roles=["admin", "approver", "agent"])
            else:
                notify(tenant_id, "comments", "New comments", body, link, user_ids=[creator])
    except (PipelineError, youtube.YouTubeError) as e:
        _update(job_id, "FAILED", 100, str(e), status="FAILED", error=str(e))
        _mark_checked(tenant_id, job["videoId"])  # don't retry a failing video on every scheduler round
        if not scheduled:
            notify(tenant_id, "comments", "Couldn't fetch new comments", str(e), f"/videos/{job['videoId']}",
                   user_ids=[creator])
    except Exception as e:
        logger.exception("Comment check %s failed", job_id)
        _update(job_id, "FAILED", 100, "Something went wrong while fetching new comments.", status="FAILED",
                error=f"{type(e).__name__}: {e}")
        _mark_checked(tenant_id, job["videoId"])


def check_new_comments(tenant_id: str, video_id: str, progress) -> Dict:
    """Fetch comments posted since the last check, read them with AI, re-link the video.
    The transcript and fact-check are left as they are."""
    video = fetch_one("SELECT * FROM video_truth_analysis WHERE tenant_id = %s AND video_id = %s",
                      (tenant_id, video_id))
    if not video:
        raise PipelineError("This video hasn't been analyzed yet.")
    if not youtube.has_api_key():
        raise PipelineError("No YouTube API key on the server. Add YOUTUBE_API_KEY to services/yudhix-sense/.env "
                            "and restart the API.")

    progress("INGESTING_COMMENTS", 20, "Looking for comments posted since the last check")
    known = {r["platform_comment_id"] for r in fetch_all(
        """SELECT platform_comment_id FROM comment
           WHERE tenant_id = %s AND platform = 'YOUTUBE' AND custom_attributes->>'video_id' = %s""",
        (tenant_id, video_id))}
    # Nothing stored yet (e.g. analyzed before a YouTube key was set): take the newest ones.
    raw = youtube.fetch_new_comments(video_id, known, config.NEW_COMMENTS_MAX)
    meta = youtube.VideoMeta(video_id=video_id, title=video["video_title"], channel_title=video["channel_title"])
    product_id = str(video["product_id"]) if video.get("product_id") else None
    stamp = datetime.now(timezone.utc).isoformat()
    _persist(tenant_id, video_id, meta, product_id, raw, extra={"new_at": stamp})

    result = {"newComments": len(raw), "negative": 0, "ideas": 0, "videoTitle": video["video_title"]}
    if raw:
        fresh = [c for c in _video_comments(tenant_id, video_id) if (c.get("new_at") or "") == stamp]
        claims = fetch_all("SELECT * FROM video_claim WHERE tenant_id = %s AND video_analysis_id = %s "
                           "ORDER BY timestamp_seconds", (tenant_id, video["id"]))
        progress("UNDERSTANDING", 45, f"Reading {len(fresh)} new comments")
        read = audience.understand(tenant_id, claims, fresh, lambda done, total: progress(
            "UNDERSTANDING", 45 + int(40 * done / max(1, total)), f"Reading new comments with AI ({done}/{total} batches)"))
        result["ideas"] = read.get("ideas", 0)
        progress("ATTRIBUTING", 90, "Linking the new comments to claims")
        attribute_video(tenant_id, video_id)
        ids = [str(c["id"]) for c in fresh]
        neg = fetch_one("""SELECT count(*) AS n FROM comment_analysis WHERE tenant_id = %s
                           AND comment_id = ANY(%s::uuid[]) AND sentiment = 'NEGATIVE'""", (tenant_id, ids))
        result["negative"] = int(neg["n"])
    _mark_checked(tenant_id, video_id)
    return result


def _run_fact_check(job_id: str, tenant_id: str, job: Dict, creator: Optional[str]) -> None:
    try:
        r = recheck_claims(tenant_id, job["videoId"], progress=lambda stage, pct, msg: _update(job_id, stage, pct, msg))
        n = r["changed"]
        message = f"{n} of {r['claims']} verdicts changed" if n else f"All {r['claims']} verdicts unchanged"
        _update(job_id, "COMPLETED", 100, message, status="COMPLETED", result=r)
        if job["trigger"] == "USER":
            notify(tenant_id, "analysis", "Claims re-checked", f"\"{r['videoTitle']}\": {message.lower()}.",
                   f"/videos/{job['videoId']}", user_ids=[creator])
    except PipelineError as e:
        _update(job_id, "FAILED", 100, str(e), status="FAILED", error=str(e))
    except Exception as e:
        logger.exception("Fact re-check %s failed", job_id)
        _update(job_id, "FAILED", 100, "Something went wrong while re-checking the claims.", status="FAILED",
                error=f"{type(e).__name__}: {e}")


def recheck_claims(tenant_id: str, video_id: str, progress) -> Dict:
    """Fact-check the stored claims again against the knowledge base as it is now. The index is built
    from the database on every check, so newly added facts count straight away."""
    video = fetch_one("SELECT * FROM video_truth_analysis WHERE tenant_id = %s AND video_id = %s",
                      (tenant_id, video_id))
    if not video:
        raise PipelineError("This video hasn't been analyzed yet.")
    claims = fetch_all("SELECT * FROM video_claim WHERE tenant_id = %s AND video_analysis_id = %s "
                       "ORDER BY timestamp_seconds", (tenant_id, video["id"]))
    index = KnowledgeIndex(fetch_all("SELECT * FROM product_knowledge WHERE tenant_id = %s", (tenant_id,)))
    changed, checked = 0, []
    for i, c in enumerate(claims, start=1):
        progress("FACT_CHECKING", 10 + int(75 * (i - 1) / max(1, len(claims))),
                 f"Checking claim {i} of {len(claims)} against your knowledge base")
        checked.append((c, verify(c["creator_quote"], index.search(f"{c['topic']} {c['creator_quote']}", k=3))))
    with cursor(commit=True) as cur:
        for c, v in checked:
            doc = v.knowledge or {}
            citation = (f"{doc.get('document_title')} {('§' + doc['clause_ref']) if doc.get('clause_ref') else ''}".strip()
                        if doc else None)
            changed += v.verdict != c["verdict"]
            cur.execute(
                """UPDATE video_claim SET verdict = %s, confidence_score = %s, rag_knowledge_id = %s,
                          fact_check_analysis = %s, official_citation = %s, verification_method = %s
                   WHERE id = %s""",
                (v.verdict, round(v.confidence, 3), doc.get("id"), v.analysis, citation, v.method, c["id"]))
        cur.execute("""UPDATE video_truth_analysis SET facts_stale = false, facts_checked_at = now()
                       WHERE id = %s""", (video["id"],))
    progress("ATTRIBUTING", 90, "Updating which reactions trace back to misinformation")
    stats = attribute_video(tenant_id, video_id)
    return {"claims": len(claims), "changed": changed, "misleadingClaims": stats["misleadingClaims"],
            "videoTitle": video["video_title"]}


def mark_facts_stale(tenant_id: str) -> int:
    """The knowledge base changed: every analyzed video in the workspace was checked against older facts."""
    with cursor(commit=True) as cur:
        cur.execute("UPDATE video_truth_analysis SET facts_stale = true WHERE tenant_id = %s", (tenant_id,))
        return cur.rowcount


def run_jobs(job_ids: List[str], tenant_id: str) -> None:
    """Run queued jobs one after another (one background task, so the AI model isn't flooded)."""
    for job_id in job_ids:
        run_job(job_id, tenant_id)


def _mark_checked(tenant_id: str, video_id: str) -> None:
    with cursor(commit=True) as cur:
        cur.execute("UPDATE video_truth_analysis SET comments_checked_at = now() WHERE tenant_id = %s AND video_id = %s",
                    (tenant_id, video_id))


# ----------------------------------------------------------------------------- pipeline

def analyze_video(tenant_id: str, video_id: str, video_url: str, product_id: Optional[str],
                  manual_transcript: Optional[str], progress) -> Dict:
    existing = fetch_one("SELECT * FROM video_truth_analysis WHERE tenant_id = %s AND video_id = %s",
                         (tenant_id, video_id))

    # 1. Metadata
    progress("FETCHING_VIDEO", 8, "Reading video details")
    meta = youtube.fetch_metadata(video_id) or _oembed_metadata(video_id, existing)

    # 2. Transcript
    progress("TRANSCRIBING", 20, "Getting the transcript")
    transcript = youtube.parse_manual_transcript(manual_transcript) if manual_transcript else youtube.fetch_transcript(video_id)
    if transcript and not transcript.segments:
        transcript = None

    knowledge = fetch_all("SELECT * FROM product_knowledge WHERE tenant_id = %s", (tenant_id,))
    index = KnowledgeIndex(knowledge)

    if transcript:
        # 3. Claims
        progress("EXTRACTING_CLAIMS", 38, f"Finding claims in {len(transcript.segments)} transcript lines")
        products = fetch_all("SELECT name FROM product WHERE tenant_id = %s", (tenant_id,))
        brand_terms = [p["name"] for p in products] + [k["document_title"] for k in knowledge]
        extracted = extract_claims(transcript, brand_terms)
        if not extracted:
            raise PipelineError("No checkable claims were found in this video's transcript.")

        # 4. Fact-check
        progress("FACT_CHECKING", 55, f"Checking {len(extracted)} claims against your knowledge base")
        checked = []
        for c in extracted:
            v = verify(c.quote, index.search(f"{c.topic} {c.quote}", k=3))
            checked.append((c, v))
        analysis_id = _save_video_and_claims(tenant_id, meta, video_url, product_id, transcript.source, checked)
    elif existing:
        # Seeded / previously analyzed video with no transcript available now: keep its claims.
        progress("FACT_CHECKING", 55, "No new transcript. Re-using the existing claims for this video")
        analysis_id = str(existing["id"])
    else:
        raise PipelineError(
            "No transcript available: the video has no captions and Whisper isn't installed on the server. "
            "Paste the transcript in the Analyze form to continue.")

    # 5. Comments
    progress("INGESTING_COMMENTS", 70, "Collecting audience comments")
    ingested = _ingest_comments(tenant_id, video_id, meta, product_id)

    # 6. Sentiment, topics and claim references (AI for the most-liked comments, rules for the rest)
    comments = _video_comments(tenant_id, video_id)
    claims = fetch_all("SELECT * FROM video_claim WHERE tenant_id = %s AND video_analysis_id = %s ORDER BY timestamp_seconds",
                       (tenant_id, analysis_id))
    if comments:
        use_ai = llm.is_available()
        progress("UNDERSTANDING", 76, f"Reading {len(comments)} comments with AI" if use_ai
                 else f"Reading {len(comments)} comments (rule-based: AI model is offline)")
        audience.understand(tenant_id, claims, comments, lambda done, total: progress(
            "UNDERSTANDING", 76 + int(12 * done / max(1, total)), f"Reading comments with AI ({done}/{total} batches)"))

    # 7. Attribution + scoring
    progress("ATTRIBUTING", 90, "Linking comments to the claims that triggered them")
    stats = attribute_video(tenant_id, video_id)

    _mark_checked(tenant_id, video_id)
    with cursor(commit=True) as cur:
        cur.execute("""UPDATE video_truth_analysis SET facts_stale = false, facts_checked_at = now()
                       WHERE tenant_id = %s AND video_id = %s""", (tenant_id, video_id))
        append_audit(cur, tenant_id, "system-truth-pipeline", "SYSTEM", "VIDEO_ANALYZED", "VIDEO", video_id,
                     {"analysis_id": analysis_id, "comments_ingested": ingested, **stats})
    return {"analysisId": analysis_id, "commentsIngested": ingested, **stats}


def _oembed_metadata(video_id: str, existing: Optional[Dict]) -> youtube.VideoMeta:
    if existing:
        return youtube.VideoMeta(video_id=video_id, title=existing["video_title"],
                                 channel_title=existing["channel_title"],
                                 published_at=existing.get("published_date") or "",
                                 duration_seconds=existing.get("duration_seconds") or 0,
                                 thumbnail_url=existing.get("thumbnail_url") or "")
    try:
        res = httpx.get("https://www.youtube.com/oembed",
                        params={"url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"}, timeout=10)
        if res.status_code == 200:
            d = res.json()
            return youtube.VideoMeta(video_id=video_id, title=d.get("title", f"YouTube video {video_id}"),
                                     channel_title=d.get("author_name", "Unknown channel"),
                                     thumbnail_url=d.get("thumbnail_url", ""))
        if res.status_code in (401, 403, 404):
            raise PipelineError("That video is private, deleted or doesn't allow embedding.")
    except httpx.HTTPError:
        pass
    return youtube.VideoMeta(video_id=video_id, title=f"YouTube video {video_id}", channel_title="Unknown channel")


def _save_video_and_claims(tenant_id: str, meta: youtube.VideoMeta, video_url: str, product_id: Optional[str],
                           transcript_source: str, checked: List) -> str:
    method = "LLM" if any(v.method == "LLM" for _, v in checked) else "HEURISTIC"
    with cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO video_truth_analysis (tenant_id, video_id, channel_title, video_title, video_url,
                   published_date, duration_seconds, product_id, thumbnail_url, transcript_source, analysis_method,
                   view_count, analyzed_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, now())
               ON CONFLICT (tenant_id, video_id) DO UPDATE SET
                   channel_title = EXCLUDED.channel_title, video_title = EXCLUDED.video_title,
                   video_url = EXCLUDED.video_url,
                   published_date = COALESCE(NULLIF(EXCLUDED.published_date, ''), video_truth_analysis.published_date),
                   duration_seconds = GREATEST(EXCLUDED.duration_seconds, video_truth_analysis.duration_seconds),
                   product_id = COALESCE(EXCLUDED.product_id, video_truth_analysis.product_id),
                   thumbnail_url = COALESCE(NULLIF(EXCLUDED.thumbnail_url, ''), video_truth_analysis.thumbnail_url),
                   transcript_source = EXCLUDED.transcript_source, analysis_method = EXCLUDED.analysis_method,
                   view_count = COALESCE(EXCLUDED.view_count, video_truth_analysis.view_count),
                   analyzed_at = now()
               RETURNING id""",
            (tenant_id, meta.video_id, meta.channel_title or "Unknown channel", meta.title, video_url,
             _pretty_date(meta.published_at), meta.duration_seconds, product_id, meta.thumbnail_url,
             transcript_source, method, meta.view_count))
        analysis_id = str(cur.fetchone()["id"])
        cur.execute("DELETE FROM video_claim WHERE tenant_id = %s AND video_analysis_id = %s", (tenant_id, analysis_id))
        for c, v in checked:
            doc = v.knowledge or {}
            citation = (f"{doc.get('document_title')} {('§' + doc['clause_ref']) if doc.get('clause_ref') else ''}".strip()
                        if doc else None)
            cur.execute(
                """INSERT INTO video_claim (tenant_id, video_analysis_id, timestamp_start, timestamp_seconds,
                       creator_quote, topic, verdict, confidence_score, rag_knowledge_id, fact_check_analysis,
                       official_citation, verification_method)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (tenant_id, analysis_id, format_timestamp(c.timestamp_seconds), c.timestamp_seconds, c.quote,
                 c.topic, v.verdict, round(v.confidence, 3), doc.get("id"), v.analysis, citation, v.method))
    return analysis_id


def _pretty_date(iso: str) -> str:
    try:
        return datetime.fromisoformat(iso.replace("Z", "+00:00")).strftime("%d %b %Y")
    except (ValueError, AttributeError):
        return iso or ""


def author_hash(tenant_id: str, platform: str, author_id: str) -> str:
    """Keyed pseudonym (matches libs/yudhix-common AuthorHasher): v1.<hex HMAC-SHA256>."""
    key = hashlib.sha256(f"{config.AUTHOR_HMAC_KEY}:{tenant_id}".encode()).digest()
    digest = hmac.new(key, f"{platform}:{author_id}".encode(), hashlib.sha256).hexdigest()
    return f"v1.{digest[:40]}"


def _ingest_comments(tenant_id: str, video_id: str, meta: youtube.VideoMeta, product_id: Optional[str]) -> int:
    spread = config.COMMENT_SAMPLING == "spread"
    if spread:
        raw = youtube.sample_comments(video_id, config.MAX_COMMENTS_PER_VIDEO, config.COMMENT_POOL_MAX)
    else:
        raw = youtube.fetch_comments(video_id, config.MAX_COMMENTS_PER_VIDEO)
    _persist(tenant_id, video_id, meta, product_id, raw)
    if spread and raw:
        _keep_only(tenant_id, video_id, [c["comment_id"] for c in raw])
    return len(raw)


def _persist(tenant_id: str, video_id: str, meta: youtube.VideoMeta, product_id: Optional[str], raw: List[Dict],
             extra: Optional[Dict] = None) -> None:
    if raw and not product_id:  # attach to this workspace's own product, never another tenant's
        first = fetch_one("SELECT id FROM product WHERE tenant_id = %s AND active ORDER BY created_at LIMIT 1",
                          (tenant_id,))
        product_id = str(first["id"]) if first else None
    for c in raw:
        masked, _ = _masker.mask(c["text"])
        sentiment, score = _classifier.classify(masked)
        persist_comment_and_analysis({
            "tenant_id": tenant_id, "platform": "YOUTUBE", "comment_id": c["comment_id"],
            "raw_text": c["text"], "masked_text": masked,
            "author_hash": author_hash(tenant_id, "YOUTUBE", c["author_channel_id"]),
            "likes": c["likes"], "replies": c["replies"], "sentiment": sentiment, "sentiment_score": score,
            "intent": "COMPLAINT" if sentiment == "NEGATIVE" else ("PRAISE" if sentiment == "POSITIVE" else "GENERAL"),
            "churn_risk": 0.7 if sentiment == "NEGATIVE" else 0.1,
            "channel_title": meta.channel_title, "video_id": video_id, "video_title": meta.title,
            "video_url": f"https://www.youtube.com/watch?v={video_id}",
            "platform_created_at": c.get("published_at") or "now()",
            "source_id": DEFAULT_SOURCE_ID, "product_id": product_id or DEFAULT_PRODUCT_ID,
            "custom_attributes": dict(extra or {}),
        })


def _keep_only(tenant_id: str, video_id: str, platform_ids: List[str]) -> None:
    """Show only this run's sample: archive the video's other comments (kept in the database, hidden
    everywhere), except comments that already have a reply. Re-sampled comments become active again."""
    with cursor(commit=True) as cur:
        cur.execute(
            """UPDATE comment c SET status = CASE WHEN c.platform_comment_id = ANY(%s) THEN 'ACTIVE' ELSE 'ARCHIVED' END
               WHERE c.tenant_id = %s AND c.custom_attributes->>'video_id' = %s
                 AND (c.platform_comment_id = ANY(%s)
                      OR NOT EXISTS (SELECT 1 FROM reply r WHERE r.tenant_id = c.tenant_id AND r.comment_id = c.id))""",
            (platform_ids, tenant_id, video_id, platform_ids))


# ----------------------------------------------------------------------------- attribution

def _video_comments(tenant_id: str, video_id: str) -> List[Dict]:
    return fetch_all(
        """SELECT c.id, c.masked_text, c.like_count, c.reply_count, c.platform_created_at,
                  c.custom_attributes->'ai' AS ai, c.custom_attributes->>'new_at' AS new_at,
                  ca.churn_risk, ca.toxic, ca.model_version, ca.sentiment, ca.sentiment_score
           FROM comment c LEFT JOIN comment_analysis ca ON ca.tenant_id = c.tenant_id AND ca.comment_id = c.id
           WHERE c.tenant_id = %s AND c.custom_attributes->>'video_id' = %s AND c.status = 'ACTIVE'""",
        (tenant_id, video_id))


def attribute_video(tenant_id: str, video_id: str) -> Dict:
    """(Re)link a video's comments to its claims, re-score them, and refresh the video's scores."""
    video = fetch_one("SELECT * FROM video_truth_analysis WHERE tenant_id = %s AND video_id = %s",
                      (tenant_id, video_id))
    if not video:
        raise PipelineError("This video hasn't been analyzed yet.")
    claims = fetch_all("SELECT * FROM video_claim WHERE tenant_id = %s AND video_analysis_id = %s",
                       (tenant_id, video["id"]))
    comments = _video_comments(tenant_id, video_id)
    # Comments the AI read keep its sentiment and claim decision; the rest use rules.
    ai_read = {str(c["id"]): c["ai"] for c in comments
               if (c.get("model_version") or "").startswith("llm/") and isinstance(c.get("ai"), dict)}

    links = attribution.attribute(claims, comments, ai_read)
    link_by_comment = {l.comment_id: l for l in links}
    verdict_by_claim = {str(c["id"]): c["verdict"] for c in claims}

    per_claim_sent: Dict[str, Counter] = {str(c["id"]): Counter() for c in claims}
    sentiments: Counter = Counter()
    misinfo_negative = 0

    with cursor(commit=True) as cur:
        cur.execute("""DELETE FROM comment_claim_link WHERE tenant_id = %s
                       AND claim_id IN (SELECT id FROM video_claim WHERE tenant_id = %s AND video_analysis_id = %s)""",
                    (tenant_id, tenant_id, video["id"]))
        for c in comments:
            cid = str(c["id"])
            if cid in ai_read:
                sentiment, s_score = c["sentiment"], float(c["sentiment_score"] or 0)
            else:
                sentiment, s_score = _classifier.classify(c["masked_text"] or "")
                audience.store_rule_topics(cur, tenant_id, cid, c["masked_text"] or "", sentiment)
            link = link_by_comment.get(cid)
            verdict = verdict_by_claim.get(link.claim_id) if link else None
            misinfo = verdict in MISINFO_VERDICTS
            churn = float(c["churn_risk"]) if c.get("churn_risk") is not None else (0.7 if sentiment == "NEGATIVE" else 0.1)
            score = impact_score(sentiment, churn, c["like_count"], c["reply_count"], c["platform_created_at"],
                                 bool(c.get("toxic")), misinfo)
            cur.execute(
                """UPDATE comment_analysis SET sentiment = %s, sentiment_score = %s, impact_score = %s, priority = %s,
                          model_version = %s
                   WHERE tenant_id = %s AND comment_id = %s""",
                (sentiment, s_score, score, priority_band(score),
                 c["model_version"] if cid in ai_read else CLASSIFIER_VERSION, tenant_id, cid))
            sentiments[sentiment] += 1
            if link:
                cur.execute(
                    """INSERT INTO comment_claim_link (tenant_id, comment_id, claim_id, score, method, evidence)
                       VALUES (%s, %s, %s, %s, %s, %s) ON CONFLICT DO NOTHING""",
                    (tenant_id, cid, link.claim_id, link.score, link.method, link.evidence))
                per_claim_sent[link.claim_id][sentiment] += 1
                if misinfo and sentiment == "NEGATIVE":
                    misinfo_negative += 1

        for claim_id, counts in per_claim_sent.items():
            total = sum(counts.values())
            dominant = counts.most_common(1)[0][0] if total else "NEUTRAL"
            cur.execute("UPDATE video_claim SET incited_comments_count = %s, sentiment_impact = %s WHERE id = %s",
                        (total, dominant, claim_id))

        total_claims = len(claims)
        misleading = sum(1 for c in claims if c["verdict"] in MISINFO_VERDICTS)
        correct = sum(1 for c in claims if c["verdict"] == "FACTUALLY_CORRECT")
        accuracy = round(correct / total_claims, 3) if total_claims else 0.0
        negative_total = sentiments["NEGATIVE"]
        misinfo_share = round(misinfo_negative / negative_total, 3) if negative_total else 0.0
        rage_bait = round(min(1.0, 0.6 * (misleading / total_claims if total_claims else 0) + 0.4 * misinfo_share), 3)
        grade = ("HIGH_SENSATIONALISM" if rage_bait >= 0.6 else "MODERATE" if rage_bait >= 0.3
                 else "FACTUAL_AND_BALANCED")
        summary = _summary(video, claims, len(comments), len(links), misinfo_share, misleading)
        cur.execute(
            """UPDATE video_truth_analysis SET total_claims = %s, misleading_claims_count = %s,
                      factual_accuracy_score = %s, rage_bait_score = %s, sensationalism_grade = %s, summary = %s
               WHERE id = %s""",
            (total_claims, misleading, accuracy, rage_bait, grade, summary, video["id"]))

    return {"comments": len(comments), "linkedComments": len(links), "claims": total_claims,
            "misleadingClaims": misleading, "misinformationShareOfNegative": misinfo_share}


def _summary(video: Dict, claims: List[Dict], n_comments: int, n_linked: int, misinfo_share: float,
             misleading: int) -> str:
    total = len(claims)
    if not total:
        return "No claims were found in this video."
    parts = [f"{misleading} of {total} claims in this video are misleading, false or unverified."]
    if n_comments:
        parts.append(f"{n_linked} of {n_comments} comments react to a specific claim.")
        if misinfo_share:
            parts.append(f"{round(misinfo_share * 100)}% of negative comments trace back to misinformation, "
                         f"not to a product problem.")
    return " ".join(parts)
