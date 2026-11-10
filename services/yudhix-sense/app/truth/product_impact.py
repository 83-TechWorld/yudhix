"""Product impact: how a video's comments affect the product, in one view.

Every number is available two ways: by comment count and by reach. Reach weights a comment
by how many people engaged with it (1 + likes + 2 x replies), so one negative comment with
2,500 likes counts for more than fifty that nobody liked.

Impact score (0-100) = 100 x (negative share of reach)^0.75 x size
  size: 0.6 .. 1.0 with total reach on a log scale (about 10,000 reach is the maximum).
High >= 60, Medium >= 35, otherwise Low.
"""
import math
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from app.core.database import fetch_all
from app.truth.attribution import root_cause
from app.truth.audience import TOPICS

SENTIMENTS = ("POSITIVE", "NEUTRAL", "NEGATIVE")
CAUSES = ("MISINFORMATION", "VALID_CONCERN", "UNLINKED")


def reach(likes: int, replies: int) -> int:
    return 1 + max(0, likes or 0) + 2 * max(0, replies or 0)


def impact_level(score: int) -> str:
    return "HIGH" if score >= 60 else "MEDIUM" if score >= 35 else "LOW"


def compute(rows: List[Dict], now: Optional[datetime] = None) -> Dict:
    """rows: one per comment with like_count, reply_count, platform_created_at, sentiment,
    model_version, verdict (of the linked claim or None), topics (list), plus fields for the top list."""
    now = now or datetime.now(timezone.utc)
    by_count, by_reach = Counter(), Counter()
    cause_count, cause_reach = Counter(), Counter()
    topics: Dict[str, Counter] = defaultdict(Counter)
    ai_count = ai_reach = 0
    days: Dict[str, Counter] = defaultdict(Counter)
    recent = previous = 0
    negatives: List[Dict] = []

    for r in rows:
        s = (r.get("sentiment") or "NEUTRAL").upper()
        s = s if s in SENTIMENTS else "NEUTRAL"
        w = reach(r.get("like_count"), r.get("reply_count"))
        by_count[s] += 1
        by_reach[s] += w
        if (r.get("model_version") or "").startswith("llm/"):
            ai_count += 1
            ai_reach += w
        for t in r.get("topics") or []:
            if t in TOPICS:
                topics[t]["comments"] += 1
                topics[t][s.lower()] += 1
                topics[t]["reach"] += w
                if s == "NEGATIVE":
                    topics[t]["negativeReach"] += w
        created = _aware(r.get("platform_created_at"))
        if created:
            days[created.date().isoformat()][s.lower()] += 1
        if s == "NEGATIVE":
            cause = root_cause(r.get("verdict"))
            cause_count[cause] += 1
            cause_reach[cause] += w
            negatives.append(r)
            if created:
                age = (now - created).days
                if age < 7:
                    recent += 1
                elif age < 14:
                    previous += 1

    total_reach = sum(by_reach.values())
    neg_reach = by_reach["NEGATIVE"]
    neg_share = neg_reach / total_reach if total_reach else 0.0
    size = 0.6 + 0.4 * min(1.0, math.log10(total_reach + 1) / 4) if total_reach else 0.0
    score = round(100 * neg_share ** 0.75 * size) if total_reach else 0

    topic_list = sorted(
        ({"topic": t, "label": TOPICS[t], **{k: c[k] for k in ("comments", "positive", "neutral", "negative",
                                                             "reach", "negativeReach")}}
         for t, c in topics.items()),
        key=lambda x: (-x["negativeReach"], -x["comments"]))

    causes = [{"cause": c, "comments": cause_count[c], "reach": cause_reach[c],
               "share": round(cause_reach[c] / neg_reach, 3) if neg_reach else 0.0} for c in CAUSES]

    top = sorted(negatives, key=lambda r: -reach(r.get("like_count"), r.get("reply_count")))[:5]

    return {
        "score": score,
        "level": impact_level(score),
        "trend": _trend(recent, previous),
        "headline": _headline(neg_share, by_count["NEGATIVE"], topic_list, causes),
        "totals": {"comments": sum(by_count.values()), "reach": total_reach,
                   "likes": sum(max(0, r.get("like_count") or 0) for r in rows)},
        "sentiment": {"byComments": {k.lower(): by_count[k] for k in SENTIMENTS},
                      "byReach": {k.lower(): by_reach[k] for k in SENTIMENTS}},
        "negativeShareOfReach": round(neg_share, 3),
        "negativeByCause": causes,
        "topics": topic_list,
        "timeline": _timeline(days),
        "topNegative": [{
            "id": str(r["id"]), "text": r.get("masked_text") or "", "likes": r.get("like_count") or 0,
            "replies": r.get("reply_count") or 0, "priority": r.get("priority"),
            "cause": root_cause(r.get("verdict")), "claimTimestamp": r.get("claim_timestamp"),
            "topics": [TOPICS[t] for t in (r.get("topics") or []) if t in TOPICS],
        } for r in top],
        "coverage": {"aiComments": ai_count,
                     "aiShareOfReach": round(ai_reach / total_reach, 3) if total_reach else 0.0},
    }


def load(tenant_id: str, video_id: str) -> Dict:
    rows = fetch_all(
        """SELECT c.id, c.masked_text, c.like_count, c.reply_count, c.platform_created_at,
                  ca.sentiment, ca.model_version, ca.priority,
                  vc.verdict, vc.timestamp_start AS claim_timestamp,
                  COALESCE((SELECT array_agg(a.aspect ORDER BY a.id) FROM comment_aspect a
                            WHERE a.tenant_id = c.tenant_id AND a.comment_id = c.id), '{}') AS topics
           FROM comment c
           JOIN comment_analysis ca ON ca.tenant_id = c.tenant_id AND ca.comment_id = c.id
           LEFT JOIN comment_claim_link l ON l.tenant_id = c.tenant_id AND l.comment_id = c.id
           LEFT JOIN video_claim vc ON vc.id = l.claim_id
           WHERE c.tenant_id = %s AND c.custom_attributes->>'video_id' = %s AND c.status = 'ACTIVE'""",
        (tenant_id, video_id))
    return compute(rows)


def _aware(v) -> Optional[datetime]:
    if not isinstance(v, datetime):
        return None
    return v if v.tzinfo else v.replace(tzinfo=timezone.utc)


def _trend(recent: int, previous: int) -> str:
    """Negative comments in the last 7 days vs the 7 days before."""
    if recent + previous < 5:
        return "QUIET"
    if recent > previous * 1.25:
        return "RISING"
    if recent < previous * 0.8:
        return "FADING"
    return "STEADY"


def _timeline(days: Dict[str, Counter]) -> Dict:
    """Daily buckets, or weekly when the comments span more than 60 days."""
    if not days:
        return {"bucket": "day", "points": []}
    keys = sorted(days)
    first, last = datetime.fromisoformat(keys[0]), datetime.fromisoformat(keys[-1])
    weekly = (last - first).days > 60
    buckets: Dict[str, Counter] = defaultdict(Counter)
    for k, c in days.items():
        d = datetime.fromisoformat(k)
        key = (d - timedelta(days=d.weekday())).date().isoformat() if weekly else k
        buckets[key].update(c)
    return {"bucket": "week" if weekly else "day",
            "points": [{"date": k, **{s: buckets[k][s] for s in ("positive", "neutral", "negative")}}
                       for k in sorted(buckets)]}


def _headline(neg_share: float, negatives: int, topics: List[Dict], causes: List[Dict]) -> str:
    if not negatives:
        return "No negative reaction so far."
    parts = [f"{round(neg_share * 100)}% of the reach is negative."]
    top = next((t for t in topics if t["negative"]), None)
    if top:
        parts.append(f"Most of it is about {top['label'].lower()}.")
    misinfo = next(c for c in causes if c["cause"] == "MISINFORMATION")["share"]
    valid = next(c for c in causes if c["cause"] == "VALID_CONCERN")["share"]
    if misinfo >= 0.05 or valid >= 0.05:
        parts.append(f"{round(misinfo * 100)}% traces back to disputed claims, "
                     f"{round(valid * 100)}% to accurate ones (real concerns).")
    return " ".join(parts)
