"""Outrage attribution: link each comment to the video claim it is reacting to.

How it works (deterministic, explainable, fast enough for 10k comments):
1. Each claim gets a term set from its quote + topic, expanded with a small concept
   thesaurus (e.g. "disc" also covers "physical", "blu-ray").
2. Terms shared by most claims (brand names, "game") are down-weighted. They show the
   comment is on-topic, but not which claim it is about.
3. A link needs two specific words shared with the claim, or one plus a related concept word
   or a timestamp that points at the claim ("at 1:14 he says..."). One word or a timestamp
   alone isn't enough.
4. Each comment links to at most one claim: the best score above a threshold.
5. Comments the AI model read use its decision instead (method AI).

Root cause per comment:
- MISINFORMATION: reacting to a MISLEADING / FALSE / UNVERIFIED claim
- VALID_CONCERN: reacting to a FACTUALLY_CORRECT claim (a real product issue to fix)
- UNLINKED: not attributable to any specific claim
"""
import math
import re
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

from app.core.text import tokens
from app.truth.verifier import MISINFO_VERDICTS

CONCEPTS: List[Set[str]] = [
    {"disc", "discs", "disk", "disks", "physical", "digital", "blu-ray", "bluray", "cartridge", "media"},
    {"own", "owning", "ownership", "license", "licence", "rent", "renting", "rental"},
    {"online", "internet", "server", "offline", "connection", "handshake", "drm", "always-online", "check-in"},
    {"save", "cloud", "progress", "backup", "storage", "upload"},
    {"subscription", "plus", "membership", "expire", "expir", "tier", "renew", "monthly"},
    {"price", "cost", "$", "expensive", "cheap", "dollar", "money", "pay", "paid", "overpriced"},
    {"controller", "drift", "stick", "joystick", "potentiometer", "dualsense", "hall-effect"},
    {"battery", "charge", "charging", "hour"},
    {"discontinu", "kill", "end", "dead", "die", "sunset", "stop", "remove", "gone"},
    {"pc", "steam", "adapter", "displayport", "steamvr"},
]

# Brand / category words: they show a comment is on-topic, not which claim it means.
GENERIC_TERMS = set(tokens("sony playstation ps ps5 ps4 ps6 xbox nintendo game games gamer gaming console consoles "
                           "video people company brand product pro slim"))
# Everyday words that appear in claims but say nothing about which claim a comment means.
WEAK_TERMS = set(tokens(
    "buy buying bought next still go going gone down up make making made add adds extra basically entire existing "
    "full get take use play playing want need know think see look say said new old good bad thing things time year "
    "years way day days lot little big really actually literally sold separately edition version their your "
    "thought think right tech technology machine video videos learn learned rights clearly everyone look looked "
    "release released releasing wait talk talking world point thing stuff guy guys man start started"))
_TS_RE = re.compile(r"\b(?:(\d{1,2}):)?(\d{1,2}):(\d{2})\b")
LINK_THRESHOLD = 2.2
# A timestamp counts when it points just after the claim starts (people quote what they just heard).
TS_BEFORE, TS_AFTER = 5, 25


@dataclass
class Link:
    comment_id: str
    claim_id: str
    score: float
    method: str  # AI | LEXICAL | TIMESTAMP
    evidence: str = ""  # matched words, shown in the UI as "why linked"


def _stemmed_concepts() -> List[Set[str]]:
    return [{t for w in group for t in (tokens(w) or [w])} for group in CONCEPTS]


_CONCEPTS = _stemmed_concepts()


def _claim_terms(claim: Dict) -> Dict[str, float]:
    base = set(tokens(f"{claim.get('creator_quote', '')} {claim.get('topic', '')}"))
    weights = {t: 1.0 for t in base}
    for group in _CONCEPTS:
        if base & group:
            for t in group:
                weights.setdefault(t, 0.6)
    return weights


def attribute(claims: List[Dict], comments: List[Dict], ai: Optional[Dict[str, Dict]] = None) -> List[Link]:
    """Link comments to claims.

    `ai` maps comment id -> {"claim": claim id or None, "why": "..."} for comments the AI model read.
    The AI decision wins for those comments (including "no claim"); the rest use lexical rules:
    - at least two specific words shared with the claim itself (not only synonyms or everyday words), or
    - one specific word plus a timestamp that points at the claim.
    """
    if not claims or not comments:
        return []
    ai = ai or {}
    claim_ids = {str(c["id"]) for c in claims}

    claim_terms = {str(c["id"]): _claim_terms(c) for c in claims}
    # Terms appearing in most claims don't discriminate between them.
    term_claim_freq: Counter = Counter()
    for terms in claim_terms.values():
        term_claim_freq.update(terms.keys())
    shared_cutoff = max(2, math.ceil(len(claims) * 0.6))

    comment_tokens = {str(c["id"]): set(tokens(c.get("masked_text") or c.get("text") or "")) for c in comments}
    df: Counter = Counter()
    for toks in comment_tokens.values():
        df.update(toks)
    n = len(comments)

    def idf(term: str) -> float:
        return min(3.0, math.log((n + 1) / (df.get(term, 0) + 1)) + 0.5)

    links: List[Link] = []
    for c in comments:
        cid = str(c["id"])
        if cid in ai:
            reading = ai[cid] or {}
            if reading.get("claim") in claim_ids:
                links.append(Link(cid, reading["claim"], 0.9, "AI", (reading.get("why") or "read by the AI model")[:200]))
            continue

        toks = comment_tokens[cid]
        text = c.get("masked_text") or c.get("text") or ""
        if not toks:
            continue
        ts_claim = _timestamp_match(text, claims)

        best: Optional[tuple] = None
        for claim_id, terms in claim_terms.items():
            score, specific_base, related, matched = 0.0, 0, 0, []
            for t in toks & terms.keys():
                matched.append(t)
                w = terms[t]
                if t in GENERIC_TERMS or t in WEAK_TERMS or term_claim_freq[t] >= shared_cutoff:
                    w *= 0.35
                elif w == 1.0:
                    specific_base += 1
                else:
                    related += 1
                score += w * idf(t)
            near = claim_id == ts_claim
            # Two specific words, or one plus a related concept or a timestamp pointing at the claim.
            if specific_base >= 2 or (specific_base >= 1 and (related >= 1 or near)):
                if near:
                    score += 2.0
                if best is None or score > best[1]:
                    best = (claim_id, score, matched, near)
        if best and best[1] >= LINK_THRESHOLD:
            evidence = _original_words(text, set(best[2]))
            if best[3]:
                evidence = (evidence + " · mentions the claim's timestamp").lstrip(" ·")
            links.append(Link(cid, best[0], round(min(1.0, best[1] / 6.0), 3),
                              "TIMESTAMP" if best[3] else "LEXICAL", evidence))
    return links


def _original_words(text: str, stems: Set[str]) -> str:
    """Turn matched stems back into the words the commenter actually wrote."""
    seen, out = set(), []
    for word in re.findall(r"[A-Za-z0-9$][A-Za-z0-9$'-]*", text or ""):
        toks = tokens(word)
        if toks and toks[0] in stems and word.lower() not in seen:
            seen.add(word.lower())
            out.append(word.lower())
    return ", ".join(out)[:200]


def _timestamp_match(text: str, claims: List[Dict]) -> Optional[str]:
    for m in _TS_RE.finditer(text or ""):
        h = int(m.group(1) or 0)
        secs = h * 3600 + int(m.group(2)) * 60 + int(m.group(3))
        nearest = min(claims, key=lambda cl: abs(int(cl.get("timestamp_seconds") or 0) - secs))
        delta = secs - int(nearest.get("timestamp_seconds") or 0)
        if -TS_BEFORE <= delta <= TS_AFTER:
            return str(nearest["id"])
    return None


def root_cause(verdict: Optional[str]) -> str:
    if not verdict:
        return "UNLINKED"
    return "MISINFORMATION" if verdict in MISINFO_VERDICTS else "VALID_CONCERN"
