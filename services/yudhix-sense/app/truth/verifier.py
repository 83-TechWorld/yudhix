"""Fact-check a claim against the retrieved brand knowledge.

Verdicts: FACTUALLY_CORRECT | MISLEADING | FALSE | UNVERIFIED_SPECULATION.
The LLM judges when available, inside guards that stop it from making things up:
  1. No evidence, no AI: if retrieval found nothing close, the claim is UNVERIFIED without asking the model.
  2. Quote check: the model must copy the source sentence it relied on, and that sentence has to really be
     in the official text. An invented quote rejects the AI's verdict.
  3. Number check: figures in the claim are compared with the source by code. "Supports" with different
     figures becomes MISLEADING and goes to review.
  4. Second opinion (cloud AI, or SECOND_OPINION=always): a second reading with the sources reordered.
     If the two disagree, the claim is flagged "Needs review" instead of trusting either.
A person can override any verdict; re-checks never overwrite a human verdict. The heuristic fallback is deliberately conservative: it only
marks a claim MISLEADING when the creator states an absolute ("forcing", "wipes", "never")
that the official text explicitly negates, and otherwise leaves it UNVERIFIED for a human.
"""
import re
from dataclasses import dataclass, replace
from difflib import SequenceMatcher
from typing import List, Optional, Tuple

from app.core import config, llm
from app.core.text import tokens
from app.truth.retrieval import Hit

VERDICTS = {"FACTUALLY_CORRECT", "MISLEADING", "FALSE", "UNVERIFIED_SPECULATION"}
MISINFO_VERDICTS = {"MISLEADING", "FALSE", "UNVERIFIED_SPECULATION"}

ABSOLUTE = re.compile(r"\b(always|never|forc\w*|requir\w*|every|completely|permanently|immediately|"
                      r"wipes?|delet\w*|revok\w*|kill\w*|end(s|ing)?|discontinu\w*|ban\w*|lose|lost|"
                      r"no longer|useless|basically)\b", re.I)
FUTURE = re.compile(r"\b(will|going to|plans? to|next[- ]gen|next console|soon|rumou?r\w*|leak\w*)\b", re.I)
NEGATION = re.compile(r"\b(not|no|never|does not|do not|is not|are not|remain\w*|retain\w*|continu\w*|"
                      r"fully committed|without|grace period|only)\b", re.I)
NUMBER = re.compile(r"\$?\d+(?:[.,]\d+)?%?")


@dataclass
class Verdict:
    verdict: str
    confidence: float
    analysis: str
    knowledge: Optional[dict]
    method: str  # LLM | HEURISTIC | HUMAN
    source_quote: Optional[str] = None   # the sentence of the official source the verdict rests on
    needs_review: bool = False
    review_reason: Optional[str] = None
    relation: Optional[str] = None


# Retrieval floor: below both, the knowledge base doesn't cover the claim and the model isn't asked.
MIN_OVERLAP = 0.2
MIN_SIMILARITY = 0.55
QUOTE_MATCH = 0.8


def has_evidence(hits: List[Hit]) -> bool:
    return any(h.overlap >= MIN_OVERLAP or h.similarity >= MIN_SIMILARITY for h in hits)


def verify(claim: str, hits: List[Hit], use_ai: bool = True) -> Verdict:
    """use_ai=False: rule-based check only (e.g. when the analysis ran out of AI time)."""
    if not use_ai:
        return _verify_heuristic(claim, hits)
    if not hits or not has_evidence(hits):
        return _verify_heuristic(claim, hits)               # guard 1: no evidence, no AI
    first = _verify_with_llm(claim, hits)
    if not first:
        return _verify_heuristic(claim, hits)
    if _second_opinion_on() and first.method == "LLM":       # guard 4
        second = _verify_with_llm(claim, list(reversed(hits)))
        if second and second.relation != first.relation:
            return replace(first, confidence=min(first.confidence, 0.5), needs_review=True,
                           review_reason=f"Two AI readings disagreed ({_rel(first.relation)} vs {_rel(second.relation)}).")
    return first


def _second_opinion_on() -> bool:
    mode = config.SECOND_OPINION
    return mode == "always" or (mode == "cloud" and llm.is_cloud())


def _rel(relation: Optional[str]) -> str:
    return (relation or "unknown").replace("_", " ").lower()


def quote_in_source(quote: str, statement: str) -> bool:
    """Guard 2: is the quoted sentence really in the official text? Allows small wording differences."""
    q = tokens(quote)
    if len(q) < 3:
        return False
    doc = set(tokens(statement))
    if sum(1 for t in q if t in doc) / len(q) >= QUOTE_MATCH:
        return True
    norm = lambda t: " ".join(t.lower().split())  # noqa: E731
    m = SequenceMatcher(None, norm(quote), norm(statement)).find_longest_match()
    return m.size >= 0.85 * len(norm(quote))


def numbers_conflict(claim: str, statement: str) -> bool:
    """Guard 3: both state figures and none of the claim's figures appear in the source."""
    c, d = _numbers(claim), _numbers(statement)
    return bool(c and d and not (c & d))


# A figure with its unit ("2TB", "$79.99", "60 fps"), but not digits inside names like "PS5" or "M.2".
FIGURE = re.compile(r"(?<![A-Za-z\d.])\$?(\d+(?:[.,]\d+)?)\s?(%|tb|gb|mb|hz|fps|k\b|p\b|hours?|days?|months?|years?)?",
                    re.I)


def _numbers(text: str) -> set:
    return {(n.replace(",", "") + (u or "").lower().rstrip("s")) for n, u in FIGURE.findall(text or "")}


def _ground(source_says: str, hits: List[Hit], idx: int) -> Tuple[Optional[dict], bool]:
    """The source that really contains the quote (the model sometimes cites the wrong number)."""
    order = [idx] + [i for i in range(len(hits)) if i != idx] if 0 <= idx < len(hits) else list(range(len(hits)))
    for i in order:
        if quote_in_source(source_says, str(hits[i].doc.get("official_statement") or "")):
            return hits[i].doc, True
    return (hits[idx].doc if 0 <= idx < len(hits) else hits[0].doc), False


RELATION_TO_VERDICT = {
    "SUPPORTS": "FACTUALLY_CORRECT",
    "CONTRADICTS": "FALSE",
    "PARTIALLY_CONTRADICTS": "MISLEADING",
    "NOT_ADDRESSED": "UNVERIFIED_SPECULATION",
}


def _verify_with_llm(claim: str, hits: List[Hit]) -> Optional[Verdict]:
    """Small local models judge "relation to source" far more reliably than they pick a verdict
    label directly, so the model describes the relation and code maps it to a verdict."""
    sources = "\n".join(
        f"[{i}] {h.doc.get('document_title')} ({h.doc.get('clause_ref') or 'n/a'}): {h.doc.get('official_statement')}"
        for i, h in enumerate(hits))
    prompt = f"""Compare a creator's claim with a brand's OFFICIAL sources. Use ONLY the sources, not your own knowledge.

Claim: "{claim}"

Official sources:
{sources}

Steps:
1. Find the source most relevant to the claim and copy the sentence that matters into "source_says".
   If no source talks about the specific fact in the claim (for example a price, a date or a feature the
   sources never mention), set relation to NOT_ADDRESSED.
2. relation:
   SUPPORTS              - the source states the same thing
   CONTRADICTS           - the source states the opposite
   PARTIALLY_CONTRADICTS - partly true but exaggerated, missing conditions, or overstated
   NOT_ADDRESSED         - the sources don't cover it
3. is_prediction: true if the claim is about what will happen in the future.

Return JSON: {{"source_index": 0, "source_says": "...", "relation": "...", "is_prediction": false,
"confidence": 0.0-1.0, "analysis": "2 short sentences in plain English for a brand manager"}}
"""
    data = llm.generate_json(prompt, max_tokens=320)  # a short answer: relation, quote, two sentences
    if not isinstance(data, dict):
        return None
    relation = str(data.get("relation", "")).upper().strip().replace(" ", "_")
    if relation not in RELATION_TO_VERDICT:
        return None
    verdict = RELATION_TO_VERDICT[relation]
    if data.get("is_prediction") is True and relation != "SUPPORTS":
        verdict = "UNVERIFIED_SPECULATION" if relation == "NOT_ADDRESSED" else "MISLEADING"
    try:
        idx = int(data.get("source_index", 0))
    except (TypeError, ValueError):
        idx = 0
    try:
        confidence = max(0.05, min(0.95, float(data.get("confidence", 0.7))))
    except (TypeError, ValueError):
        confidence = 0.7

    analysis = str(data.get("analysis") or "").strip() or "Checked against official documentation."
    if relation == "NOT_ADDRESSED":
        return Verdict(verdict, confidence, analysis, None, "LLM", relation=relation)

    # Guard 2: the evidence must be a real sentence from the official text.
    source_says = " ".join(str(data.get("source_says") or "").split())[:600]
    doc, grounded = _ground(source_says, hits, idx)
    if not grounded:
        fallback = _verify_heuristic(claim, hits)
        return replace(fallback, needs_review=True, relation=relation,
                       review_reason="The AI's quoted evidence isn't in the official source, so its verdict was "
                                     "not used. Rule-based result shown.")
    statement = str(doc.get("official_statement") or "")
    needs_review, reason = False, None

    # Guard 3: figures are compared by code, not trusted to the model.
    if verdict == "FACTUALLY_CORRECT" and numbers_conflict(claim, statement):
        verdict, confidence = "MISLEADING", min(confidence, 0.6)
        needs_review, reason = True, "The AI said the source supports this, but the figures differ."

    # The claim states an absolute ("never", "forcing") that the source qualifies.
    heuristic = _verify_heuristic(claim, hits)
    if verdict == "FACTUALLY_CORRECT" and heuristic.verdict == "MISLEADING":
        verdict, confidence = "MISLEADING", min(confidence, 0.6)

    return Verdict(verdict, confidence, analysis, doc, "LLM", source_quote=source_says,
                   needs_review=needs_review, review_reason=reason, relation=relation)


def _verify_heuristic(claim: str, hits: List[Hit]) -> Verdict:
    best = hits[0] if hits else None
    if FUTURE.search(claim) and (not best or best.overlap < 0.5):
        return Verdict("UNVERIFIED_SPECULATION", 0.55,
                       "This is a prediction about the future. No official document confirms it.",
                       best.doc if best else None, "HEURISTIC")
    if not best or best.overlap < 0.2:
        return Verdict("UNVERIFIED_SPECULATION", 0.4,
                       "No official document in the knowledge base covers this claim. Add one, or review it manually.",
                       None, "HEURISTIC")

    statement = str(best.doc.get("official_statement") or "")
    claim_numbers = set(NUMBER.findall(claim))
    doc_numbers = set(NUMBER.findall(statement))
    if claim_numbers and claim_numbers & doc_numbers:
        return Verdict("FACTUALLY_CORRECT", min(0.9, 0.6 + best.overlap / 2),
                       f"The figures match the official source: \"{_short(statement)}\"", best.doc, "HEURISTIC")
    if claim_numbers and doc_numbers and not (claim_numbers & doc_numbers):
        return Verdict("MISLEADING", 0.6,
                       f"The figures differ from the official source, which says: \"{_short(statement)}\"",
                       best.doc, "HEURISTIC")
    if ABSOLUTE.search(claim) and NEGATION.search(statement):
        return Verdict("MISLEADING", min(0.85, 0.55 + best.overlap / 2),
                       f"The claim states an absolute, but the official source qualifies it: \"{_short(statement)}\"",
                       best.doc, "HEURISTIC")
    if best.overlap >= 0.45:
        return Verdict("FACTUALLY_CORRECT", 0.55 + best.overlap / 4,
                       f"Consistent with the official source: \"{_short(statement)}\"", best.doc, "HEURISTIC")
    return Verdict("UNVERIFIED_SPECULATION", 0.45,
                   f"Partly related to \"{best.doc.get('document_title')}\", but not clearly confirmed. Needs a human check.",
                   best.doc, "HEURISTIC")


def _short(text: str, n: int = 220) -> str:
    text = " ".join(text.split())
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"
