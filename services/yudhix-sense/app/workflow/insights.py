"""KPIs for the Track screen."""
from typing import Dict, Optional

from app.core.database import fetch_all, fetch_one


def summary(tenant_id: str, video_id: Optional[str] = None) -> Dict:
    vf = "AND c.custom_attributes->>'video_id' = %s" if video_id else ""
    vp = (video_id,) if video_id else ()

    comments = fetch_one(
        f"""SELECT count(*) AS total,
                   count(*) FILTER (WHERE ca.sentiment = 'NEGATIVE') AS negative,
                   count(*) FILTER (WHERE ca.sentiment = 'POSITIVE') AS positive,
                   count(*) FILTER (WHERE ca.sentiment = 'NEUTRAL') AS neutral,
                   count(*) FILTER (WHERE ca.priority = 'P1') AS p1,
                   count(*) FILTER (WHERE ca.priority = 'P2') AS p2,
                   count(*) FILTER (WHERE ca.priority = 'P3') AS p3,
                   count(*) FILTER (WHERE ca.sentiment = 'NEGATIVE'
                                    AND vc.verdict IN ('MISLEADING', 'FALSE', 'UNVERIFIED_SPECULATION')) AS misinfo_negative,
                   count(*) FILTER (WHERE ca.sentiment = 'NEGATIVE' AND vc.verdict = 'FACTUALLY_CORRECT') AS valid_negative
            FROM comment c
            JOIN comment_analysis ca ON ca.tenant_id = c.tenant_id AND ca.comment_id = c.id
            LEFT JOIN comment_claim_link l ON l.tenant_id = c.tenant_id AND l.comment_id = c.id
            LEFT JOIN video_claim vc ON vc.id = l.claim_id
            WHERE c.tenant_id = %s AND c.status = 'ACTIVE' {vf}""", (tenant_id, *vp))

    replies = fetch_one(
        f"""SELECT count(*) FILTER (WHERE r.status = 'DRAFT') AS draft,
                   count(*) FILTER (WHERE r.status = 'IN_REVIEW') AS in_review,
                   count(*) FILTER (WHERE r.status = 'REJECTED') AS rejected,
                   count(*) FILTER (WHERE r.status = 'APPROVED') AS approved,
                   count(*) FILTER (WHERE r.status = 'POSTED') AS posted,
                   count(*) FILTER (WHERE r.status <> 'POSTED' AND r.sla_due_at < now()) AS sla_breached,
                   avg(EXTRACT(EPOCH FROM (r.approved_at - r.submitted_at)) / 3600)
                       FILTER (WHERE r.approved_at IS NOT NULL AND r.submitted_at IS NOT NULL) AS avg_review_hours
            FROM reply r JOIN comment c ON c.tenant_id = r.tenant_id AND c.id = r.comment_id
            WHERE r.tenant_id = %s {vf}""", (tenant_id, *vp))

    outcomes = fetch_one(
        f"""SELECT count(*) FILTER (WHERE ro.outcome = 'IMPROVED') AS improved,
                   count(*) FILTER (WHERE ro.outcome = 'NEUTRAL') AS neutral,
                   count(*) FILTER (WHERE ro.outcome = 'WORSENED') AS worsened,
                   count(*) FILTER (WHERE ro.outcome IS NULL) AS pending
            FROM reply_outcome ro JOIN comment c ON c.tenant_id = ro.tenant_id AND c.id = ro.comment_id
            WHERE ro.tenant_id = %s {vf}""", (tenant_id, *vp))

    claims = fetch_one(
        f"""SELECT count(*) AS total,
                   count(*) FILTER (WHERE vc.verdict = 'FACTUALLY_CORRECT') AS correct,
                   count(*) FILTER (WHERE vc.verdict = 'MISLEADING') AS misleading,
                   count(*) FILTER (WHERE vc.verdict = 'FALSE') AS false_count,
                   count(*) FILTER (WHERE vc.verdict = 'UNVERIFIED_SPECULATION') AS unverified,
                   count(DISTINCT v.id) AS videos
            FROM video_truth_analysis v LEFT JOIN video_claim vc ON vc.video_analysis_id = v.id
            WHERE v.tenant_id = %s {"AND v.video_id = %s" if video_id else ""}""", (tenant_id, *vp))

    evaluated = int(outcomes["improved"] + outcomes["neutral"] + outcomes["worsened"])
    negative = int(comments["negative"])
    return {
        "videos": int(claims["videos"]),
        "claims": {"total": int(claims["total"]), "correct": int(claims["correct"]),
                   "misleading": int(claims["misleading"]), "false": int(claims["false_count"]),
                   "unverified": int(claims["unverified"])},
        "comments": {k: int(comments[k]) for k in ("total", "negative", "positive", "neutral", "p1", "p2", "p3")},
        "misinformationShareOfNegative": round(int(comments["misinfo_negative"]) / negative, 3) if negative else 0.0,
        "validConcernShareOfNegative": round(int(comments["valid_negative"]) / negative, 3) if negative else 0.0,
        "replies": {k: int(replies[k] or 0) for k in ("draft", "in_review", "rejected", "approved", "posted",
                                                      "sla_breached")},
        "avgReviewHours": round(float(replies["avg_review_hours"]), 2) if replies["avg_review_hours"] else None,
        "outcomes": {k: int(outcomes[k]) for k in ("improved", "neutral", "worsened", "pending")},
        "turnaroundRate": round(int(outcomes["improved"]) / evaluated, 3) if evaluated else None,
    }


def sentiment_trend(tenant_id: str, video_id: Optional[str] = None, days: int = 60) -> list:
    vf = "AND c.custom_attributes->>'video_id' = %s" if video_id else ""
    rows = fetch_all(
        f"""SELECT date_trunc('day', c.platform_created_at)::date AS day,
                   count(*) FILTER (WHERE ca.sentiment = 'POSITIVE') AS positive,
                   count(*) FILTER (WHERE ca.sentiment = 'NEGATIVE') AS negative,
                   count(*) FILTER (WHERE ca.sentiment = 'NEUTRAL') AS neutral
            FROM comment c JOIN comment_analysis ca ON ca.tenant_id = c.tenant_id AND ca.comment_id = c.id
            WHERE c.tenant_id = %s AND c.status = 'ACTIVE' {vf}
              AND c.platform_created_at >= (SELECT max(platform_created_at) FROM comment WHERE tenant_id = %s)
                                            - make_interval(days => %s)
            GROUP BY 1 ORDER BY 1""",
        (tenant_id, *((video_id,) if video_id else ()), tenant_id, days))
    return [{"day": r["day"].isoformat(), "positive": int(r["positive"]), "negative": int(r["negative"]),
             "neutral": int(r["neutral"])} for r in rows]


def video_leaderboard(tenant_id: str) -> list:
    rows = fetch_all(
        """SELECT v.video_id, v.video_title, v.channel_title, v.factual_accuracy_score, v.misleading_claims_count,
                  v.total_claims,
                  (SELECT count(*) FROM comment c WHERE c.tenant_id = v.tenant_id
                       AND c.custom_attributes->>'video_id' = v.video_id AND c.status = 'ACTIVE') AS comments,
                  (SELECT count(*) FROM reply r JOIN comment c ON c.id = r.comment_id
                       WHERE r.tenant_id = v.tenant_id AND r.status = 'POSTED'
                         AND c.custom_attributes->>'video_id' = v.video_id) AS replies_posted
           FROM video_truth_analysis v WHERE v.tenant_id = %s
           ORDER BY v.misleading_claims_count DESC, v.factual_accuracy_score ASC""", (tenant_id,))
    return [{"videoId": r["video_id"], "title": r["video_title"], "channel": r["channel_title"],
             "factualAccuracy": float(r["factual_accuracy_score"] or 0), "misleadingClaims": r["misleading_claims_count"],
             "totalClaims": r["total_claims"], "comments": int(r["comments"]), "repliesPosted": int(r["replies_posted"])}
            for r in rows]
