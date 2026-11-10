"""Inbox, reply workflow and turnaround outcomes."""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional

from app.core import config
from app.core import llm
from app.core.database import append_audit, cursor, fetch_all, fetch_one
from app.pipeline.classifier import FastSentimentClassifier
from app.truth import outreach, youtube
from app.platform import billing
from app.platform.notifications import notify
from app.truth.verifier import MISINFO_VERDICTS
from app.workflow.state import Actor, WorkflowError, check_editable, next_status, outcome_from

_classifier = FastSentimentClassifier()


def _iso(v):
    return v.isoformat() if hasattr(v, "isoformat") else v


# ----------------------------------------------------------------------------- inbox

INBOX_SELECT = """
    SELECT c.id, c.platform, c.platform_comment_id, c.masked_text, c.like_count, c.reply_count,
           c.platform_created_at, c.author_hash, c.custom_attributes->>'video_id' AS video_id,
           c.custom_attributes->>'video_title' AS video_title,
           ca.sentiment, ca.impact_score, ca.priority, ca.churn_risk, ca.suggested_reply, ca.intent,
           c.custom_attributes->>'new_at' AS new_at, (c.custom_attributes->>'rating')::float AS rating,
           c.custom_attributes->>'listing_title' AS listing_title,
           l.claim_id, l.evidence, vc.verdict, vc.topic AS claim_topic, vc.timestamp_start AS claim_timestamp,
           r.id AS reply_id, r.status AS reply_status,
           CASE WHEN vc.verdict IS NULL THEN 'UNLINKED'
                WHEN vc.verdict IN ('MISLEADING', 'FALSE', 'UNVERIFIED_SPECULATION') THEN 'MISINFORMATION'
                ELSE 'VALID_CONCERN' END AS root_cause
    FROM comment c
    JOIN comment_analysis ca ON ca.tenant_id = c.tenant_id AND ca.comment_id = c.id
    LEFT JOIN comment_claim_link l ON l.tenant_id = c.tenant_id AND l.comment_id = c.id
    LEFT JOIN video_claim vc ON vc.id = l.claim_id
    LEFT JOIN LATERAL (
        SELECT id, status FROM reply WHERE tenant_id = c.tenant_id AND comment_id = c.id
        ORDER BY created_at DESC LIMIT 1) r ON true
"""


def _inbox_item(r: Dict) -> Dict:
    return {
        "id": str(r["id"]), "platform": r["platform"], "text": r["masked_text"], "likes": r["like_count"],
        "replies": r["reply_count"], "createdAt": _iso(r["platform_created_at"]),
        "authorHash": r["author_hash"], "videoId": r["video_id"], "videoTitle": r["video_title"],
        "sentiment": r["sentiment"], "impactScore": float(r["impact_score"] or 0), "priority": r["priority"],
        "rootCause": r["root_cause"],
        "claim": {"id": str(r["claim_id"]), "verdict": r["verdict"], "topic": r["claim_topic"],
                  "timestamp": r["claim_timestamp"], "evidence": r["evidence"]} if r["claim_id"] else None,
        "replyId": str(r["reply_id"]) if r["reply_id"] else None, "replyStatus": r["reply_status"],
        "intent": r.get("intent"), "isNew": bool(r.get("new_at")),
        "rating": r.get("rating"), "listingTitle": r.get("listing_title"),
    }


def inbox(tenant_id: str, video_id: Optional[str] = None, priority: Optional[str] = None,
          sentiment: Optional[str] = None, cause: Optional[str] = None, status: str = "OPEN",
          q: Optional[str] = None, limit: int = 50, offset: int = 0, intent: Optional[str] = None,
          fresh: bool = False, platform: Optional[str] = None) -> Dict:
    where, params = ["c.tenant_id = %s", "c.status = 'ACTIVE'"], [tenant_id]
    if video_id:
        where.append("c.custom_attributes->>'video_id' = %s"); params.append(video_id)
    if priority:
        where.append("ca.priority = %s"); params.append(priority)
    if sentiment:
        where.append("ca.sentiment = %s"); params.append(sentiment)
    if q:
        where.append("c.masked_text ILIKE %s"); params.append(f"%{q}%")
    if intent in ("IDEA", "BUY", "LEAVE", "QUESTION"):
        where.append("ca.intent = %s"); params.append(intent)
    elif intent:  # praise / complaint / other follow the current sentiment (see app/truth/growth.py)
        where.append("COALESCE(ca.intent, '') NOT IN ('IDEA', 'BUY', 'LEAVE', 'QUESTION') AND ca.sentiment = %s")
        params.append({"PRAISE": "POSITIVE", "COMPLAINT": "NEGATIVE"}.get(intent, "NEUTRAL"))
    if platform:  # YOUTUBE | AMAZON
        where.append("c.platform = %s"); params.append(platform.upper())
    if fresh:  # added by "Fetch new comments" or the schedule since the last full analysis
        where.append("c.custom_attributes ? 'new_at'")
    if status == "OPEN":
        where.append("(r.status IS NULL OR r.status <> 'POSTED')")
    elif status == "REPLIED":
        where.append("r.status = 'POSTED'")
    base = f"{INBOX_SELECT} WHERE {' AND '.join(where)}"
    if cause:
        base = f"SELECT * FROM ({base}) x WHERE x.root_cause = %s"
        params.append(cause)
    total = fetch_one(f"SELECT count(*) AS n FROM ({base}) t", tuple(params))["n"]
    rows = fetch_all(f"SELECT * FROM ({base}) t ORDER BY t.impact_score DESC, t.like_count DESC LIMIT %s OFFSET %s",
                     tuple(params + [limit, offset]))
    return {"items": [_inbox_item(r) for r in rows], "total": int(total), "limit": limit, "offset": offset}


def comment_detail(tenant_id: str, comment_id: str) -> Optional[Dict]:
    r = fetch_one(f"{INBOX_SELECT} WHERE c.tenant_id = %s AND c.id = %s", (tenant_id, comment_id))
    if not r:
        return None
    item = _inbox_item(r)
    item["churnRisk"] = float(r["churn_risk"] or 0)
    if r["claim_id"]:
        k = fetch_one(
            """SELECT vc.creator_quote, vc.fact_check_analysis, vc.official_citation, pk.document_title,
                      pk.clause_ref, pk.official_statement
               FROM video_claim vc LEFT JOIN product_knowledge pk ON pk.id = vc.rag_knowledge_id
               WHERE vc.id = %s""", (r["claim_id"],))
        if k:
            item["claim"].update({"quote": k["creator_quote"], "analysis": k["fact_check_analysis"],
                                  "officialStatement": k["official_statement"],
                                  "source": k["document_title"] or k["official_citation"]})
    item["replyHistory"] = [_reply(x) for x in fetch_all(
        f"{REPLY_SELECT} WHERE r.tenant_id = %s AND r.comment_id = %s ORDER BY r.created_at DESC",
        (tenant_id, comment_id))]
    return item


# ----------------------------------------------------------------------------- replies

REPLY_SELECT = """
    SELECT r.*, au.full_name AS author_name, ap.full_name AS approver_name, c.masked_text AS comment_text, c.custom_attributes->>'video_title' AS video_title,
           c.custom_attributes->>'video_id' AS video_id, ca.priority, ca.sentiment AS comment_sentiment,
           ro.outcome, ro.follow_up_text, ro.evaluated_at,
           (SELECT json_agg(json_build_object('step', s.step_name, 'decision', s.decision, 'reviewerId', s.reviewer_id,
                                              'comments', s.comments, 'at', s.action_at) ORDER BY s.action_at)
              FROM approval_step s WHERE s.reply_id = r.id) AS steps,
           (SELECT json_object_agg(m.keycloak_user_id, coalesce(m.full_name, m.email)) FROM tenant_user m
              WHERE m.tenant_id = r.tenant_id) AS people
    FROM reply r
    JOIN comment c ON c.tenant_id = r.tenant_id AND c.id = r.comment_id
    LEFT JOIN tenant_user au ON au.tenant_id = r.tenant_id AND au.keycloak_user_id = r.author_id::text
    LEFT JOIN tenant_user ap ON ap.tenant_id = r.tenant_id AND ap.keycloak_user_id = r.approver_id::text
    LEFT JOIN comment_analysis ca ON ca.tenant_id = c.tenant_id AND ca.comment_id = c.id
    LEFT JOIN LATERAL (SELECT outcome, follow_up_text, evaluated_at FROM reply_outcome
                       WHERE reply_id = r.id ORDER BY evaluated_at DESC LIMIT 1) ro ON true
"""

def _reply(r: Dict) -> Dict:
    now = datetime.now(timezone.utc)
    due = r["sla_due_at"]
    return {
        "id": str(r["id"]), "commentId": str(r["comment_id"]), "commentText": r["comment_text"],
        "videoId": r["video_id"], "videoTitle": r["video_title"], "priority": r["priority"],
        "commentSentiment": r["comment_sentiment"], "text": r["reply_text"], "status": r["status"],
        "authorId": str(r["author_id"]), "authorName": r.get("author_name") or "Former member",
        "approverId": str(r["approver_id"]) if r.get("approver_id") else None,
        "approverName": (r.get("approver_name") or "Former member") if r.get("approver_id") else None,
        "slaDueAt": _iso(due), "slaBreached": r["status"] not in ("POSTED",) and due is not None and due < now,
        "rejectionReason": r.get("rejection_reason"), "deliveryMode": r.get("delivery_mode"),
        "platformReplyId": r.get("platform_reply_id"), "createdAt": _iso(r["created_at"]),
        "updatedAt": _iso(r["updated_at"]), "submittedAt": _iso(r.get("submitted_at")),
        "approvedAt": _iso(r.get("approved_at")), "postedAt": _iso(r.get("posted_at")),
        "claimId": str(r["claim_id"]) if r.get("claim_id") else None,
        "outcome": r.get("outcome"), "followUpText": r.get("follow_up_text"),
        "steps": [{**s, "reviewerName": (r.get("people") or {}).get(str(s.get("reviewerId")), "Reviewer")}
                  for s in (r.get("steps") or [])],
    }


def list_replies(tenant_id: str, status: Optional[str] = None, limit: int = 100) -> List[Dict]:
    where, params = ["r.tenant_id = %s"], [tenant_id]
    if status:
        where.append("r.status = ANY(%s)"); params.append(status.split(","))
    rows = fetch_all(f"{REPLY_SELECT} WHERE {' AND '.join(where)} ORDER BY r.updated_at DESC LIMIT %s",
                     tuple(params + [limit]))
    return [_reply(r) for r in rows]


def get_reply(tenant_id: str, reply_id: str) -> Optional[Dict]:
    r = fetch_one(f"{REPLY_SELECT} WHERE r.tenant_id = %s AND r.id = %s", (tenant_id, reply_id))
    return _reply(r) if r else None


def suggest_reply(tenant_id: str, comment_id: str, brand_name: str) -> Dict:
    item = comment_detail(tenant_id, comment_id)
    if not item:
        raise WorkflowError("Comment not found.", 404)
    claim = item.get("claim")
    stored = fetch_one("SELECT suggested_reply FROM comment_analysis WHERE tenant_id = %s AND comment_id = %s",
                       (tenant_id, comment_id))
    with llm.use_tenant(tenant_id):
        text = outreach.reply_draft(
            item["text"], item["sentiment"],
            {"verdict": claim["verdict"], "official_statement": claim.get("officialStatement"),
             "fact_check_analysis": claim.get("analysis"), "document_title": claim.get("source")} if claim else None,
            brand_name, None)
    cites_fact = bool(claim and claim["verdict"] in MISINFO_VERDICTS)
    if not cites_fact and stored and stored.get("suggested_reply") and item["sentiment"] == "NEGATIVE":
        text = stored["suggested_reply"]
    return {"text": text, "citesOfficialFact": cites_fact}


def create_reply(tenant_id: str, actor: Actor, comment_id: str, text: str) -> Dict:
    if not (text or "").strip():
        raise WorkflowError("Reply text can't be empty.", 400)
    c = fetch_one(
        """SELECT c.id, c.platform, ca.priority, l.claim_id FROM comment c
           JOIN comment_analysis ca ON ca.tenant_id = c.tenant_id AND ca.comment_id = c.id
           LEFT JOIN comment_claim_link l ON l.tenant_id = c.tenant_id AND l.comment_id = c.id
           WHERE c.tenant_id = %s AND c.id = %s""", (tenant_id, comment_id))
    if not c:
        raise WorkflowError("Comment not found.", 404)
    open_reply = fetch_one("""SELECT id FROM reply WHERE tenant_id = %s AND comment_id = %s
                              AND status IN ('DRAFT', 'IN_REVIEW', 'REJECTED', 'APPROVED')""", (tenant_id, comment_id))
    if open_reply:
        raise WorkflowError("This comment already has a reply in progress.")
    reply_id = str(uuid.uuid4())
    due = datetime.now(timezone.utc) + timedelta(hours=config.SLA_HOURS.get(c["priority"], 24))
    with cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO reply (id, tenant_id, comment_id, platform, reply_text, status, author_id, sla_due_at, claim_id)
               VALUES (%s, %s, %s, %s, %s, 'DRAFT', %s, %s, %s)""",
            (reply_id, tenant_id, comment_id, c["platform"], text.strip(), actor.id, due, c["claim_id"]))
        append_audit(cur, tenant_id, actor.id, "USER", "REPLY_DRAFTED", "REPLY", reply_id,
                     {"comment_id": comment_id, "status": "DRAFT"})
    return get_reply(tenant_id, reply_id)


def edit_reply(tenant_id: str, actor: Actor, reply_id: str, text: str) -> Dict:
    current = _load(tenant_id, reply_id)
    check_editable(current["status"])
    if not (text or "").strip():
        raise WorkflowError("Reply text can't be empty.", 400)
    with cursor(commit=True) as cur:
        cur.execute("UPDATE reply SET reply_text = %s, updated_at = now() WHERE id = %s", (text.strip(), reply_id))
        append_audit(cur, tenant_id, actor.id, "USER", "REPLY_EDITED", "REPLY", reply_id,
                     {"status": current["status"]}, {"text": current["reply_text"]})
    return get_reply(tenant_id, reply_id)


def transition(tenant_id: str, actor: Actor, reply_id: str, action: str, reason: Optional[str] = None) -> Dict:
    current = _load(tenant_id, reply_id)
    target = next_status(action, current["status"], actor, str(current["author_id"]), reason)
    if action == "post":
        billing.check_quota(tenant_id, "REPLY_POSTED")
    with cursor(commit=True) as cur:
        if action == "submit":
            cur.execute("""UPDATE reply SET status = %s, submitted_at = now(), rejection_reason = NULL,
                           updated_at = now() WHERE id = %s""", (target, reply_id))
        elif action in ("approve", "reject"):
            cur.execute(
                """UPDATE reply SET status = %s, approver_id = %s, rejection_reason = %s,
                          approved_at = CASE WHEN %s = 'APPROVED' THEN now() ELSE approved_at END, updated_at = now()
                   WHERE id = %s""", (target, actor.id, reason if action == "reject" else None, target, reply_id))
            cur.execute("""INSERT INTO approval_step (tenant_id, reply_id, step_name, reviewer_id, decision, comments)
                           VALUES (%s, %s, 'BRAND_REVIEW', %s, %s, %s)""",
                        (tenant_id, reply_id, actor.id, target, reason))
        elif action == "post":
            # Live posting needs a YouTube OAuth connection (yudhix-link). Until then replies are
            # recorded as SIMULATED so the workflow and audit trail can be exercised end to end.
            cur.execute(
                """UPDATE reply SET status = 'POSTED', posted_at = now(), delivery_mode = 'SIMULATED',
                          platform_reply_id = %s, updated_at = now() WHERE id = %s""",
                (f"sim-{uuid.uuid4().hex[:12]}", reply_id))
            cur.execute(
                """INSERT INTO reply_outcome (id, tenant_id, reply_id, comment_id, initial_sentiment, turned_around, source)
                   SELECT %s, r.tenant_id, r.id, r.comment_id, COALESCE(ca.sentiment, 'NEUTRAL'), false, 'PENDING'
                   FROM reply r LEFT JOIN comment_analysis ca ON ca.tenant_id = r.tenant_id AND ca.comment_id = r.comment_id
                   WHERE r.id = %s""", (str(uuid.uuid4()), reply_id))
        append_audit(cur, tenant_id, actor.id, "USER", f"REPLY_{target}", "REPLY", reply_id,
                     {"from": current["status"], "to": target, "reason": reason})
    author = str(current["author_id"])
    if action == "post":
        billing.record(tenant_id, "REPLY_POSTED", 1, key=f"reply:{reply_id}")
    elif action == "submit":
        notify(tenant_id, "review", "A reply needs your review", _excerpt(current["reply_text"]), "/approvals",
               roles=["approver", "admin"], exclude=actor.id)
    elif action == "approve":
        notify(tenant_id, "review", "Your reply was approved", "It's ready to post.", "/approvals",
               user_ids=[author], exclude=actor.id)
    elif action == "reject":
        notify(tenant_id, "review", "Changes requested on your reply", reason or "", "/approvals",
               user_ids=[author], exclude=actor.id)
    return get_reply(tenant_id, reply_id)


def _excerpt(text: str, n: int = 140) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= n else text[: n - 1] + "…"


def _load(tenant_id: str, reply_id: str) -> Dict:
    r = fetch_one("SELECT * FROM reply WHERE tenant_id = %s AND id = %s", (tenant_id, reply_id))
    if not r:
        raise WorkflowError("Reply not found.", 404)
    return r


# ----------------------------------------------------------------------------- outcomes

def record_outcome(tenant_id: str, actor: Actor, reply_id: str, follow_up_text: Optional[str],
                   outcome: Optional[str]) -> Dict:
    """Record what happened after a reply: from the customer's follow-up text, or set directly."""
    r = _load(tenant_id, reply_id)
    if r["status"] != "POSTED":
        raise WorkflowError("Outcomes can only be recorded for posted replies.")
    row = fetch_one("SELECT * FROM reply_outcome WHERE reply_id = %s ORDER BY evaluated_at DESC LIMIT 1", (reply_id,))
    initial = row["initial_sentiment"] if row else "NEGATIVE"
    follow_sentiment = None
    if follow_up_text:
        follow_sentiment, _ = _classifier.classify(follow_up_text)
        outcome = outcome or outcome_from(initial, follow_sentiment)
    if outcome not in ("IMPROVED", "NEUTRAL", "WORSENED"):
        raise WorkflowError("Give the customer's follow-up text or pick an outcome.", 400)
    with cursor(commit=True) as cur:
        if row:
            cur.execute(
                """UPDATE reply_outcome SET outcome = %s, follow_up_text = %s, checkpoint_24h_sentiment = %s,
                          turned_around = %s, source = 'MANUAL', evaluated_at = now(), updated_at = now()
                   WHERE id = %s""",
                (outcome, follow_up_text, follow_sentiment, outcome == "IMPROVED", row["id"]))
        else:
            cur.execute(
                """INSERT INTO reply_outcome (id, tenant_id, reply_id, comment_id, initial_sentiment, outcome,
                       follow_up_text, checkpoint_24h_sentiment, turned_around, source)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'MANUAL')""",
                (str(uuid.uuid4()), tenant_id, reply_id, r["comment_id"], initial, outcome, follow_up_text,
                 follow_sentiment, outcome == "IMPROVED"))
        append_audit(cur, tenant_id, actor.id, "USER", "OUTCOME_RECORDED", "REPLY", reply_id, {"outcome": outcome})
    return get_reply(tenant_id, reply_id)


def check_live_outcomes(tenant_id: str) -> Dict:
    """For replies posted LIVE: read the thread and score the original author's follow-up."""
    rows = fetch_all(
        """SELECT r.id, r.posted_at, c.platform_comment_id, c.author_hash, ro.initial_sentiment
           FROM reply r JOIN comment c ON c.tenant_id = r.tenant_id AND c.id = r.comment_id
           LEFT JOIN reply_outcome ro ON ro.reply_id = r.id
           WHERE r.tenant_id = %s AND r.status = 'POSTED' AND r.delivery_mode = 'LIVE'
             AND (ro.outcome IS NULL)""", (tenant_id,))
    simulated = fetch_one("""SELECT count(*) AS n FROM reply WHERE tenant_id = %s AND status = 'POSTED'
                             AND delivery_mode = 'SIMULATED'""", (tenant_id,))["n"]
    checked = 0
    from app.truth.pipeline import author_hash  # local import: pipeline imports workflow-free modules only
    for r in rows:
        for reply in youtube.fetch_thread_replies(r["platform_comment_id"]):
            if author_hash(tenant_id, "YOUTUBE", reply["author_channel_id"]) != r["author_hash"]:
                continue
            sentiment, _ = _classifier.classify(reply["text"])
            outcome = outcome_from(r["initial_sentiment"] or "NEGATIVE", sentiment)
            with cursor(commit=True) as cur:
                cur.execute("""UPDATE reply_outcome SET outcome = %s, checkpoint_24h_sentiment = %s, turned_around = %s,
                               source = 'PLATFORM', evaluated_at = now(), updated_at = now() WHERE reply_id = %s""",
                            (outcome, sentiment, outcome == "IMPROVED", r["id"]))
            checked += 1
            break
    return {"checked": checked, "awaitingFollowUp": len(rows) - checked, "simulatedReplies": int(simulated),
            "youtubeConnected": youtube.has_api_key()}
