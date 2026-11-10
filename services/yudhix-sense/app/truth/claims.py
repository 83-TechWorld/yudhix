"""Atomic claim extraction: turn a transcript into short, checkable, timestamped statements.

Primary path is the local LLM. When no model is available, a rule-based extractor picks
sentences that make factual assertions about the brand's products (numbers, prices,
absolutes, policy verbs) so the pipeline still produces a usable report.
"""
import re
from dataclasses import dataclass
from typing import Iterable, List, Set

from app.core import llm
from app.core.text import STOPWORDS, split_sentences, tokens
from app.truth.youtube import Transcript

MAX_CLAIMS = 8


@dataclass
class ExtractedClaim:
    timestamp_seconds: int
    quote: str
    topic: str


ASSERTION_PATTERNS = [
    r"\$\s?\d", r"\b\d+(\.\d+)?\s?(%|percent|gb|tb|fps|hours?|days?|years?|dollars?|rupees?)\b",
    r"\b(always|never|every|all|none|no longer|completely|permanently|immediately|forever|only)\b",
    r"\b(will|won't|is going to|are going to|plans? to|is forcing|forces?|requires?|bans?|removes?|"
    r"kills?|ends?|ending|discontinu\w*|cancel\w*|wipes?|deletes?|revok\w*|lock\w*|blocks?)\b",
    r"\b(confirmed|announced|according to|officially|leaked|reportedly)\b",
]
HEDGES = re.compile(r"\b(i think|maybe|in my opinion|i feel|probably|subscribe|like and|sponsor|link in)\b", re.I)


def extract_claims(transcript: Transcript, brand_terms: Iterable[str]) -> List[ExtractedClaim]:
    claims = _extract_with_llm(transcript)
    if claims:
        return claims[:MAX_CLAIMS]
    return _extract_heuristic(transcript, {t for term in brand_terms for t in tokens(term)})


def _numbered_lines(transcript: Transcript, max_chars: int = 12000) -> str:
    lines, total = [], 0
    for seg in transcript.segments:
        line = f"[{int(seg.start)}] {seg.text}"
        total += len(line)
        if total > max_chars:
            break
        lines.append(line)
    return "\n".join(lines)


def _extract_with_llm(transcript: Transcript) -> List[ExtractedClaim]:
    prompt = f"""You are a fact-checking analyst. Below is a video transcript; each line starts with
its start time in seconds in square brackets. Extract up to {MAX_CLAIMS} ATOMIC, CHECKABLE factual
claims the creator makes about a company, product, price, policy or feature. Skip opinions, jokes,
sponsor reads and calls to subscribe. Quote the creator as closely as possible, and include the full
sentence with its subject so each claim makes sense on its own ("Sony will drop disc drives from the next
PlayStation", not "it's finished").

Return JSON: {{"claims": [{{"timestamp_seconds": 74, "quote": "...", "topic": "3-5 word topic"}}]}}

Transcript:
{_numbered_lines(transcript)}
"""
    data = llm.generate_json(prompt)
    if not isinstance(data, dict):
        return []
    out: List[ExtractedClaim] = []
    for c in data.get("claims", []) or []:
        quote = str(c.get("quote", "")).strip()
        if len(quote) < 15:
            continue
        try:
            ts = int(float(c.get("timestamp_seconds", 0)))
        except (TypeError, ValueError):
            ts = 0
        out.append(ExtractedClaim(timestamp_seconds=ts, quote=quote[:500],
                                  topic=str(c.get("topic") or _topic_from(quote))[:100]))
    return out


def _extract_heuristic(transcript: Transcript, brand_tokens: Set[str]) -> List[ExtractedClaim]:
    # Rebuild sentences across caption fragments, remembering where each began.
    sentences: List[tuple] = []
    buffer, start = "", None
    for seg in transcript.segments:
        if start is None:
            start = seg.start
        buffer = f"{buffer} {seg.text}".strip()
        if re.search(r"[.!?]$", seg.text.strip()) or len(buffer) > 220:
            for s in split_sentences(buffer):
                sentences.append((start, s))
            buffer, start = "", None
    if buffer:
        for s in split_sentences(buffer):
            sentences.append((start or 0, s))

    scored = []
    for ts, sentence in sentences:
        if len(sentence) < 30 or HEDGES.search(sentence):
            continue
        lower = sentence.lower()
        score = sum(1.0 for p in ASSERTION_PATTERNS if re.search(p, lower))
        sent_tokens = set(tokens(sentence))
        score += 1.5 * len(sent_tokens & brand_tokens)
        if score >= 2.0:
            scored.append((score, int(ts), sentence))

    scored.sort(key=lambda x: -x[0])
    chosen, seen = [], set()
    for score, ts, sentence in scored:
        key = frozenset(tokens(sentence))
        if any(len(key & s) / max(1, len(key | s)) > 0.6 for s in seen):
            continue
        seen.add(key)
        chosen.append(ExtractedClaim(timestamp_seconds=ts, quote=sentence[:500], topic=_topic_from(sentence)))
        if len(chosen) >= MAX_CLAIMS:
            break
    return sorted(chosen, key=lambda c: c.timestamp_seconds)


def _topic_from(sentence: str) -> str:
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'-]+", sentence)
             if w.lower() not in STOPWORDS and len(w) > 2][:4]
    return " ".join(w.capitalize() for w in words) or "General Claim"
