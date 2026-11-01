"""Fact-check a claim against the retrieved brand knowledge.

Verdicts: FACTUALLY_CORRECT | MISLEADING | FALSE | UNVERIFIED_SPECULATION.
The LLM judges when available. The heuristic fallback is deliberately conservative: it only
marks a claim MISLEADING when the creator states an absolute ("forcing", "wipes", "never")
that the official text explicitly negates, and otherwise leaves it UNVERIFIED for a human.
"""
import re
from dataclasses import dataclass
from typing import List, Optional

from app.core import llm
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
    method: str  # LLM | HEURISTIC


def verify(claim: str, hits: List[Hit]) -> Verdict:
    result = _verify_with_llm(claim, hits) if hits else None
    return result or _verify_heuristic(claim, hits)


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
    data = llm.generate_json(prompt)
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
    doc = hits[idx].doc if 0 <= idx < len(hits) else hits[0].doc
    try:
        confidence = max(0.05, min(0.95, float(data.get("confidence", 0.7))))
    except (TypeError, ValueError):
        confidence = 0.7

    # Guardrail: the model said "supports" but the claim states an absolute the source negates.
    heuristic = _verify_heuristic(claim, hits)
    if verdict == "FACTUALLY_CORRECT" and heuristic.verdict == "MISLEADING":
        verdict, confidence = "MISLEADING", min(confidence, 0.6)

    analysis = str(data.get("analysis") or "").strip() or "Checked against official documentation."
    return Verdict(verdict, confidence, analysis, None if relation == "NOT_ADDRESSED" else doc, "LLM")


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
