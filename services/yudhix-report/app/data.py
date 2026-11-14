"""Read-only queries. Each one covers all selected workspaces at once and groups by workspace.

Comments and reviews count in a period by when they were written (platform_created_at). Videos and
claims count by when Yudhix analyzed them. Replies by when they were drafted. Ideas, AI settings,
listings and the team are shown as they are now.
"""
from collections import defaultdict
from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from app.catalog import Window
from app.db import fetch_all
from app import config

BAD_VERDICTS = ("MISLEADING", "FALSE", "UNVERIFIED_SPECULATION")


def _n(v) -> int:
    return int(v or 0)


def _f(v) -> Optional[float]:
    return float(v) if v is not None else None


def comments(ids: List[str], w: Window) -> Dict[str, Dict[str, Dict]]:
    """{workspace: {platform: counts}} for comments and reviews written in the window."""
    rows = fetch_all(
        """SELECT c.tenant_id::text AS ws, c.platform,
                  count(*) AS total,
                  count(*) FILTER (WHERE ca.sentiment = 'POSITIVE') AS positive,
                  count(*) FILTER (WHERE ca.sentiment = 'NEGATIVE') AS negative,
                  count(*) FILTER (WHERE ca.sentiment IS NULL OR ca.sentiment NOT IN ('POSITIVE', 'NEGATIVE')) AS neutral,
                  count(*) FILTER (WHERE ca.sentiment = 'NEGATIVE' AND EXISTS (
                      SELECT 1 FROM comment_claim_link l JOIN video_claim vc ON vc.id = l.claim_id
                      WHERE l.tenant_id = c.tenant_id AND l.comment_id = c.id
                        AND vc.verdict IN ('MISLEADING', 'FALSE', 'UNVERIFIED_SPECULATION'))) AS misinfo_negative,
                  count(*) FILTER (WHERE ca.model_version LIKE 'llm/%%' OR ca.model_version LIKE 'ollama/%%') AS ai_read,
                  count(*) FILTER (WHERE ca.comment_id IS NULL) AS unread,
                  count(*) FILTER (WHERE ca.priority = 'P1') AS p1,
                  coalesce(sum(c.like_count), 0) AS likes
           FROM comment c
           LEFT JOIN comment_analysis ca ON ca.tenant_id = c.tenant_id AND ca.comment_id = c.id
           WHERE c.tenant_id = ANY(%s::uuid[]) AND c.status = 'ACTIVE'
             AND c.platform_created_at >= %s AND c.platform_created_at < %s
           GROUP BY 1, 2""", (ids, w.lower, w.end))
    out: Dict[str, Dict[str, Dict]] = defaultdict(dict)
    for r in rows:
        out[r["ws"]][r["platform"]] = {k: _n(r[k]) for k in (
            "total", "positive", "negative", "neutral", "misinfo_negative", "ai_read", "unread", "p1", "likes")}
    return out


def trend(ids: List[str], w: Window) -> List[Dict]:
    """Sentiment per day / week / month across all selected workspaces."""
    grain = w.grain
    if w.start is None:
        span = fetch_all("""SELECT min(platform_created_at) AS lo FROM comment
                            WHERE tenant_id = ANY(%s::uuid[]) AND status = 'ACTIVE'""", (ids,))
        lo = span[0]["lo"] if span else None
        if lo and (w.end - lo).days > 3 * 365:
            grain = "quarter"
    rows = fetch_all(
        f"""SELECT date_trunc('{grain}', c.platform_created_at)::date AS bucket,
                   count(*) FILTER (WHERE ca.sentiment = 'POSITIVE') AS positive,
                   count(*) FILTER (WHERE ca.sentiment = 'NEGATIVE') AS negative,
                   count(*) FILTER (WHERE ca.sentiment IS NULL OR ca.sentiment NOT IN ('POSITIVE', 'NEGATIVE')) AS neutral
            FROM comment c
            LEFT JOIN comment_analysis ca ON ca.tenant_id = c.tenant_id AND ca.comment_id = c.id
            WHERE c.tenant_id = ANY(%s::uuid[]) AND c.status = 'ACTIVE'
              AND c.platform_created_at >= %s AND c.platform_created_at < %s
            GROUP BY 1 ORDER BY 1""", (ids, w.lower, w.end))
    got = {r["bucket"]: r for r in rows}
    if not rows:
        return []
    first = _floor(w.start.date(), grain) if w.start else rows[0]["bucket"]
    out, b, last = [], first, _floor(w.end.date(), grain)
    while b <= last and len(out) < 400:
        r = got.get(b, {})
        out.append({"bucket": b, "grain": grain, "positive": _n(r.get("positive")),
                    "negative": _n(r.get("negative")), "neutral": _n(r.get("neutral"))})
        b = _next(b, grain)
    return out


def _floor(d: date, grain: str) -> date:
    if grain == "week":
        return d - timedelta(days=d.weekday())
    if grain == "month":
        return d.replace(day=1)
    if grain == "quarter":
        return d.replace(month=3 * ((d.month - 1) // 3) + 1, day=1)
    return d


def _next(d: date, grain: str) -> date:
    if grain == "day":
        return d + timedelta(days=1)
    if grain == "week":
        return d + timedelta(days=7)
    months = 3 if grain == "quarter" else 1
    m = d.month - 1 + months
    return date(d.year + m // 12, m % 12 + 1, 1)


def claims(ids: List[str], w: Window) -> Dict[str, Dict]:
    rows = fetch_all(
        """SELECT v.tenant_id::text AS ws,
                  count(DISTINCT v.id) AS videos,
                  count(vc.id) AS total,
                  count(vc.id) FILTER (WHERE vc.verdict = 'FACTUALLY_CORRECT') AS correct,
                  count(vc.id) FILTER (WHERE vc.verdict = 'MISLEADING') AS misleading,
                  count(vc.id) FILTER (WHERE vc.verdict = 'FALSE') AS false_count,
                  count(vc.id) FILTER (WHERE vc.verdict = 'UNVERIFIED_SPECULATION') AS unverified,
                  count(vc.id) FILTER (WHERE vc.needs_review) AS needs_review,
                  count(vc.id) FILTER (WHERE vc.verification_method = 'LLM') AS by_ai,
                  count(vc.id) FILTER (WHERE vc.verification_method = 'HEURISTIC') AS by_rules,
                  count(vc.id) FILTER (WHERE vc.verification_method = 'HUMAN' OR vc.reviewed_by IS NOT NULL) AS by_human,
                  count(vc.id) FILTER (WHERE vc.verification_method = 'SEEDED') AS seeded
           FROM video_truth_analysis v LEFT JOIN video_claim vc ON vc.video_analysis_id = v.id
           WHERE v.tenant_id = ANY(%s::uuid[])
             AND coalesce(v.analyzed_at, v.created_at) >= %s AND coalesce(v.analyzed_at, v.created_at) < %s
           GROUP BY 1""", (ids, w.lower, w.end))
    acc = fetch_all(
        """SELECT tenant_id::text AS ws, avg(factual_accuracy_score) AS accuracy, coalesce(sum(view_count), 0) AS views,
                  coalesce(sum(view_count) FILTER (WHERE misleading_claims_count > 0), 0) AS views_misleading,
                  count(*) FILTER (WHERE misleading_claims_count > 0) AS videos_misleading
           FROM video_truth_analysis
           WHERE tenant_id = ANY(%s::uuid[])
             AND coalesce(analyzed_at, created_at) >= %s AND coalesce(analyzed_at, created_at) < %s
           GROUP BY 1""", (ids, w.lower, w.end))
    by = {a["ws"]: a for a in acc}
    out = {}
    for r in rows:
        a = by.get(r["ws"], {})
        out[r["ws"]] = {
            "videos": _n(r["videos"]), "total": _n(r["total"]), "correct": _n(r["correct"]),
            "misleading": _n(r["misleading"]), "false": _n(r["false_count"]), "unverified": _n(r["unverified"]),
            "needsReview": _n(r["needs_review"]), "byAi": _n(r["by_ai"]), "byRules": _n(r["by_rules"]),
            "byHuman": _n(r["by_human"]), "seeded": _n(r["seeded"]),
            "accuracy": _f(a.get("accuracy")), "views": _n(a.get("views")),
            "viewsMisleading": _n(a.get("views_misleading")), "videosMisleading": _n(a.get("videos_misleading")),
        }
    return out


def risky_videos(ids: List[str], w: Window, limit: int = config.TABLE_ROWS) -> List[Dict]:
    rows = fetch_all(
        """SELECT v.tenant_id::text AS ws, v.video_id, v.video_title, v.channel_title, v.view_count,
                  v.factual_accuracy_score, v.misleading_claims_count, v.total_claims,
                  (SELECT count(*) FROM comment c JOIN comment_analysis ca ON ca.tenant_id = c.tenant_id AND ca.comment_id = c.id
                    WHERE c.tenant_id = v.tenant_id AND c.custom_attributes->>'video_id' = v.video_id
                      AND c.status = 'ACTIVE' AND ca.sentiment = 'NEGATIVE') AS negative_comments
           FROM video_truth_analysis v
           WHERE v.tenant_id = ANY(%s::uuid[])
             AND coalesce(v.analyzed_at, v.created_at) >= %s AND coalesce(v.analyzed_at, v.created_at) < %s
           ORDER BY v.misleading_claims_count DESC, v.view_count DESC NULLS LAST, v.factual_accuracy_score ASC
           LIMIT %s""", (ids, w.lower, w.end, limit))
    return [{"ws": r["ws"], "videoId": r["video_id"], "title": r["video_title"] or r["video_id"],
             "channel": r["channel_title"], "views": r["view_count"], "accuracy": _f(r["factual_accuracy_score"]),
             "misleading": _n(r["misleading_claims_count"]), "claims": _n(r["total_claims"]),
             "negativeComments": _n(r["negative_comments"])} for r in rows]


def products(ids: List[str], w: Window) -> List[Dict]:
    rows = fetch_all(
        """SELECT p.tenant_id::text AS ws, p.id::text AS id, p.name, p.category,
                  count(c.id) FILTER (WHERE c.platform = 'YOUTUBE') AS yt,
                  count(c.id) FILTER (WHERE c.platform = 'YOUTUBE' AND ca.sentiment = 'POSITIVE') AS yt_pos,
                  count(c.id) FILTER (WHERE c.platform = 'YOUTUBE' AND ca.sentiment = 'NEGATIVE') AS yt_neg,
                  count(c.id) FILTER (WHERE c.platform = 'AMAZON') AS az,
                  count(c.id) FILTER (WHERE c.platform = 'AMAZON' AND ca.sentiment = 'POSITIVE') AS az_pos,
                  count(c.id) FILTER (WHERE c.platform = 'AMAZON' AND ca.sentiment = 'NEGATIVE') AS az_neg,
                  (SELECT avg(l.rating) FROM product_listing l WHERE l.tenant_id = p.tenant_id AND l.product_id = p.id
                     AND l.rating IS NOT NULL) AS rating,
                  (SELECT coalesce(sum(l.ratings_count), 0) FROM product_listing l
                     WHERE l.tenant_id = p.tenant_id AND l.product_id = p.id) AS ratings_count,
                  (SELECT count(*) FROM product_listing l WHERE l.tenant_id = p.tenant_id AND l.product_id = p.id) AS listings
           FROM product p
           LEFT JOIN comment c ON c.tenant_id = p.tenant_id AND c.product_id = p.id AND c.status = 'ACTIVE'
                AND c.platform_created_at >= %s AND c.platform_created_at < %s
           LEFT JOIN comment_analysis ca ON ca.tenant_id = c.tenant_id AND ca.comment_id = c.id
           WHERE p.tenant_id = ANY(%s::uuid[]) AND coalesce(p.active, true) AND NOT coalesce(p.is_competitor, false)
           GROUP BY p.tenant_id, p.id, p.name, p.category
           ORDER BY count(c.id) DESC, p.name""", (w.lower, w.end, ids))
    return [{"ws": r["ws"], "id": r["id"], "name": r["name"], "category": r["category"],
             "youtube": {"total": _n(r["yt"]), "positive": _n(r["yt_pos"]), "negative": _n(r["yt_neg"])},
             "amazon": {"total": _n(r["az"]), "positive": _n(r["az_pos"]), "negative": _n(r["az_neg"])},
             "rating": round(float(r["rating"]), 1) if r["rating"] is not None else None,
             "ratingsCount": _n(r["ratings_count"]), "listings": _n(r["listings"])} for r in rows]


def replies(ids: List[str], w: Window) -> Dict[str, Dict]:
    rows = fetch_all(
        """SELECT r.tenant_id::text AS ws,
                  count(*) AS total,
                  count(*) FILTER (WHERE r.status = 'DRAFT') AS draft,
                  count(*) FILTER (WHERE r.status = 'IN_REVIEW') AS in_review,
                  count(*) FILTER (WHERE r.status = 'APPROVED') AS approved,
                  count(*) FILTER (WHERE r.status = 'POSTED') AS posted,
                  count(*) FILTER (WHERE r.status = 'REJECTED') AS rejected,
                  count(*) FILTER (WHERE r.status NOT IN ('POSTED', 'REJECTED') AND r.sla_due_at < now()) AS sla_breached,
                  avg(EXTRACT(EPOCH FROM (r.approved_at - r.submitted_at)) / 3600)
                      FILTER (WHERE r.approved_at IS NOT NULL AND r.submitted_at IS NOT NULL) AS review_hours,
                  avg(EXTRACT(EPOCH FROM (r.posted_at - r.created_at)) / 3600)
                      FILTER (WHERE r.posted_at IS NOT NULL) AS post_hours
           FROM reply r
           WHERE r.tenant_id = ANY(%s::uuid[]) AND r.created_at >= %s AND r.created_at < %s
           GROUP BY 1""", (ids, w.lower, w.end))
    outcomes = fetch_all(
        """SELECT ro.tenant_id::text AS ws,
                  count(*) FILTER (WHERE ro.outcome = 'IMPROVED') AS improved,
                  count(*) FILTER (WHERE ro.outcome = 'NEUTRAL') AS unchanged,
                  count(*) FILTER (WHERE ro.outcome = 'WORSENED') AS worsened,
                  count(*) FILTER (WHERE ro.outcome IS NULL) AS pending
           FROM reply_outcome ro JOIN reply r ON r.id = ro.reply_id
           WHERE ro.tenant_id = ANY(%s::uuid[]) AND r.created_at >= %s AND r.created_at < %s
           GROUP BY 1""", (ids, w.lower, w.end))
    by = {o["ws"]: o for o in outcomes}
    out = {}
    for r in rows:
        o = by.get(r["ws"], {})
        out[r["ws"]] = {
            **{k: _n(r[k]) for k in ("total", "draft", "in_review", "approved", "posted", "rejected", "sla_breached")},
            "reviewHours": round(float(r["review_hours"]), 1) if r["review_hours"] is not None else None,
            "postHours": round(float(r["post_hours"]), 1) if r["post_hours"] is not None else None,
            "improved": _n(o.get("improved")), "unchanged": _n(o.get("unchanged")),
            "worsened": _n(o.get("worsened")), "pending": _n(o.get("pending")),
        }
    return out


def ideas(ids: List[str], limit: int = config.TABLE_ROWS) -> Dict:
    """Current ideas (not period-bound: an idea is a running theme)."""
    status = fetch_all(
        """SELECT tenant_id::text AS ws, status, count(*) AS n FROM product_idea
           WHERE tenant_id = ANY(%s::uuid[]) GROUP BY 1, 2""", (ids,))
    top = fetch_all(
        """SELECT i.tenant_id::text AS ws, i.title, i.topic, i.status, i.updated_at,
                  count(pic.comment_id) AS comments,
                  coalesce(sum(c.like_count), 0) AS likes
           FROM product_idea i
           LEFT JOIN product_idea_comment pic ON pic.tenant_id = i.tenant_id AND pic.idea_id = i.id
           LEFT JOIN comment c ON c.tenant_id = pic.tenant_id AND c.id = pic.comment_id
           WHERE i.tenant_id = ANY(%s::uuid[]) AND i.status <> 'DECLINED'
           GROUP BY i.id ORDER BY count(pic.comment_id) DESC, coalesce(sum(c.like_count), 0) DESC LIMIT %s""",
        (ids, limit))
    by_ws: Dict[str, Dict[str, int]] = defaultdict(dict)
    for r in status:
        by_ws[r["ws"]][r["status"]] = _n(r["n"])
    return {"byWorkspace": dict(by_ws),
            "top": [{"ws": r["ws"], "title": r["title"], "topic": r["topic"], "status": r["status"],
                     "comments": _n(r["comments"]), "likes": _n(r["likes"])} for r in top]}


def operations(ids: List[str], w: Window) -> Dict:
    ai = fetch_all(
        """SELECT tenant_id::text AS ws, mode, provider, model, embed_model, status, validated_at
           FROM ai_setting WHERE tenant_id = ANY(%s::uuid[])""", (ids,))
    jobs = fetch_all(
        """SELECT tenant_id::text AS ws, kind, trigger,
                  count(*) AS runs,
                  count(*) FILTER (WHERE status = 'COMPLETED') AS ok,
                  count(*) FILTER (WHERE status = 'FAILED') AS failed,
                  count(*) FILTER (WHERE status IN ('QUEUED', 'RUNNING')) AS active,
                  avg(EXTRACT(EPOCH FROM (finished_at - created_at))) FILTER (WHERE status = 'COMPLETED') AS secs,
                  (array_agg(left(coalesce(error, message), 160) ORDER BY created_at DESC)
                      FILTER (WHERE status = 'FAILED'))[1] AS last_error
           FROM video_analysis_job
           WHERE tenant_id = ANY(%s::uuid[]) AND created_at >= %s AND created_at < %s
           GROUP BY 1, 2, 3""", (ids, w.lower, w.end))
    listings = fetch_all(
        """SELECT tenant_id::text AS ws, status, count(*) AS n, max(checked_at) AS checked_at
           FROM product_listing WHERE tenant_id = ANY(%s::uuid[]) GROUP BY 1, 2""", (ids,))
    knowledge = fetch_all(
        """SELECT t.id::text AS ws,
                  (SELECT count(*) FROM product_knowledge k WHERE k.tenant_id = t.id) AS facts,
                  (SELECT count(*) FROM knowledge_document d WHERE d.tenant_id = t.id) AS documents,
                  (SELECT count(DISTINCT e.knowledge_id) FROM knowledge_embedding e WHERE e.tenant_id = t.id) AS embedded,
                  (SELECT max(finished_at) FROM ai_sync_run s WHERE s.tenant_id = t.id AND s.status = 'COMPLETED') AS synced_at,
                  (SELECT min(comments_checked_at) FROM video_truth_analysis v WHERE v.tenant_id = t.id) AS oldest_check,
                  (SELECT max(comments_checked_at) FROM video_truth_analysis v WHERE v.tenant_id = t.id) AS latest_check,
                  (SELECT count(*) FROM video_truth_analysis v WHERE v.tenant_id = t.id AND v.facts_stale) AS stale_videos,
                  (SELECT enabled FROM comment_watch cw WHERE cw.tenant_id = t.id) AS watch_enabled,
                  (SELECT interval_hours FROM comment_watch cw WHERE cw.tenant_id = t.id) AS watch_hours
           FROM tenant t WHERE t.id = ANY(%s::uuid[])""", (ids,))
    out_jobs: Dict[str, List[Dict]] = defaultdict(list)
    for r in jobs:
        out_jobs[r["ws"]].append({"kind": r["kind"], "trigger": r["trigger"], "runs": _n(r["runs"]), "ok": _n(r["ok"]),
                                  "failed": _n(r["failed"]), "active": _n(r["active"]),
                                  "avgSeconds": round(float(r["secs"])) if r["secs"] is not None else None,
                                  "lastError": r["last_error"]})
    out_listings: Dict[str, Dict[str, int]] = defaultdict(dict)
    for r in listings:
        out_listings[r["ws"]][r["status"]] = _n(r["n"])
    return {
        "ai": {r["ws"]: {"mode": r["mode"], "provider": r["provider"], "model": r["model"],
                         "embedModel": r["embed_model"], "status": r["status"]} for r in ai},
        "jobs": dict(out_jobs),
        "listings": dict(out_listings),
        "knowledge": {r["ws"]: {"facts": _n(r["facts"]), "documents": _n(r["documents"]), "embedded": _n(r["embedded"]),
                                "syncedAt": r["synced_at"], "oldestCheck": r["oldest_check"],
                                "latestCheck": r["latest_check"], "staleVideos": _n(r["stale_videos"]),
                                "watchEnabled": r["watch_enabled"], "watchHours": r["watch_hours"]}
                      for r in knowledge},
    }


def team(ids: List[str], w: Window) -> Dict:
    members = fetch_all(
        """SELECT tenant_id::text AS ws, coalesce(roles[1], 'analyst') AS role, count(*) AS n,
                  max(last_seen_at) AS last_seen
           FROM tenant_user WHERE tenant_id = ANY(%s::uuid[]) AND active GROUP BY 1, 2""", (ids,))
    subs = fetch_all(
        """SELECT t.id::text AS ws, t.plan_code, s.status, s.billing_interval, s.current_period_end, s.trial_ends_at
           FROM tenant t LEFT JOIN subscription s ON s.tenant_id = t.id
           WHERE t.id = ANY(%s::uuid[])""", (ids,))
    usage = fetch_all(
        """SELECT tenant_id::text AS ws, metric_type, sum(quantity) AS n FROM usage_event
           WHERE tenant_id = ANY(%s::uuid[]) AND recorded_at >= %s AND recorded_at < %s GROUP BY 1, 2""",
        (ids, w.lower, w.end))
    by_role: Dict[str, Dict[str, int]] = defaultdict(dict)
    last_seen: Dict[str, Optional[datetime]] = {}
    for r in members:
        by_role[r["ws"]][r["role"]] = _n(r["n"])
        if r["last_seen"] and (r["ws"] not in last_seen or (last_seen[r["ws"]] or r["last_seen"]) <= r["last_seen"]):
            last_seen[r["ws"]] = r["last_seen"]
    use: Dict[str, Dict[str, int]] = defaultdict(dict)
    for r in usage:
        use[r["ws"]][r["metric_type"]] = _n(r["n"])
    return {"roles": dict(by_role), "lastSeen": last_seen,
            "plans": {r["ws"]: {"plan": r["plan_code"], "status": r["status"], "interval": r["billing_interval"],
                                "renews": r["current_period_end"], "trialEnds": r["trial_ends_at"]} for r in subs},
            "usage": dict(use)}
