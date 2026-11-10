"""Product growth: the positive side of a video's comments, and the product ideas they contain.

Per video (the "Product growth" tab):
  growth score (0-100) = 100 x (positive share of reach)^0.75 x size   (mirror of the impact score)
  what people want      comments by intent: ideas, praise, buying, questions, complaints, leaving
  what people love      topics ranked by positive reach
  ideas                 feature requests grouped into themes, with their status
  buying signals, praise and leaving: the most-liked comments of each

Across videos (the Ideas page): every feature request is grouped into a product idea by theme.
Similar requests ("more storage", "add more storage space") land in the same idea, so the product
team works one backlog: New -> Reviewing -> Planned -> Shipped (or Declined).
"""
import math
import re
from collections import Counter, defaultdict
from typing import Dict, Iterable, List, Optional, Tuple

from app.core.database import append_audit, cursor, fetch_all, fetch_one
from app.truth.audience import INTENTS, TOPICS
from app.truth.product_impact import reach

IDEA_STATUSES = ("NEW", "REVIEWING", "PLANNED", "SHIPPED", "DECLINED")
SIMILAR = 0.5  # word overlap (Jaccard) at which two requests count as the same idea

_STOP = {"a", "an", "the", "to", "for", "of", "on", "in", "with", "and", "or", "it", "its", "they", "we", "us", "be",
         "would", "should", "could", "please", "more", "some", "any", "add", "added", "adding", "have", "has", "get",
         "make", "making", "bring", "back", "give", "let", "option", "options", "ability", "support", "feature",
         "new", "better", "is", "are", "that", "this", "so", "just", "like", "also", "really", "very", "can", "my",
         "your", "their", "our", "you", "i", "me", "ps5", "ps", "playstation", "sony"}


# ----------------------------------------------------------------------------- grouping

def theme_words(title: str) -> List[str]:
    words = re.findall(r"[a-z0-9+#]+", (title or "").lower())
    out = []
    for w in words:
        if w in _STOP:
            continue
        if len(w) > 4 and w.endswith("s") and not w.endswith("ss"):
            w = w[:-1]  # games -> game
        out.append(w)
    return sorted(set(out))


def theme_key(title: str) -> str:
    return " ".join(theme_words(title))[:120]


def similarity(a: Iterable[str], b: Iterable[str]) -> float:
    a, b = set(a), set(b)
    return len(a & b) / len(a | b) if a and b else 0.0


def match_idea(words: List[str], ideas: List[Dict]) -> Optional[Dict]:
    """The existing idea with the same theme, or the most similar one above the threshold."""
    key = " ".join(words)
    best, best_score = None, 0.0
    for idea in ideas:
        if idea["theme_key"] == key:
            return idea
        score = similarity(words, idea["theme_key"].split())
        if score > best_score:
            best, best_score = idea, score
    return best if best_score >= SIMILAR else None


def link_ideas(cur, tenant_id: str, comment_ids: List[str], requests: List[Tuple[str, str, str]]) -> int:
    """Re-link comments to ideas. requests: (comment id, requested thing, topic) for each IDEA comment.
    Requests without a usable phrase stay as IDEA comments without an idea. Returns links made."""
    if comment_ids:
        cur.execute("DELETE FROM product_idea_comment WHERE tenant_id = %s AND comment_id = ANY(%s::uuid[])",
                    (tenant_id, comment_ids))
    cur.execute("SELECT id, theme_key FROM product_idea WHERE tenant_id = %s", (tenant_id,))
    ideas = [dict(r) for r in cur.fetchall()]
    linked = 0
    for comment_id, phrase, topic in requests:
        words = theme_words(phrase)
        if not words:
            continue
        idea = match_idea(words, ideas)
        if not idea:
            cur.execute(
                """INSERT INTO product_idea (tenant_id, theme_key, title, topic) VALUES (%s, %s, %s, %s)
                   ON CONFLICT (tenant_id, theme_key) DO UPDATE SET updated_at = product_idea.updated_at
                   RETURNING id, theme_key""",
                (tenant_id, " ".join(words)[:120], _title(phrase), topic if topic in TOPICS else "FEATURES"))
            idea = dict(cur.fetchone())
            ideas.append(idea)
        cur.execute("""INSERT INTO product_idea_comment (tenant_id, idea_id, comment_id) VALUES (%s, %s, %s)
                       ON CONFLICT DO NOTHING""", (tenant_id, idea["id"], comment_id))
        linked += 1
    # Ideas nobody touched and no comment supports any more (e.g. after re-reading) are dropped.
    cur.execute("""DELETE FROM product_idea p WHERE p.tenant_id = %s AND p.status = 'NEW' AND p.note IS NULL
                     AND NOT EXISTS (SELECT 1 FROM product_idea_comment pc WHERE pc.idea_id = p.id)""", (tenant_id,))
    return linked


def _title(phrase: str) -> str:
    phrase = " ".join(phrase.split())[:200]
    return phrase[:1].upper() + phrase[1:]


# ----------------------------------------------------------------------------- per-video growth view

def growth_level(score: int) -> str:
    return "STRONG" if score >= 60 else "MODERATE" if score >= 35 else "LOW"


def compute(rows: List[Dict]) -> Dict:
    """rows: one per active comment with like_count, reply_count, sentiment, intent, model_version, topics,
    idea_id / idea_title / idea_status, masked_text, id."""
    by_reach, by_count = Counter(), Counter()
    intents: Dict[str, Counter] = defaultdict(Counter)
    loved: Dict[str, Counter] = defaultdict(Counter)
    ideas: Dict[str, Dict] = {}
    unthemed: List[Dict] = []
    buckets: Dict[str, List[Dict]] = defaultdict(list)
    ai_count = 0

    for r in rows:
        s = (r.get("sentiment") or "NEUTRAL").upper()
        w = reach(r.get("like_count"), r.get("reply_count"))
        intent = _intent(r.get("intent"), s)
        by_reach[s] += w
        by_count[s] += 1
        intents[intent]["comments"] += 1
        intents[intent]["reach"] += w
        if (r.get("model_version") or "").startswith("llm/"):
            ai_count += 1
        if s == "POSITIVE":
            for t in r.get("topics") or []:
                if t in TOPICS:
                    loved[t]["comments"] += 1
                    loved[t]["reach"] += w
        item = _comment(r, w)
        if intent == "IDEA":
            if r.get("idea_id"):
                g = ideas.setdefault(str(r["idea_id"]), {
                    "id": str(r["idea_id"]), "title": r.get("idea_title"), "status": r.get("idea_status") or "NEW",
                    "comments": 0, "reach": 0, "examples": []})
                g["comments"] += 1
                g["reach"] += w
                g["examples"].append(item)
            else:
                unthemed.append(item)
        if intent in ("BUY", "LEAVE") or s == "POSITIVE":
            buckets["PRAISE" if intent not in ("BUY", "LEAVE") else intent].append(item)

    total = sum(by_reach.values())
    pos_share = by_reach["POSITIVE"] / total if total else 0.0
    size = 0.6 + 0.4 * min(1.0, math.log10(total + 1) / 4) if total else 0.0
    score = round(100 * pos_share ** 0.75 * size) if total else 0

    idea_list = sorted(ideas.values(), key=lambda g: (-g["reach"], -g["comments"]))
    for g in idea_list:
        g["examples"] = sorted(g["examples"], key=lambda c: -c["reach"])[:3]
    loved_list = sorted(({"topic": t, "label": TOPICS[t], "comments": c["comments"], "reach": c["reach"]}
                         for t, c in loved.items()), key=lambda x: (-x["reach"], -x["comments"]))
    top = {k: sorted(v, key=lambda c: -c["reach"])[:5] for k, v in buckets.items()}

    return {
        "score": score,
        "level": growth_level(score),
        "headline": _headline(pos_share, loved_list, idea_list, intents),
        "totals": {"comments": sum(by_count.values()), "reach": total},
        "positiveShareOfReach": round(pos_share, 3),
        "intents": [{"intent": k, "label": INTENTS[k], "comments": intents[k]["comments"],
                     "reach": intents[k]["reach"]} for k in INTENTS],
        "loved": loved_list,
        "ideas": idea_list,
        "ideaComments": intents["IDEA"]["comments"],
        "unthemedIdeas": sorted(unthemed, key=lambda c: -c["reach"])[:5],
        "topPraise": top.get("PRAISE", []),
        "buyingSignals": top.get("BUY", []),
        "leaving": top.get("LEAVE", []),
        "coverage": {"aiComments": ai_count},
    }


SPECIFIC_INTENTS = ("IDEA", "BUY", "LEAVE", "QUESTION")


def _intent(stored: Optional[str], sentiment: str) -> str:
    """Specific intents are kept. Praise / complaint / other just restate sentiment, which re-linking may
    have changed since, so they follow the current sentiment (also covers older rows tagged GENERAL)."""
    stored = (stored or "").upper()
    if stored in SPECIFIC_INTENTS:
        return stored
    return {"POSITIVE": "PRAISE", "NEGATIVE": "COMPLAINT"}.get(sentiment, "OTHER")


def _comment(r: Dict, w: int) -> Dict:
    return {"id": str(r["id"]), "text": r.get("masked_text") or "", "likes": r.get("like_count") or 0,
            "replies": r.get("reply_count") or 0, "reach": w, "sentiment": r.get("sentiment")}


def _headline(pos_share: float, loved: List[Dict], ideas: List[Dict], intents: Dict[str, Counter]) -> str:
    total = sum(c["comments"] for c in intents.values())
    if not total:
        return "No comments yet."
    parts = [f"{round(pos_share * 100)}% of the reach is positive."]
    if loved:
        parts.append(f"People like {loved[0]['label'].lower()} most.")
    n_ideas = intents["IDEA"]["comments"]
    if n_ideas:
        s = "s" if n_ideas != 1 else ""
        parts.append(f"{n_ideas} comment{s} ask{'' if s else 's'} for a change" +
                     (f"; the top idea is “{ideas[0]['title']}”." if ideas else "."))
    if intents["BUY"]["comments"]:
        parts.append(f"{intents['BUY']['comments']} show buying intent.")
    return " ".join(parts)


def load(tenant_id: str, video_id: str) -> Dict:
    rows = fetch_all(
        """SELECT c.id, c.masked_text, c.like_count, c.reply_count, ca.sentiment, ca.intent, ca.model_version,
                  pi.id AS idea_id, pi.title AS idea_title, pi.status AS idea_status,
                  COALESCE((SELECT array_agg(a.aspect ORDER BY a.id) FROM comment_aspect a
                            WHERE a.tenant_id = c.tenant_id AND a.comment_id = c.id), '{}') AS topics
           FROM comment c
           JOIN comment_analysis ca ON ca.tenant_id = c.tenant_id AND ca.comment_id = c.id
           LEFT JOIN LATERAL (SELECT idea_id FROM product_idea_comment pc
                              WHERE pc.tenant_id = c.tenant_id AND pc.comment_id = c.id LIMIT 1) l ON true
           LEFT JOIN product_idea pi ON pi.id = l.idea_id
           WHERE c.tenant_id = %s AND c.custom_attributes->>'video_id' = %s AND c.status = 'ACTIVE'""",
        (tenant_id, video_id))
    return compute(rows)


# ----------------------------------------------------------------------------- ideas backlog

_IDEA_SELECT = """
    SELECT p.*, count(pc.comment_id) AS comments,
           COALESCE(sum(1 + c.like_count + 2 * c.reply_count), 0) AS reach,
           count(DISTINCT c.custom_attributes->>'video_id') AS videos,
           max(c.platform_created_at) AS last_comment_at
    FROM product_idea p
    LEFT JOIN product_idea_comment pc ON pc.idea_id = p.id
    LEFT JOIN comment c ON c.tenant_id = pc.tenant_id AND c.id = pc.comment_id
"""


def _idea(r: Dict) -> Dict:
    iso = lambda v: v.isoformat() if hasattr(v, "isoformat") else v  # noqa: E731
    return {"id": str(r["id"]), "title": r["title"], "topic": r.get("topic"),
            "topicLabel": TOPICS.get(r.get("topic") or "", None), "status": r["status"], "note": r.get("note"),
            "comments": int(r.get("comments") or 0), "reach": int(r.get("reach") or 0),
            "videos": int(r.get("videos") or 0), "lastCommentAt": iso(r.get("last_comment_at")),
            "createdAt": iso(r.get("created_at")), "updatedAt": iso(r.get("updated_at"))}


def list_ideas(tenant_id: str, status: Optional[str] = None, video_id: Optional[str] = None) -> List[Dict]:
    where, params = ["p.tenant_id = %s"], [tenant_id]
    if status:
        where.append("p.status = %s"); params.append(status.upper())
    if video_id:
        where.append("""EXISTS (SELECT 1 FROM product_idea_comment x JOIN comment xc ON xc.id = x.comment_id
                         WHERE x.idea_id = p.id AND xc.custom_attributes->>'video_id' = %s)""")
        params.append(video_id)
    rows = fetch_all(f"{_IDEA_SELECT} WHERE {' AND '.join(where)} GROUP BY p.id ORDER BY reach DESC, comments DESC",
                     tuple(params))
    return [_idea(r) for r in rows]


def get_idea(tenant_id: str, idea_id: str) -> Optional[Dict]:
    r = fetch_one(f"{_IDEA_SELECT} WHERE p.tenant_id = %s AND p.id = %s GROUP BY p.id", (tenant_id, idea_id))
    if not r:
        return None
    idea = _idea(r)
    idea["commentList"] = [{
        "id": str(c["id"]), "text": c["masked_text"], "likes": c["like_count"], "replies": c["reply_count"],
        "sentiment": c["sentiment"], "videoId": c["video_id"], "videoTitle": c["video_title"],
        "createdAt": c["platform_created_at"].isoformat() if c.get("platform_created_at") else None,
        "active": c["status"] == "ACTIVE",
    } for c in fetch_all(
        """SELECT c.id, c.masked_text, c.like_count, c.reply_count, c.platform_created_at, c.status, ca.sentiment,
                  c.custom_attributes->>'video_id' AS video_id, c.custom_attributes->>'video_title' AS video_title
           FROM product_idea_comment pc
           JOIN comment c ON c.tenant_id = pc.tenant_id AND c.id = pc.comment_id
           LEFT JOIN comment_analysis ca ON ca.tenant_id = c.tenant_id AND ca.comment_id = c.id
           WHERE pc.tenant_id = %s AND pc.idea_id = %s
           ORDER BY c.like_count DESC LIMIT 100""", (tenant_id, idea_id))]
    return idea


def update_idea(tenant_id: str, actor: str, idea_id: str, data: Dict) -> Optional[Dict]:
    status = (data.get("status") or "").upper() or None
    if status and status not in IDEA_STATUSES:
        raise ValueError(f"Status must be one of {', '.join(IDEA_STATUSES)}.")
    note = data.get("note")
    with cursor(commit=True) as cur:
        cur.execute(
            """UPDATE product_idea SET status = COALESCE(%s, status), title = COALESCE(%s, title),
                      note = CASE WHEN %s THEN NULLIF(%s, '') ELSE note END,
                      updated_by = %s, updated_at = now()
               WHERE tenant_id = %s AND id = %s RETURNING id, status, title""",
            (status, data.get("title"), note is not None, note, actor, tenant_id, idea_id))
        row = cur.fetchone()
        if row and status:
            append_audit(cur, tenant_id, actor, "USER", "IDEA_STATUS_CHANGED", "IDEA", idea_id,
                         {"status": status, "title": row["title"]})
    return get_idea(tenant_id, idea_id) if row else None
