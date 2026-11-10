"""Read models for the truth-first screens: videos, claims, audience impact, knowledge, outreach."""
from typing import Dict, List, Optional

from app.core import llm
from app.core.database import append_audit, cursor, fetch_all, fetch_one
from app.truth import outreach
from app.truth.attribution import root_cause
from app.truth.verifier import MISINFO_VERDICTS, VERDICTS


def _iso(v):
    return v.isoformat() if hasattr(v, "isoformat") else v


def _video(r: Dict, comment_stats: Optional[Dict] = None) -> Dict:
    s = comment_stats or {}
    return {
        "id": str(r["id"]), "videoId": r["video_id"], "title": r["video_title"], "channel": r["channel_title"],
        "url": r["video_url"],
        "thumbnailUrl": r.get("thumbnail_url") or f"https://i.ytimg.com/vi/{r['video_id']}/hqdefault.jpg",
        "publishedDate": r.get("published_date"), "durationSeconds": r.get("duration_seconds") or 0,
        "viewCount": r.get("view_count"),
        "factualAccuracy": float(r.get("factual_accuracy_score") or 0),
        "rageBaitScore": float(r.get("rage_bait_score") or 0),
        "sensationalismGrade": r.get("sensationalism_grade"),
        "totalClaims": r.get("total_claims") or 0, "misleadingClaims": r.get("misleading_claims_count") or 0,
        "summary": r.get("summary"), "transcriptSource": r.get("transcript_source"),
        "analysisMethod": r.get("analysis_method"),
        "productId": str(r["product_id"]) if r.get("product_id") else None,
        "analyzedAt": _iso(r.get("analyzed_at") or r.get("created_at")),
        "comments": int(s.get("total") or 0), "negativeComments": int(s.get("negative") or 0),
        "positiveComments": int(s.get("positive") or 0), "linkedComments": int(s.get("linked") or 0),
        "newComments": int(s.get("fresh") or 0),
        "commentsCheckedAt": _iso(r.get("comments_checked_at")),
        "factsStale": bool(r.get("facts_stale")), "factsCheckedAt": _iso(r.get("facts_checked_at")),
    }


def _comment_stats(tenant_id: str, video_id: Optional[str] = None) -> Dict[str, Dict]:
    rows = fetch_all(
        f"""SELECT c.custom_attributes->>'video_id' AS video_id, count(*) AS total,
                   count(*) FILTER (WHERE ca.sentiment = 'NEGATIVE') AS negative,
                   count(*) FILTER (WHERE ca.sentiment = 'POSITIVE') AS positive,
                   count(l.comment_id) AS linked,
                   count(*) FILTER (WHERE c.custom_attributes ? 'new_at') AS fresh
            FROM comment c
            LEFT JOIN comment_analysis ca ON ca.tenant_id = c.tenant_id AND ca.comment_id = c.id
            LEFT JOIN comment_claim_link l ON l.tenant_id = c.tenant_id AND l.comment_id = c.id
            WHERE c.tenant_id = %s AND c.status = 'ACTIVE' {"AND c.custom_attributes->>'video_id' = %s" if video_id else ""}
            GROUP BY 1""",
        (tenant_id, video_id) if video_id else (tenant_id,))
    return {r["video_id"]: r for r in rows}


def list_videos(tenant_id: str) -> List[Dict]:
    stats = _comment_stats(tenant_id)
    rows = fetch_all("""SELECT * FROM video_truth_analysis WHERE tenant_id = %s
                        ORDER BY COALESCE(analyzed_at, created_at) DESC""", (tenant_id,))
    return [_video(r, stats.get(r["video_id"])) for r in rows]


def _claim(r: Dict) -> Dict:
    return {
        "id": str(r["id"]), "timestamp": r["timestamp_start"], "timestampSeconds": r.get("timestamp_seconds") or 0,
        "quote": r["creator_quote"], "topic": r["topic"], "verdict": r["verdict"],
        "isMisinformation": r["verdict"] in MISINFO_VERDICTS,
        "confidence": float(r.get("confidence_score") or 0), "analysis": r["fact_check_analysis"],
        "citation": r.get("official_citation"), "linkedComments": r.get("incited_comments_count") or 0,
        "sentimentImpact": r.get("sentiment_impact"), "verificationMethod": r.get("verification_method"),
        "sourceQuote": r.get("source_quote"), "needsReview": bool(r.get("needs_review")),
        "reviewReason": r.get("review_reason"),
        "knowledge": {
            "id": str(r["knowledge_id"]), "title": r.get("document_title"), "clauseRef": r.get("clause_ref"),
            "statement": r.get("official_statement"), "source": r.get("citation_source"),
        } if r.get("knowledge_id") else None,
    }


def get_claims(tenant_id: str, analysis_id: str) -> List[Dict]:
    rows = fetch_all(
        """SELECT vc.*, pk.id AS knowledge_id, pk.document_title, pk.clause_ref, pk.official_statement,
                  pk.citation_source
           FROM video_claim vc LEFT JOIN product_knowledge pk ON pk.id = vc.rag_knowledge_id
           WHERE vc.tenant_id = %s AND vc.video_analysis_id = %s ORDER BY vc.timestamp_seconds""",
        (tenant_id, analysis_id))
    return [_claim(r) for r in rows]


def get_video(tenant_id: str, video_id: str) -> Optional[Dict]:
    r = fetch_one("SELECT * FROM video_truth_analysis WHERE tenant_id = %s AND video_id = %s", (tenant_id, video_id))
    if not r:
        return None
    video = _video(r, _comment_stats(tenant_id, video_id).get(video_id))
    video["claims"] = get_claims(tenant_id, str(r["id"]))
    return video


def set_video_product(tenant_id: str, actor: str, video_id: str, product_id: Optional[str]) -> Optional[Dict]:
    """Link a video (and its comments) to a product of this workspace, or unlink it (None)."""
    if product_id and not fetch_one("SELECT 1 FROM product WHERE tenant_id = %s AND id = %s", (tenant_id, product_id)):
        raise ValueError("That product isn't in this workspace.")
    with cursor(commit=True) as cur:
        cur.execute("UPDATE video_truth_analysis SET product_id = %s WHERE tenant_id = %s AND video_id = %s RETURNING id",
                    (product_id, tenant_id, video_id))
        if not cur.fetchone():
            return None
        cur.execute("""UPDATE comment SET product_id = %s WHERE tenant_id = %s AND platform = 'YOUTUBE'
                       AND custom_attributes->>'video_id' = %s""", (product_id, tenant_id, video_id))
        append_audit(cur, tenant_id, actor, "USER", "VIDEO_PRODUCT_CHANGED", "VIDEO", video_id, {"product_id": product_id})
    return get_video(tenant_id, video_id)


def override_claim(tenant_id: str, actor: str, claim_id: str, verdict: str, note: Optional[str]) -> Optional[Dict]:
    """A person sets the verdict. Kept through re-checks; comments are re-linked by the caller."""
    if verdict not in VERDICTS:
        raise ValueError("Unknown verdict.")
    with cursor(commit=True) as cur:
        cur.execute(
            """UPDATE video_claim SET verdict = %s, verification_method = 'HUMAN', needs_review = false,
                      review_reason = NULL, confidence_score = 1.0, reviewed_by = %s, reviewed_at = now(),
                      fact_check_analysis = COALESCE(NULLIF(%s, ''), fact_check_analysis)
               WHERE tenant_id = %s AND id = %s
               RETURNING video_analysis_id, verdict""", (verdict, actor, note or "", tenant_id, claim_id))
        row = cur.fetchone()
        if not row:
            return None
        cur.execute("SELECT video_id FROM video_truth_analysis WHERE id = %s", (row["video_analysis_id"],))
        video_id = cur.fetchone()["video_id"]
        append_audit(cur, tenant_id, actor, "USER", "CLAIM_VERDICT_OVERRIDDEN", "CLAIM", claim_id,
                     {"verdict": verdict, "video_id": video_id})
    return {"videoId": video_id, "verdict": verdict}


def get_impact(tenant_id: str, video_id: str) -> Optional[Dict]:
    """Audience impact: which claims drove which reactions, and the root-cause split."""
    video = get_video(tenant_id, video_id)
    if not video:
        return None
    rows = fetch_all(
        """SELECT ca.sentiment, vc.id AS claim_id, vc.verdict, count(*) AS n
           FROM comment c
           JOIN comment_analysis ca ON ca.tenant_id = c.tenant_id AND ca.comment_id = c.id
           LEFT JOIN comment_claim_link l ON l.tenant_id = c.tenant_id AND l.comment_id = c.id
           LEFT JOIN video_claim vc ON vc.id = l.claim_id
           WHERE c.tenant_id = %s AND c.custom_attributes->>'video_id' = %s AND c.status = 'ACTIVE'
           GROUP BY 1, 2, 3""",
        (tenant_id, video_id))

    per_claim: Dict[str, Dict] = {c["id"]: {"positive": 0, "negative": 0, "neutral": 0} for c in video["claims"]}
    causes = {"MISINFORMATION": {"total": 0, "negative": 0}, "VALID_CONCERN": {"total": 0, "negative": 0},
              "UNLINKED": {"total": 0, "negative": 0}}
    for r in rows:
        key = (r["sentiment"] or "NEUTRAL").lower()
        n = int(r["n"])
        cause = root_cause(r["verdict"])
        causes[cause]["total"] += n
        if key == "negative":
            causes[cause]["negative"] += n
        if r["claim_id"]:
            per_claim[str(r["claim_id"])][key if key in ("positive", "negative") else "neutral"] += n

    negative_total = sum(c["negative"] for c in causes.values())
    claims = []
    for c in video["claims"]:
        counts = per_claim.get(c["id"], {})
        claims.append({**c, "sentiment": counts, "linkedComments": sum(counts.values())})
    misinfo_neg = causes["MISINFORMATION"]["negative"]
    return {
        "video": {k: v for k, v in video.items() if k != "claims"},
        "claims": sorted(claims, key=lambda c: -c["linkedComments"]),
        "rootCauses": [{"cause": k, **v} for k, v in causes.items()],
        "negativeComments": negative_total,
        "misinformationShareOfNegative": round(misinfo_neg / negative_total, 3) if negative_total else 0.0,
        "headline": _headline(video, claims, misinfo_neg, negative_total),
    }


def _headline(video: Dict, claims: List[Dict], misinfo_neg: int, negative_total: int) -> str:
    if not negative_total:
        return "No negative reaction to attribute yet."
    top = max((c for c in claims if c["isMisinformation"]), key=lambda c: c["sentiment"].get("negative", 0), default=None)
    share = round(100 * misinfo_neg / negative_total)
    if top and top["sentiment"].get("negative"):
        return (f"{share}% of negative comments react to misinformation. The biggest driver is the claim at "
                f"{top['timestamp']} (\"{top['topic']}\").")
    return f"{share}% of negative comments react to misinformation."


def claim_comments(tenant_id: str, claim_id: str, limit: int = 50) -> List[Dict]:
    return [{
        "id": str(r["id"]), "text": r["masked_text"], "likes": r["like_count"], "replies": r["reply_count"],
        "sentiment": r["sentiment"], "priority": r["priority"], "impactScore": float(r["impact_score"] or 0),
        "linkScore": float(r["score"]), "linkMethod": r["method"], "evidence": r.get("evidence"),
    } for r in fetch_all(
        """SELECT c.id, c.masked_text, c.like_count, c.reply_count, ca.sentiment, ca.priority, ca.impact_score,
                  l.score, l.method, l.evidence
           FROM comment_claim_link l
           JOIN comment c ON c.tenant_id = l.tenant_id AND c.id = l.comment_id
           LEFT JOIN comment_analysis ca ON ca.tenant_id = c.tenant_id AND ca.comment_id = c.id
           WHERE l.tenant_id = %s AND l.claim_id = %s
           ORDER BY c.like_count DESC LIMIT %s""",
        (tenant_id, claim_id, limit))]


# ----------------------------------------------------------------------------- knowledge

def _knowledge(r: Dict) -> Dict:
    return {"id": str(r["id"]), "productId": str(r["product_id"]) if r.get("product_id") else None,
            "productName": r.get("product_name"), "title": r["document_title"], "category": r["category"],
            "clauseRef": r.get("clause_ref"), "statement": r["official_statement"],
            "source": r.get("citation_source"), "verifiedAt": _iso(r.get("verified_at")),
            "documentId": str(r["document_id"]) if r.get("document_id") else None,
            "usedByClaims": int(r.get("used_by") or 0)}


def stale_videos(tenant_id: str) -> List[str]:
    """Videos whose claims were checked before the knowledge base last changed."""
    return [r["video_id"] for r in fetch_all(
        "SELECT video_id FROM video_truth_analysis WHERE tenant_id = %s AND facts_stale ORDER BY analyzed_at DESC",
        (tenant_id,))]


def list_knowledge(tenant_id: str) -> List[Dict]:
    return [_knowledge(r) for r in fetch_all(
        """SELECT pk.*, p.name AS product_name,
                  (SELECT count(*) FROM video_claim vc WHERE vc.rag_knowledge_id = pk.id) AS used_by
           FROM product_knowledge pk LEFT JOIN product p ON p.id = pk.product_id
           WHERE pk.tenant_id = %s ORDER BY pk.category, pk.document_title""", (tenant_id,))]


def add_knowledge(tenant_id: str, actor: str, data: Dict) -> Dict:
    with cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO product_knowledge (tenant_id, product_id, document_title, category, clause_ref,
                   official_statement, citation_source)
               VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING *""",
            (tenant_id, data.get("productId") or None, data["title"], data.get("category") or "General",
             data.get("clauseRef"), data["statement"], data.get("source")))
        row = dict(cur.fetchone())
        append_audit(cur, tenant_id, actor, "USER", "KNOWLEDGE_ADDED", "KNOWLEDGE", str(row["id"]),
                     {"title": row["document_title"]})
    return _knowledge(row)


def delete_knowledge(tenant_id: str, actor: str, knowledge_id: str) -> bool:
    with cursor(commit=True) as cur:
        cur.execute("DELETE FROM product_knowledge WHERE tenant_id = %s AND id = %s RETURNING document_title",
                    (tenant_id, knowledge_id))
        row = cur.fetchone()
        if row:
            append_audit(cur, tenant_id, actor, "USER", "KNOWLEDGE_DELETED", "KNOWLEDGE", knowledge_id,
                         {"title": row["document_title"]})
        return bool(row)


# ----------------------------------------------------------------------------- creator outreach

def _outreach(r: Dict) -> Dict:
    return {"id": str(r["id"]), "videoId": r["video_id"], "channel": r.get("channel_title"),
            "claimIds": [str(x) for x in (r.get("claim_ids") or [])], "subject": r["subject"], "body": r["body"],
            "status": r["status"], "createdAt": _iso(r.get("created_at")), "updatedAt": _iso(r.get("updated_at"))}


def list_outreach(tenant_id: str, video_id: str) -> List[Dict]:
    return [_outreach(r) for r in fetch_all(
        "SELECT * FROM creator_outreach WHERE tenant_id = %s AND video_id = %s ORDER BY created_at DESC",
        (tenant_id, video_id))]


def create_outreach(tenant_id: str, actor: str, video_id: str, claim_ids: Optional[List[str]],
                    brand_name: str) -> Optional[Dict]:
    video = get_video(tenant_id, video_id)
    if not video:
        return None
    claims = [c for c in video["claims"] if (c["id"] in claim_ids if claim_ids else c["isMisinformation"])]
    if not claims:
        raise ValueError("Pick at least one claim. This video has no misleading claims to clarify.")
    with llm.use_tenant(tenant_id):
        note = _creator_note(video, claims, brand_name)
    return _save_outreach(tenant_id, actor, video_id, video, claims, note)


def _creator_note(video: Dict, claims: List[Dict], brand_name: str) -> Dict:
    return outreach.creator_note(video["channel"], video["title"], [{
        "timestamp_start": c["timestamp"], "creator_quote": c["quote"],
        "official_statement": (c["knowledge"] or {}).get("statement"), "fact_check_analysis": c["analysis"],
        "document_title": (c["knowledge"] or {}).get("title"), "clause_ref": (c["knowledge"] or {}).get("clauseRef"),
        "official_citation": c["citation"],
    } for c in claims], brand_name)


def _save_outreach(tenant_id: str, actor: str, video_id: str, video: Dict, claims: List[Dict], note: Dict) -> Dict:
    with cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO creator_outreach (tenant_id, video_id, channel_title, claim_ids, subject, body, created_by)
               VALUES (%s, %s, %s, %s::uuid[], %s, %s, %s) RETURNING *""",
            (tenant_id, video_id, video["channel"], [c["id"] for c in claims], note["subject"], note["body"], actor))
        row = dict(cur.fetchone())
        append_audit(cur, tenant_id, actor, "USER", "CREATOR_NOTE_DRAFTED", "VIDEO", video_id,
                     {"outreach_id": str(row["id"]), "claims": len(claims)})
    return _outreach(row)


def update_outreach(tenant_id: str, actor: str, outreach_id: str, data: Dict) -> Optional[Dict]:
    with cursor(commit=True) as cur:
        cur.execute(
            """UPDATE creator_outreach SET subject = COALESCE(%s, subject), body = COALESCE(%s, body),
                      status = COALESCE(%s, status), updated_at = now()
               WHERE tenant_id = %s AND id = %s RETURNING *""",
            (data.get("subject"), data.get("body"), data.get("status"), tenant_id, outreach_id))
        row = cur.fetchone()
        if row and data.get("status") == "SENT":
            append_audit(cur, tenant_id, actor, "USER", "CREATOR_NOTE_SENT", "VIDEO", row["video_id"],
                         {"outreach_id": outreach_id})
    return _outreach(dict(row)) if row else None
