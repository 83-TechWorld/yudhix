"""Amazon listings: link a product to its Amazon page and collect the reviews, by hand or on a schedule.

A check runs as a job ("AMAZON") with the same progress UI as a video analysis:
  1. read the listing (title, stars, rating count) and its reviews  (app/truth/amazon.py)
  2. store new reviews as comments with platform AMAZON, PII masked, author pseudonymized
  3. read them with AI (topics, intent, feature requests) like YouTube comments
  4. sentiment follows the stars (4-5 positive, 3 neutral, 1-2 negative); impact and priority from it
Reviews already stored keep their reading; their helpful-vote counts are refreshed.
"""
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from app.core import config, llm
from app.core.database import append_audit, cursor, fetch_all, fetch_one
from app.db import DEFAULT_SOURCE_ID, persist_comment_and_analysis
from app.pipeline.masker import PiiMasker
from app.platform import billing
from app.platform.notifications import notify
from app.truth import amazon, audience
from app.truth.scoring import impact_score, priority_band

logger = logging.getLogger(__name__)
_masker = PiiMasker()


class ListingError(Exception):
    pass


def _listing(r: Dict) -> Dict:
    iso = lambda v: v.isoformat() if hasattr(v, "isoformat") else v  # noqa: E731
    return {"id": str(r["id"]), "productId": str(r["product_id"]), "channel": r["channel"],
            "marketplace": r["marketplace"], "asin": r["external_id"], "url": r["url"], "title": r.get("title"),
            "imageUrl": r.get("image_url"), "rating": float(r["rating"]) if r.get("rating") is not None else None,
            "ratingsCount": r.get("ratings_count"), "reviewsStored": r.get("reviews_stored") or 0,
            "status": r["status"], "lastError": r.get("last_error"), "checkedAt": iso(r.get("checked_at")),
            "createdAt": iso(r.get("created_at"))}


def list_listings(tenant_id: str, product_id: Optional[str] = None) -> List[Dict]:
    where, params = "tenant_id = %s", [tenant_id]
    if product_id:
        where += " AND product_id = %s"
        params.append(product_id)
    return [_listing(r) for r in fetch_all(f"SELECT * FROM product_listing WHERE {where} ORDER BY created_at",
                                           tuple(params))]


def get_listing(tenant_id: str, listing_id: str) -> Optional[Dict]:
    r = fetch_one("SELECT * FROM product_listing WHERE tenant_id = %s AND id = %s", (tenant_id, listing_id))
    return _listing(r) if r else None


def add_listing(tenant_id: str, actor: str, url: str, product_id: str) -> Dict:
    """Register (or re-use) the listing for this URL under a product of this workspace."""
    if not product_id or not fetch_one("SELECT 1 FROM product WHERE tenant_id = %s AND id = %s", (tenant_id, product_id)):
        raise ListingError("Pick the product these reviews belong to.")
    try:
        market, asin, canonical = amazon.parse_url(url)
    except amazon.AmazonError as e:
        raise ListingError(str(e)) from e
    with cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO product_listing (tenant_id, product_id, channel, marketplace, external_id, url, created_by)
               VALUES (%s, %s, 'AMAZON', %s, %s, %s, %s)
               ON CONFLICT (tenant_id, channel, marketplace, external_id)
               DO UPDATE SET product_id = EXCLUDED.product_id RETURNING *""",
            (tenant_id, product_id, market, asin, canonical, actor))
        row = dict(cur.fetchone())
    return _listing(row)


def delete_listing(tenant_id: str, actor: str, listing_id: str) -> bool:
    """Stop tracking a listing. Its reviews are archived (hidden), not deleted."""
    with cursor(commit=True) as cur:
        cur.execute("DELETE FROM product_listing WHERE tenant_id = %s AND id = %s RETURNING external_id",
                    (tenant_id, listing_id))
        row = cur.fetchone()
        if row:
            cur.execute("""UPDATE comment SET status = 'ARCHIVED' WHERE tenant_id = %s AND platform = 'AMAZON'
                           AND custom_attributes->>'listing_id' = %s""", (tenant_id, listing_id))
            append_audit(cur, tenant_id, actor, "USER", "LISTING_REMOVED", "PRODUCT", listing_id, {"asin": row["external_id"]})
    return bool(row)


def start_check(tenant_id: str, listing: Dict, actor: str, trigger: str = "USER") -> Dict:
    from app.truth import pipeline
    running = pipeline.active_job(tenant_id, listing["asin"])
    if running:
        return running
    return pipeline.create_job(tenant_id, listing["url"], listing["productId"], actor, kind="AMAZON",
                               trigger=trigger, video_id=listing["asin"])


# ----------------------------------------------------------------------------- the check

def run_check(job_id: str, tenant_id: str, job: Dict, creator: Optional[str], update) -> None:
    """Job body for kind AMAZON. `update(stage, pct, message, status=, error=, result=)` writes job progress."""
    listing_row = fetch_one("""SELECT * FROM product_listing WHERE tenant_id = %s AND channel = 'AMAZON'
                               AND external_id = %s""", (tenant_id, job["videoId"]))
    scheduled = job["trigger"] == "SCHEDULE"
    if not listing_row:
        update("FAILED", 100, "This Amazon listing is no longer tracked.", status="FAILED", error="listing removed")
        return
    listing_id = str(listing_row["id"])
    try:
        update("FETCHING_VIDEO", 10, f"Reading the Amazon listing on {listing_row['marketplace']}")
        data = amazon.fetch(listing_row["url"], config.AMAZON_MAX_REVIEWS)
        update("INGESTING_COMMENTS", 40, f"Storing {len(data.reviews)} reviews")
        new_ids = _store(tenant_id, listing_row, data)
        fresh = _comments(tenant_id, new_ids)
        if fresh:
            update("UNDERSTANDING", 60, f"Reading {len(fresh)} new reviews" + (" with AI" if llm.is_available() else ""))
            audience.understand(tenant_id, [], fresh, lambda d, t: update(
                "UNDERSTANDING", 60 + int(30 * d / max(1, t)), f"Reading reviews with AI ({d}/{t} batches)"))
        update("ATTRIBUTING", 92, "Scoring reviews by stars and helpful votes")
        stats = _score(tenant_id, listing_id)
        result = {"newComments": len(new_ids), "negative": stats["newNegative"], "ideas": stats["newIdeas"],
                  "videoTitle": data.title or listing_row["external_id"], "reviewsSeen": len(data.reviews),
                  "source": data.source}
        _finish(listing_id, data, "OK", None)
        message = (f"{len(new_ids)} new review{'s' if len(new_ids) != 1 else ''}" if new_ids
                   else f"No new reviews ({len(data.reviews)} checked)")
        update("COMPLETED", 100, message, status="COMPLETED", result=result)
        if new_ids:
            billing.record(tenant_id, "COMMENT_INGESTED", len(new_ids), key=f"job:{job_id}")
            body = f"{len(new_ids)} new on {data.title or 'Amazon'}" + (f": {stats['newNegative']} negative." if stats["newNegative"] else ".")
            link = f"/products/{listing_row['product_id']}?channel=AMAZON"
            if scheduled:
                notify(tenant_id, "comments", "New Amazon reviews", body, link, roles=["admin", "approver", "agent"])
            else:
                notify(tenant_id, "comments", "Amazon reviews collected", body, link, user_ids=[creator])
    except amazon.AmazonBlocked as e:
        _finish(listing_id, None, "BLOCKED", str(e))
        update("FAILED", 100, str(e), status="FAILED", error=str(e))
    except amazon.AmazonError as e:
        _finish(listing_id, None, "FAILED", str(e))
        update("FAILED", 100, str(e), status="FAILED", error=str(e))
    except Exception as e:
        logger.exception("Amazon check %s failed", job_id)
        _finish(listing_id, None, "FAILED", "Something went wrong while reading the reviews.")
        update("FAILED", 100, "Something went wrong while reading the reviews.", status="FAILED",
               error=f"{type(e).__name__}: {e}")


def _store(tenant_id: str, listing_row: Dict, data: amazon.Listing) -> List[str]:
    """Store every review; returns the platform ids of the ones that are new."""
    from app.truth.pipeline import author_hash
    known = {r["platform_comment_id"] for r in fetch_all(
        "SELECT platform_comment_id FROM comment WHERE tenant_id = %s AND platform = 'AMAZON' AND platform_comment_id = ANY(%s)",
        (tenant_id, [r.review_id for r in data.reviews]))}
    new_ids, stamp = [], amazon.now_iso()
    for r in data.reviews:
        text = f"{r.title}. {r.body}" if r.title and not r.body.startswith(r.title) else r.body
        masked, _ = _masker.mask(text)
        sentiment = amazon.sentiment_for(r.rating) or "NEUTRAL"
        attrs = {"channel": "AMAZON", "listing_id": str(listing_row["id"]), "asin": listing_row["external_id"],
                 "marketplace": listing_row["marketplace"], "rating": r.rating, "verified": r.verified,
                 "review_title": r.title[:300], "listing_title": (data.title or "")[:300], "country": r.country,
                 "url": f"https://www.{listing_row['marketplace']}/gp/customer-reviews/{r.review_id}"}
        is_new = r.review_id not in known
        if is_new:
            attrs["new_at"] = stamp
            new_ids.append(r.review_id)
        else:  # keep the AI reading and "new" mark of reviews stored earlier
            prev = fetch_one("""SELECT custom_attributes FROM comment WHERE tenant_id = %s AND platform = 'AMAZON'
                                AND platform_comment_id = %s""", (tenant_id, r.review_id))
            for k in ("ai", "new_at"):
                if prev and (prev["custom_attributes"] or {}).get(k) is not None:
                    attrs[k] = prev["custom_attributes"][k]
        persist_comment_and_analysis({
            "tenant_id": tenant_id, "platform": "AMAZON", "comment_id": r.review_id, "raw_text": text,
            "masked_text": masked, "author_hash": author_hash(tenant_id, "AMAZON", r.author or r.review_id),
            "likes": r.helpful_votes, "replies": 0, "sentiment": sentiment,
            "sentiment_score": {"POSITIVE": 0.8, "NEGATIVE": -0.8}.get(sentiment, 0.0),
            "intent": "COMPLAINT" if sentiment == "NEGATIVE" else "PRAISE" if sentiment == "POSITIVE" else "OTHER",
            "churn_risk": 0.6 if sentiment == "NEGATIVE" else 0.1,
            "platform_created_at": r.date or "now()", "source_id": DEFAULT_SOURCE_ID,
            "product_id": str(listing_row["product_id"]), "custom_attributes": attrs,
        } if is_new else {
            # existing review: refresh counts/text only, keep its analysis
            "tenant_id": tenant_id, "platform": "AMAZON", "comment_id": r.review_id, "raw_text": text,
            "masked_text": masked, "author_hash": author_hash(tenant_id, "AMAZON", r.author or r.review_id),
            "likes": r.helpful_votes, "replies": 0, "platform_created_at": r.date or "now()",
            "source_id": DEFAULT_SOURCE_ID, "product_id": str(listing_row["product_id"]), "custom_attributes": attrs,
            **_current_analysis(tenant_id, r.review_id),
        })
    return new_ids


def _current_analysis(tenant_id: str, platform_id: str) -> Dict:
    r = fetch_one("""SELECT ca.sentiment, ca.sentiment_score, ca.intent, ca.churn_risk, ca.impact_score, ca.priority
                     FROM comment c JOIN comment_analysis ca ON ca.tenant_id = c.tenant_id AND ca.comment_id = c.id
                     WHERE c.tenant_id = %s AND c.platform = 'AMAZON' AND c.platform_comment_id = %s""",
                  (tenant_id, platform_id)) or {}
    return {k: v for k, v in {"sentiment": r.get("sentiment"), "sentiment_score": r.get("sentiment_score"),
                              "intent": r.get("intent"), "churn_risk": r.get("churn_risk"),
                              "impact_score": r.get("impact_score"), "priority": r.get("priority")}.items() if v is not None}


def _comments(tenant_id: str, platform_ids: List[str]) -> List[Dict]:
    if not platform_ids:
        return []
    return fetch_all(
        """SELECT c.id, c.masked_text, c.like_count, c.reply_count, c.platform_created_at FROM comment c
           WHERE c.tenant_id = %s AND c.platform = 'AMAZON' AND c.platform_comment_id = ANY(%s)""",
        (tenant_id, platform_ids))


def _score(tenant_id: str, listing_id: str) -> Dict:
    """Stars decide sentiment (the AI keeps topics and intent); impact and priority follow."""
    rows = fetch_all(
        """SELECT c.id, c.like_count, c.reply_count, c.platform_created_at, c.custom_attributes, ca.intent, ca.churn_risk
           FROM comment c JOIN comment_analysis ca ON ca.tenant_id = c.tenant_id AND ca.comment_id = c.id
           WHERE c.tenant_id = %s AND c.platform = 'AMAZON' AND c.custom_attributes->>'listing_id' = %s
             AND c.status = 'ACTIVE'""", (tenant_id, listing_id))
    new_negative = new_ideas = 0
    with cursor(commit=True) as cur:
        for r in rows:
            attrs = r["custom_attributes"] or {}
            sentiment = amazon.sentiment_for(attrs.get("rating")) or "NEUTRAL"
            created = r["platform_created_at"] if isinstance(r["platform_created_at"], datetime) else None
            churn = float(r["churn_risk"]) if r.get("churn_risk") is not None else (0.6 if sentiment == "NEGATIVE" else 0.1)
            score = impact_score(sentiment, churn, r["like_count"], r["reply_count"], created)
            cur.execute("""UPDATE comment_analysis SET sentiment = %s, impact_score = %s, priority = %s
                           WHERE tenant_id = %s AND comment_id = %s""",
                        (sentiment, score, priority_band(score), tenant_id, r["id"]))
            cur.execute("UPDATE comment_aspect SET sentiment = %s WHERE tenant_id = %s AND comment_id = %s",
                        (sentiment, tenant_id, r["id"]))
            if attrs.get("new_at"):
                new_negative += sentiment == "NEGATIVE"
                new_ideas += (r.get("intent") or "") == "IDEA"
        cur.execute("""UPDATE product_listing SET reviews_stored = (SELECT count(*) FROM comment c WHERE c.tenant_id = %s
                           AND c.platform = 'AMAZON' AND c.custom_attributes->>'listing_id' = %s) WHERE id = %s""",
                    (tenant_id, listing_id, listing_id))
    return {"newNegative": new_negative, "newIdeas": new_ideas}


def _finish(listing_id: str, data: Optional[amazon.Listing], status: str, error: Optional[str]) -> None:
    with cursor(commit=True) as cur:
        if data:
            cur.execute("""UPDATE product_listing SET title = COALESCE(%s, title), image_url = COALESCE(%s, image_url),
                                  rating = COALESCE(%s, rating), ratings_count = COALESCE(%s, ratings_count),
                                  status = %s, last_error = %s, checked_at = now() WHERE id = %s""",
                        (data.title, data.image_url, data.rating, data.ratings_count, status, error, listing_id))
        else:
            cur.execute("UPDATE product_listing SET status = %s, last_error = %s, checked_at = now() WHERE id = %s",
                        (status, error, listing_id))


def due_listings(limit: int = 20) -> List[Dict]:
    """Listings whose last check is older than their workspace's schedule interval."""
    return [{"tenant_id": str(r["tenant_id"]), "id": str(r["id"])} for r in fetch_all(
        """SELECT l.tenant_id, l.id FROM product_listing l
           JOIN tenant t ON t.id = l.tenant_id AND t.status = 'ACTIVE'
           LEFT JOIN comment_watch w ON w.tenant_id = l.tenant_id
           WHERE COALESCE(w.enabled, true)
             AND COALESCE(l.checked_at, l.created_at - interval '100 years')
                 < now() - make_interval(hours => COALESCE(w.interval_hours, %s))
           ORDER BY l.checked_at NULLS FIRST LIMIT %s""", (config.SCHEDULER_DEFAULT_HOURS, limit))]
