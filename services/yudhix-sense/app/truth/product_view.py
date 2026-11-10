"""One product across channels: YouTube comments and Amazon reviews, side by side.

Every comment and review carries its product, so a product's page can split sentiment by channel
(YouTube vs Amazon), show what each channel talks about, and list the positive and negative voices
from either channel with their source (the video or the Amazon listing).
"""
from collections import Counter, defaultdict
from typing import Dict, List, Optional

from app.core.database import fetch_all, fetch_one
from app.truth.audience import TOPICS
from app.truth.listings import list_listings
from app.truth.product_impact import reach

CHANNELS = {"YOUTUBE": "YouTube", "AMAZON": "Amazon"}
SENTIMENTS = ("POSITIVE", "NEUTRAL", "NEGATIVE")


def _rows(tenant_id: str, product_id: Optional[str] = None) -> List[Dict]:
    where, params = ["c.tenant_id = %s", "c.status = 'ACTIVE'", "c.platform IN ('YOUTUBE', 'AMAZON')"], [tenant_id]
    if product_id:
        where.append("c.product_id = %s")
        params.append(product_id)
    return fetch_all(
        f"""SELECT c.product_id, c.platform, c.like_count, c.reply_count, ca.sentiment,
                   COALESCE((SELECT array_agg(a.aspect) FROM comment_aspect a
                             WHERE a.tenant_id = c.tenant_id AND a.comment_id = c.id), '{{}}') AS topics
            FROM comment c JOIN comment_analysis ca ON ca.tenant_id = c.tenant_id AND ca.comment_id = c.id
            WHERE {' AND '.join(where)}""", tuple(params))


def split(rows: List[Dict]) -> Dict[str, Dict]:
    """Per channel: comment and reach counts by sentiment, plus top topics with their sentiment."""
    out: Dict[str, Dict] = {}
    for ch in CHANNELS:
        out[ch] = {"channel": ch, "label": CHANNELS[ch], "comments": 0, "reach": 0,
                   "byComments": Counter(), "byReach": Counter(), "topics": defaultdict(Counter)}
    for r in rows:
        ch = out.get(r["platform"])
        if not ch:
            continue
        s = (r.get("sentiment") or "NEUTRAL").upper()
        s = s if s in SENTIMENTS else "NEUTRAL"
        w = reach(r.get("like_count"), r.get("reply_count"))
        ch["comments"] += 1
        ch["reach"] += w
        ch["byComments"][s] += 1
        ch["byReach"][s] += w
        for t in r.get("topics") or []:
            if t in TOPICS:
                ch["topics"][t][s] += 1
    result = {}
    for key, ch in out.items():
        n = ch["comments"] or 1
        topics = sorted(({"topic": t, "label": TOPICS[t], "positive": c["POSITIVE"], "neutral": c["NEUTRAL"],
                          "negative": c["NEGATIVE"], "comments": sum(c.values())} for t, c in ch["topics"].items()),
                        key=lambda x: -x["comments"])[:6]
        result[key] = {
            "channel": key, "label": ch["label"], "comments": ch["comments"], "reach": ch["reach"],
            "sentiment": {s.lower(): ch["byComments"][s] for s in SENTIMENTS},
            "sentimentByReach": {s.lower(): ch["byReach"][s] for s in SENTIMENTS},
            "positiveShare": round(ch["byComments"]["POSITIVE"] / n, 3) if ch["comments"] else 0.0,
            "negativeShare": round(ch["byComments"]["NEGATIVE"] / n, 3) if ch["comments"] else 0.0,
            "topics": topics,
        }
    return result


def list_products(tenant_id: str) -> List[Dict]:
    products = fetch_all("SELECT * FROM product WHERE tenant_id = %s AND active ORDER BY name", (tenant_id,))
    by_product: Dict[str, List[Dict]] = defaultdict(list)
    for r in _rows(tenant_id):
        by_product[str(r["product_id"])].append(r)
    listings = defaultdict(list)
    for l in list_listings(tenant_id):
        listings[l["productId"]].append(l)
    videos = {str(r["product_id"]): int(r["n"]) for r in fetch_all(
        """SELECT c.product_id, count(DISTINCT c.custom_attributes->>'video_id') AS n FROM comment c
           WHERE c.tenant_id = %s AND c.platform = 'YOUTUBE' AND c.status = 'ACTIVE' GROUP BY 1""", (tenant_id,))}
    out = []
    for p in products:
        pid = str(p["id"])
        ratings = [l["rating"] for l in listings[pid] if l["rating"] is not None]
        out.append({"id": pid, "name": p["name"], "category": p.get("category"),
                    "channels": split(by_product[pid]), "videos": videos.get(pid, 0),
                    "listings": len(listings[pid]),
                    "amazonRating": round(sum(ratings) / len(ratings), 2) if ratings else None})
    return out


def overview(tenant_id: str, product_id: str) -> Optional[Dict]:
    p = fetch_one("SELECT * FROM product WHERE tenant_id = %s AND id = %s", (tenant_id, product_id))
    if not p:
        return None
    channels = split(_rows(tenant_id, product_id))
    videos = [{"videoId": r["video_id"], "title": r["video_title"], "channel": r["channel_title"],
               "comments": int(r["n"]), "thumbnailUrl": r.get("thumbnail_url") or f"https://i.ytimg.com/vi/{r['video_id']}/hqdefault.jpg"}
              for r in fetch_all(
        """SELECT c.custom_attributes->>'video_id' AS video_id, max(v.video_title) AS video_title,
                  max(v.channel_title) AS channel_title, max(v.thumbnail_url) AS thumbnail_url, count(*) AS n
           FROM comment c LEFT JOIN video_truth_analysis v ON v.tenant_id = c.tenant_id
                AND v.video_id = c.custom_attributes->>'video_id'
           WHERE c.tenant_id = %s AND c.product_id = %s AND c.platform = 'YOUTUBE' AND c.status = 'ACTIVE'
             AND c.custom_attributes ? 'video_id'
           GROUP BY 1 ORDER BY count(*) DESC""", (tenant_id, product_id))]
    total = sum(c["comments"] for c in channels.values())
    pos = sum(c["sentiment"]["positive"] for c in channels.values())
    neg = sum(c["sentiment"]["negative"] for c in channels.values())
    return {"id": str(p["id"]), "name": p["name"], "category": p.get("category"),
            "totals": {"comments": total, "positive": pos, "negative": neg,
                       "neutral": total - pos - neg},
            "channels": channels, "videos": videos, "listings": list_listings(tenant_id, product_id),
            "headline": _headline(channels)}


def _headline(channels: Dict[str, Dict]) -> str:
    yt, az = channels["YOUTUBE"], channels["AMAZON"]
    if not yt["comments"] and not az["comments"]:
        return "No comments or reviews yet. Analyze a video or add an Amazon listing."
    parts = []
    for ch in (yt, az):
        if ch["comments"]:
            parts.append(f"{ch['label']}: {round(ch['positiveShare'] * 100)}% positive, "
                         f"{round(ch['negativeShare'] * 100)}% negative ({ch['comments']:,})")
    text = " · ".join(parts) + "."
    if yt["comments"] and az["comments"]:
        gap = az["negativeShare"] - yt["negativeShare"]
        if abs(gap) >= 0.1:
            louder = "Buyers on Amazon" if gap > 0 else "Viewers on YouTube"
            text += f" {louder} are {round(abs(gap) * 100)} points more negative."
    return text


def comments(tenant_id: str, product_id: str, channel: Optional[str] = None, sentiment: Optional[str] = None,
             limit: int = 30, offset: int = 0) -> Dict:
    where = ["c.tenant_id = %s", "c.product_id = %s", "c.status = 'ACTIVE'", "c.platform IN ('YOUTUBE', 'AMAZON')"]
    params: list = [tenant_id, product_id]
    if channel in CHANNELS:
        where.append("c.platform = %s")
        params.append(channel)
    if sentiment in SENTIMENTS:
        where.append("ca.sentiment = %s")
        params.append(sentiment)
    base = f"""FROM comment c JOIN comment_analysis ca ON ca.tenant_id = c.tenant_id AND ca.comment_id = c.id
               WHERE {' AND '.join(where)}"""
    total = fetch_one(f"SELECT count(*) AS n {base}", tuple(params))["n"]
    rows = fetch_all(
        f"""SELECT c.id, c.platform, c.masked_text, c.like_count, c.reply_count, c.platform_created_at,
                   c.custom_attributes AS attrs, ca.sentiment, ca.priority,
                   COALESCE((SELECT array_agg(a.aspect) FROM comment_aspect a
                             WHERE a.tenant_id = c.tenant_id AND a.comment_id = c.id), '{{}}') AS topics
            {base} ORDER BY (1 + c.like_count + 2 * c.reply_count) DESC, c.platform_created_at DESC
            LIMIT %s OFFSET %s""", tuple(params + [limit, offset]))
    items = []
    for r in rows:
        a = r["attrs"] or {}
        amazon = r["platform"] == "AMAZON"
        items.append({
            "id": str(r["id"]), "channel": r["platform"], "text": r["masked_text"], "likes": r["like_count"],
            "replies": r["reply_count"], "sentiment": r["sentiment"], "priority": r["priority"],
            "createdAt": r["platform_created_at"].isoformat() if r.get("platform_created_at") else None,
            "rating": a.get("rating") if amazon else None, "verified": bool(a.get("verified")) if amazon else None,
            "source": a.get("listing_title") if amazon else a.get("video_title"),
            "sourceId": a.get("listing_id") if amazon else a.get("video_id"),
            "url": a.get("url") if amazon else None, "isNew": bool(a.get("new_at")),
            "topics": [TOPICS[t] for t in (r.get("topics") or []) if t in TOPICS],
        })
    return {"items": items, "total": int(total), "limit": limit, "offset": offset}
