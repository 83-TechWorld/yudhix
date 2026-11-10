"""Impact score (0-100) and priority band for a comment.

score = 100 x severity^0.8 x engagement x recency
  severity   : how bad the comment is (sentiment, churn risk, toxicity)
  engagement : 0.55 .. 1.0, log-scaled likes + 2 x replies (about 300 likes is the maximum)
  recency    : 0.75 .. 1.0, decays over ~2 weeks

Calibration: a fresh negative comment with ~100 likes is P1, the same comment a month
later is P2, and a negative comment nobody liked is P3.
Comments reacting to misinformation get a 10% boost because they spread the false claim.
"""
import math
from datetime import datetime, timezone
from typing import Optional

SEVERITY = {"NEGATIVE": 0.6, "MIXED": 0.45, "NEUTRAL": 0.3, "POSITIVE": 0.1}


def impact_score(sentiment: str, churn_risk: float, likes: int, replies: int,
                 created_at: Optional[datetime], toxic: bool = False, misinformation: bool = False) -> float:
    severity = SEVERITY.get((sentiment or "NEUTRAL").upper(), 0.3)
    if (sentiment or "").upper() == "NEGATIVE":
        severity += 0.4 * max(0.0, min(1.0, churn_risk or 0.0))
    if toxic:
        severity = min(1.0, severity + 0.1)

    engagement = min(1.0, math.log10(1 + max(0, likes or 0) + 2 * max(0, replies or 0)) / 2.5)

    recency = 1.0
    if created_at:
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
        age_days = max(0.0, (datetime.now(timezone.utc) - created_at).total_seconds() / 86400)
        recency = max(0.0, math.exp(-age_days / 14))

    score = 100 * min(1.0, severity) ** 0.8 * (0.55 + 0.45 * engagement) * (0.75 + 0.25 * recency)
    if misinformation:
        score *= 1.1
    return round(min(100.0, score), 2)


def priority_band(score: float) -> str:
    if score >= 80:
        return "P1"
    if score >= 50:
        return "P2"
    return "P3"
