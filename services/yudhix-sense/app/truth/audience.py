"""Audience understanding: sentiment, topics and claim reference for each comment.

With the local AI model awake, comments are classified in batches (most-liked first, so the
comments with the most reach always get the AI's reading). Each batch returns, per comment:
  sentiment  POSITIVE | NEUTRAL | NEGATIVE
  topics     0-2 codes from TOPICS (what the comment is about)
  claim      the number of the video claim it reacts to, or 0
Batches run one at a time: a local Ollama serves one request at a time, so parallel
requests only queue (and time out while queued). A time budget keeps an analysis bounded; whatever the AI doesn't reach falls back to rules
(keyword sentiment, keyword topics, lexical claim matching in attribution.py).

Results are stored on the comment so "Re-link" can re-run attribution without the AI:
  comment_analysis.sentiment / sentiment_score / model_version ('llm/<model>' or rules)
  comment_aspect rows: one per topic
  comment.custom_attributes.ai = {"claim": <claim id or null>, "why": "...", "v": 1}
"""
import json
import logging
import re
import time
from typing import Callable, Dict, List, Optional, Tuple

from app.core import config, llm
from app.core.database import cursor
from app.pipeline.classifier import FastSentimentClassifier

logger = logging.getLogger(__name__)

# Generic product topics: work for any consumer brand, not only gaming.
TOPICS: Dict[str, str] = {
    "PRICE": "Price & value",
    "QUALITY": "Quality & hardware",
    "PERFORMANCE": "Performance",
    "FEATURES": "Features & software",
    "CONTENT": "Games & content",
    "SERVICE": "Online & subscriptions",
    "SUPPORT": "Support & warranty",
    "TRUST": "Trust in the company",
    "COMPETITION": "Competitors & switching",
}

_RULES: Dict[str, List[str]] = {
    "PRICE": ["price", "prices", "priced", "pricing", "cost", "costs", "expensive", "cheap", "cheaper", "afford",
              "affordable", "overpriced", "money", "worth", "value", "pay", "paying", "paid", "dollar", "dollars",
              "rupees", "msrp", "discount", "sale", "inflation", "$", "₹", "greed", "greedy", "rip off", "ripoff"],
    "QUALITY": ["hardware", "build", "quality", "broken", "break", "breaks", "defect", "defective", "drift",
                "overheat", "overheating", "loud", "noise", "fan", "scratch", "scratches", "cheaply made", "plastic",
                "durable", "reliability", "disc drive", "controller", "battery", "port", "usb"],
    "PERFORMANCE": ["fps", "frame rate", "framerate", "performance", "lag", "laggy", "stutter", "loading",
                    "resolution", "4k", "1080p", "graphics", "ray tracing", "upscaling", "pssr", "teraflops", "gpu",
                    "cpu", "power", "faster", "slower", "smooth"],
    "FEATURES": ["feature", "features", "update", "firmware", "ui", "interface", "menu", "software", "backwards",
                 "compatibility", "compatible", "app", "settings", "bug", "bugs"],
    "CONTENT": ["game", "games", "exclusive", "exclusives", "studio", "studios", "title", "titles", "remaster",
                "remasters", "sequel", "library", "first party", "first-party", "live service", "single player",
                "gta", "spider-man", "spiderman", "god of war", "cancel", "canceled", "cancelled"],
    "SERVICE": ["psn", "ps plus", "playstation plus", "subscription", "subscribe", "online", "server", "servers",
                "account", "monthly", "membership", "game pass", "gamepass", "cloud", "store", "digital"],
    "SUPPORT": ["support", "warranty", "repair", "refund", "return", "replacement", "customer service",
                "help desk", "ticket", "rma"],
    "TRUST": ["anti-consumer", "anti consumer", "scam", "lied", "lie", "lies", "trust", "corporate", "corporation",
              "corporations", "shareholders", "greed", "boycott", "never again", "disrespect", "arrogant", "layoffs"],
    "COMPETITION": ["xbox", "nintendo", "switch", "steam", "steam deck", "steam machine", "valve", "pc", "gaming pc",
                    "switching", "switched", "jump ship", "go back to"],
}
_RULE_RE = {t: re.compile(r"(?<![a-z0-9])(" + "|".join(re.escape(w) for w in words) + r")(?![a-z0-9])")
            for t, words in _RULES.items()}

_classifier = FastSentimentClassifier()
RULES_VERSION = "rules/sentiment-v2"
BATCH_SIZE = 10
BATCH_TIMEOUT_SECONDS = 120
MAX_FAILURES_IN_A_ROW = 2


# ----------------------------------------------------------------------------- rules

def rule_topics(text: str, limit: int = 2) -> List[str]:
    """Topics by keyword hits, strongest first."""
    lower = (text or "").lower()
    hits = []
    for topic, rx in _RULE_RE.items():
        n = len(rx.findall(lower))
        if n:
            hits.append((n, topic))
    hits.sort(key=lambda h: -h[0])
    return [t for _, t in hits[:limit]]


def rule_sentiment(text: str) -> Tuple[str, float]:
    return _classifier.classify(text or "")


# ----------------------------------------------------------------------------- AI

def _prompt(claims: List[Dict], batch: List[Dict]) -> str:
    claim_lines = "\n".join(f'{i + 1}. [{c.get("timestamp_start") or ""}] "{(c.get("creator_quote") or "")[:220]}"'
                            for i, c in enumerate(claims)) or "(none)"
    topic_lines = ", ".join(f"{k} ({v})" for k, v in TOPICS.items())
    comment_lines = "\n".join(f'{i + 1}. {(c.get("masked_text") or "")[:400]!r}' for i, c in enumerate(batch))
    return f"""You analyze YouTube comments on a video about a product, for the product's brand team.

Claims the creator makes in the video:
{claim_lines}

Topics: {topic_lines}

For EACH comment return:
- "i": the comment number
- "s": sentiment toward the product or brand: "POS", "NEU" or "NEG". Sarcasm counts as what is meant.
  Complaints, criticism, frustration or disappointment about the product, prices, games or company
  are "NEG" even when phrased as a joke or a question. Only genuinely neutral remarks are "NEU".
- "t": 0 to 2 topic codes the comment is clearly about (empty list if none)
- "c": the number of the claim the comment directly responds to, or 0. Only pick a claim when the
  comment clearly discusses that specific statement; sharing a common word is not enough. Most
  comments respond to no specific claim: use 0 then.
- "w": for "c" > 0, up to 8 words from the comment that show the link; otherwise ""

Comments:
{comment_lines}

Return JSON: {{"results": [{{"i": 1, "s": "NEG", "t": ["PRICE"], "c": 0, "w": ""}}, ...]}}"""


_S = {"POS": "POSITIVE", "NEU": "NEUTRAL", "NEG": "NEGATIVE",
      "POSITIVE": "POSITIVE", "NEUTRAL": "NEUTRAL", "NEGATIVE": "NEGATIVE"}


def _parse(raw, batch: List[Dict], claims: List[Dict]) -> Dict[str, Dict]:
    out: Dict[str, Dict] = {}
    items = raw.get("results") if isinstance(raw, dict) else raw
    if not isinstance(items, list):
        return out
    for item in items:
        if not isinstance(item, dict):
            continue
        try:
            idx = int(item.get("i")) - 1
        except (TypeError, ValueError):
            continue
        if not 0 <= idx < len(batch):
            continue
        sentiment = _S.get(str(item.get("s", "")).upper())
        if not sentiment:
            continue
        topics = [t for t in (item.get("t") or []) if isinstance(t, str) and t.upper() in TOPICS]
        try:
            claim_no = int(item.get("c") or 0)
        except (TypeError, ValueError):
            claim_no = 0
        claim_id = str(claims[claim_no - 1]["id"]) if 1 <= claim_no <= len(claims) else None
        why = str(item.get("w") or "")[:120] if claim_id else ""
        out[str(batch[idx]["id"])] = {"sentiment": sentiment, "topics": [t.upper() for t in topics][:2],
                                      "claim": claim_id, "why": why}
    return out


def classify_with_ai(claims: List[Dict], comments: List[Dict], budget_seconds: float,
                     on_progress: Optional[Callable[[int, int], None]] = None) -> Dict[str, Dict]:
    """AI reading for as many comments as fit in the time budget, most-liked first."""
    if not comments or not llm.is_available():
        return {}
    ordered = sorted(comments, key=lambda c: -(int(c.get("like_count") or 0) + 2 * int(c.get("reply_count") or 0)))
    batches = [ordered[i:i + BATCH_SIZE] for i in range(0, len(ordered), BATCH_SIZE)]
    deadline = time.time() + budget_seconds
    results: Dict[str, Dict] = {}
    failures = 0
    for done, batch in enumerate(batches, start=1):
        if time.time() > deadline or failures >= MAX_FAILURES_IN_A_ROW:
            break
        raw = llm.generate_json(_prompt(claims, batch), timeout=BATCH_TIMEOUT_SECONDS,
                                max_tokens=40 * len(batch) + 100)
        parsed = _parse(raw or {}, batch, claims)
        failures = 0 if parsed else failures + 1
        results.update(parsed)
        if on_progress:
            on_progress(done, len(batches))
    logger.info("AI classified %d of %d comments", len(results), len(comments))
    return results


# ----------------------------------------------------------------------------- store

def understand(tenant_id: str, claims: List[Dict], comments: List[Dict],
               progress: Optional[Callable[[int, int], None]] = None) -> Dict:
    """Classify a video's comments (AI where possible, rules otherwise) and store the result."""
    ai = classify_with_ai(claims, comments, config.LLM_COMMENT_BUDGET_SECONDS, progress)
    model = f"llm/{config.OLLAMA_MODEL}"
    with cursor(commit=True) as cur:
        for c in comments:
            cid = str(c["id"])
            text = c.get("masked_text") or ""
            reading = ai.get(cid)
            if reading:
                sentiment, topics = reading["sentiment"], reading["topics"] or rule_topics(text)
                score = {"POSITIVE": 0.8, "NEGATIVE": -0.8}.get(sentiment, 0.0)
                version = model
                ai_attr = {"claim": reading["claim"], "why": reading["why"], "v": 1}
            else:
                sentiment, score = rule_sentiment(text)
                topics, version, ai_attr = rule_topics(text), RULES_VERSION, None
            cur.execute(
                """UPDATE comment_analysis SET sentiment = %s, sentiment_score = %s, model_version = %s,
                          intent = %s, churn_risk = %s
                   WHERE tenant_id = %s AND comment_id = %s""",
                (sentiment, score, version,
                 "COMPLAINT" if sentiment == "NEGATIVE" else "PRAISE" if sentiment == "POSITIVE" else "GENERAL",
                 _churn(sentiment, text), tenant_id, cid))
            _store_topics(cur, tenant_id, cid, topics, sentiment)
            cur.execute(
                """UPDATE comment SET custom_attributes = CASE WHEN %s::jsonb IS NULL
                          THEN custom_attributes - 'ai' ELSE jsonb_set(custom_attributes, '{ai}', %s::jsonb) END
                   WHERE tenant_id = %s AND id = %s""",
                (json.dumps(ai_attr) if ai_attr else None, json.dumps(ai_attr) if ai_attr else None, tenant_id, cid))
    return {"aiClassified": len(ai), "ruleClassified": len(comments) - len(ai)}


def store_rule_topics(cur, tenant_id: str, comment_id: str, text: str, sentiment: str) -> None:
    """Rules-only topics, used when re-linking comments the AI never read."""
    _store_topics(cur, tenant_id, comment_id, rule_topics(text), sentiment)


def _store_topics(cur, tenant_id: str, comment_id: str, topics: List[str], sentiment: str) -> None:
    cur.execute("DELETE FROM comment_aspect WHERE tenant_id = %s AND comment_id = %s", (tenant_id, comment_id))
    for t in topics:
        cur.execute("INSERT INTO comment_aspect (tenant_id, comment_id, aspect, sentiment) VALUES (%s, %s, %s, %s)",
                    (tenant_id, comment_id, t, sentiment))


def _churn(sentiment: str, text: str) -> float:
    if sentiment != "NEGATIVE":
        return 0.1
    lower = (text or "").lower()
    return 0.9 if any(p in lower for p in FastSentimentClassifier.CHURN_PHRASES) else 0.6
