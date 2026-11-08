"""Audience understanding: sentiment, topics and claim reference for each comment.

With the local AI model awake, comments are classified in batches (most-liked first, so the
comments with the most reach always get the AI's reading). Each batch returns, per comment:
  sentiment  POSITIVE | NEUTRAL | NEGATIVE
  topics     0-2 codes from TOPICS (what the comment is about)
  claim      the number of the video claim it reacts to, or 0
  intent     what the commenter wants: IDEA (feature request or suggestion), PRAISE, BUY (bought or
             plans to), LEAVE (return, cancel or switch away), QUESTION, COMPLAINT, OTHER
  idea       for IDEA, the request in 2-6 words ("more storage", "cheaper digital games")
Batches run one at a time: a local Ollama serves one request at a time, so parallel
requests only queue (and time out while queued). A time budget keeps an analysis bounded; whatever the AI doesn't reach falls back to rules
(keyword sentiment, keyword topics, lexical claim matching in attribution.py).

Results are stored on the comment so "Re-link" can re-run attribution without the AI:
  comment_analysis.sentiment / sentiment_score / model_version ('llm/<model>' or rules)
  comment_aspect rows: one per topic
  comment_analysis.intent: one of INTENTS
  comment.custom_attributes.ai = {"claim": <claim id or null>, "why": "...", "idea": "...", "v": 1}
Feature requests are then grouped into product ideas (app/truth/growth.py).
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

# What the commenter wants, most specific first.
INTENTS: Dict[str, str] = {
    "IDEA": "Feature requests & ideas",
    "PRAISE": "Praise",
    "BUY": "Buying signals",
    "QUESTION": "Questions",
    "COMPLAINT": "Complaints",
    "LEAVE": "Leaving / returning",
    "OTHER": "Other",
}
_IDEA_RE = re.compile(
    r"\b(?:i wish (?:it|they|sony|there|the)|(?:they|sony|playstation) (?:should|need to|needs to) "
    r"(?:add|make|bring|include|allow|give|release|let|put|offer|lower|drop)|please (?:add|bring back|make|give us|let us"
    r"|include|release)|would (?:be )?(?:nice|great|cool|awesome) if|would love (?:to see|it if|a)|bring back"
    r"|give us (?:a|an|the|more|back)|add (?:support for|an option)|why not (?:add|make|have)|feature request"
    r"|my suggestion|hope (?:they|sony) (?:add|make|bring))\b")
_BUY_RE = re.compile(r"\b(pre-?order(?:ed|ing)?|ordered (?:one|mine|it)|(?:just )?bought (?:one|it|mine|a)|buying (?:one|it)"
                     r"|getting one|day one|take my money|(?:will|gonna|going to) buy|picked (?:one|it) up|instant buy"
                     r"|sold me|can'?t wait to (?:buy|get))\b")
_LEAVE_RE = re.compile(r"\b(return(?:ing|ed)? (?:it|mine|my)|cancel(?:l)?(?:ed|ing)? my|refund|switch(?:ing|ed)? to"
                       r"|going back to|sell(?:ing)? my|never buying|not buying|won'?t (?:buy|be buying)|unsubscrib"
                       r"|done with (?:sony|playstation|this)|moving to|jump(?:ing)? ship)\b")
_QUESTION_RE = re.compile(r"^(?:what|how|when|why|does|do|is|are|can|will|would|should|which|where|anyone)\b")

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


def rule_intent(text: str, sentiment: str) -> str:
    """Intent by phrase rules. Rules can spot a request but can't name it well, so only the AI's
    reading turns a request into a product idea."""
    lower = " ".join((text or "").lower().split())
    if _IDEA_RE.search(lower):
        return "IDEA"
    if _LEAVE_RE.search(lower):
        return "LEAVE"
    if _BUY_RE.search(lower) and sentiment != "NEGATIVE":
        return "BUY"
    if sentiment != "NEGATIVE" and (lower.rstrip().endswith("?") or _QUESTION_RE.search(lower)):
        return "QUESTION"
    return {"POSITIVE": "PRAISE", "NEGATIVE": "COMPLAINT"}.get(sentiment, "OTHER")


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
- "n": what the commenter wants: "IDEA" (asks for a feature, change or improvement, or suggests one),
  "PRAISE", "BUY" (bought it or plans to), "LEAVE" (returning, cancelling or switching away),
  "QUESTION", "COMPLAINT" or "OTHER". A complaint that also asks for a specific change is "IDEA".
- "f": for "IDEA", the requested thing in 2-6 plain words, e.g. "more storage", "cheaper digital games";
  otherwise ""

Comments:
{comment_lines}

Return JSON: {{"results": [{{"i": 1, "s": "NEG", "t": ["PRICE"], "c": 0, "w": "", "n": "COMPLAINT", "f": ""}}, ...]}}"""


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
        intent = str(item.get("n") or "").upper()
        intent = intent if intent in INTENTS else None
        idea = " ".join(str(item.get("f") or "").split()[:8])[:80] if intent == "IDEA" else ""
        out[str(batch[idx]["id"])] = {"sentiment": sentiment, "topics": [t.upper() for t in topics][:2],
                                      "claim": claim_id, "why": why, "intent": intent, "idea": idea}
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
                                max_tokens=60 * len(batch) + 100)
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
    from app.truth import growth  # growth imports this module

    ai = classify_with_ai(claims, comments, config.LLM_COMMENT_BUDGET_SECONDS, progress)
    model = f"llm/{config.OLLAMA_MODEL}"
    ideas = []
    with cursor(commit=True) as cur:
        for c in comments:
            cid = str(c["id"])
            text = c.get("masked_text") or ""
            reading = ai.get(cid)
            if reading:
                sentiment, topics = reading["sentiment"], reading["topics"] or rule_topics(text)
                score = {"POSITIVE": 0.8, "NEGATIVE": -0.8}.get(sentiment, 0.0)
                version = model
                intent = reading.get("intent") or rule_intent(text, sentiment)
                idea = reading.get("idea") or ""
                ai_attr = {"claim": reading["claim"], "why": reading["why"], "idea": idea, "v": 2}
            else:
                sentiment, score = rule_sentiment(text)
                topics, version, ai_attr = rule_topics(text), RULES_VERSION, None
                intent, idea = rule_intent(text, sentiment), ""
            cur.execute(
                """UPDATE comment_analysis SET sentiment = %s, sentiment_score = %s, model_version = %s,
                          intent = %s, churn_risk = %s
                   WHERE tenant_id = %s AND comment_id = %s""",
                (sentiment, score, version, intent, _churn(sentiment, text), tenant_id, cid))
            _store_topics(cur, tenant_id, cid, topics, sentiment)
            if intent == "IDEA":
                ideas.append((cid, idea, topics[0] if topics else "FEATURES"))
            cur.execute(
                """UPDATE comment SET custom_attributes = CASE WHEN %s::jsonb IS NULL
                          THEN custom_attributes - 'ai' ELSE jsonb_set(custom_attributes, '{ai}', %s::jsonb) END
                   WHERE tenant_id = %s AND id = %s""",
                (json.dumps(ai_attr) if ai_attr else None, json.dumps(ai_attr) if ai_attr else None, tenant_id, cid))
        growth.link_ideas(cur, tenant_id, [str(c["id"]) for c in comments], ideas)
    return {"aiClassified": len(ai), "ruleClassified": len(comments) - len(ai), "ideas": len(ideas)}


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
