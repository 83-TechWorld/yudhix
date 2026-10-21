import os
import uuid
import hashlib
import json
import logging
from typing import List, Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)

DB_NAME = os.getenv("PG_DB", "yudhix")
DB_USER = os.getenv("PG_USER", "postgres")
DB_PASSWORD = os.getenv("PG_PASSWORD", "postgres")
DB_HOST = os.getenv("PG_HOST", "localhost")
DB_PORT = int(os.getenv("PG_PORT", "5432"))

DEFAULT_TENANT_ID = "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
DEFAULT_SOURCE_ID = "c0a80101-0000-0000-0000-000000000001"
DEFAULT_PRODUCT_ID = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"


def get_db_connection():
    try:
        return psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
    except Exception as e:
        # Fallback without password if local trust/peer
        return psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            host=DB_HOST,
            port=DB_PORT
        )


def persist_comment_and_analysis(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Persists a raw comment, its privacy-masked text, deep AI analysis, and granular aspects
    into PostgreSQL tables: comment, comment_analysis, and comment_aspect.
    """
    tenant_id = data.get("tenant_id") or DEFAULT_TENANT_ID
    platform = (data.get("platform") or "YOUTUBE").upper()
    platform_comment_id = str(data.get("comment_id") or data.get("platform_comment_id") or str(uuid.uuid4()))
    
    # Generate deterministic UUID for comment id
    comment_uuid = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{tenant_id}:{platform}:{platform_comment_id}"))
    source_id = data.get("source_id") or DEFAULT_SOURCE_ID
    product_id = data.get("product_id") or DEFAULT_PRODUCT_ID
    
    raw_text = data.get("raw_text") or data.get("masked_text") or ""
    masked_text = data.get("masked_text") or raw_text
    author_hash = data.get("author_hash") or f"sha256:{hashlib.sha256(platform_comment_id.encode()).hexdigest()[:16]}...yt"
    content_hash = hashlib.sha256(raw_text.encode('utf-8')).hexdigest()
    
    like_count = int(data.get("likes") or data.get("like_count") or 0)
    reply_count = int(data.get("replies") or data.get("reply_count") or 0)
    
    sentiment = (data.get("sentiment") or "NEUTRAL").upper()
    sentiment_score = float(data.get("sentiment_score") or 0.0)
    intent = (data.get("intent") or "GENERAL").upper()
    churn_risk = float(data.get("churn_risk") or 0.0)
    impact_score = float(data.get("impact_score") or (80.0 if sentiment == "NEGATIVE" else 45.0))
    priority = data.get("priority") or ("P1" if (sentiment == "NEGATIVE" and churn_risk > 0.4) else "P2")
    toxic = bool(data.get("toxic", False))
    suggested_reply = data.get("suggested_reply") or "Thank you for reaching out to us. Our customer team is here to help!"
    aspects = data.get("aspects") or []

    custom_attrs = data.get("custom_attributes") or {}
    if data.get("channel_title"):
        custom_attrs["channel_title"] = data.get("channel_title")
    if data.get("video_id"):
        custom_attrs["video_id"] = data.get("video_id")
    if data.get("video_title"):
        custom_attrs["video_title"] = data.get("video_title")
    if data.get("video_url"):
        custom_attrs["video_url"] = data.get("video_url")
    custom_attrs_json = json.dumps(custom_attrs)
    platform_created_at = data.get("platform_created_at") or "now()"

    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            # 1. Insert or update core comment
            cur.execute("""
                INSERT INTO comment (
                    tenant_id, id, platform, platform_comment_id, parent_comment_id,
                    source_id, product_id, author_hash, author_key_version,
                    masked_text, text_expires_at, language, country_hint,
                    like_count, reply_count, dislike_count, platform_created_at,
                    first_seen_at, last_seen_at, content_hash, status, custom_attributes
                ) VALUES (
                    %s, %s, %s, %s, NULL,
                    %s, %s, %s, 1,
                    %s, now() + interval '30 days', 'en', 'GLOBAL',
                    %s, %s, 0, %s,
                    now(), now(), %s, 'ACTIVE', %s::jsonb
                )
                ON CONFLICT (tenant_id, platform, platform_comment_id)
                DO UPDATE SET
                    like_count = EXCLUDED.like_count,
                    reply_count = EXCLUDED.reply_count,
                    masked_text = EXCLUDED.masked_text,
                    platform_created_at = EXCLUDED.platform_created_at,
                    custom_attributes = EXCLUDED.custom_attributes,
                    last_seen_at = now()
                RETURNING id;
            """, (
                tenant_id, comment_uuid, platform, platform_comment_id,
                source_id, product_id, author_hash,
                masked_text, like_count, reply_count,
                platform_created_at, content_hash, custom_attrs_json
            ))
            row = cur.fetchone()
            actual_comment_id = str(row[0]) if row else comment_uuid

            # 2. Insert or update comment analysis
            cur.execute("""
                INSERT INTO comment_analysis (
                    tenant_id, comment_id, analyzed_at, model_version,
                    sentiment, sentiment_score, intent, topic_id,
                    toxic, churn_risk, impact_score, priority,
                    needs_review, suggested_reply
                ) VALUES (
                    %s, %s, now(), 'ollama/llama3.1',
                    %s, %s, %s, NULL,
                    %s, %s, %s, %s,
                    %s, %s
                )
                ON CONFLICT (tenant_id, comment_id)
                DO UPDATE SET
                    sentiment = EXCLUDED.sentiment,
                    sentiment_score = EXCLUDED.sentiment_score,
                    intent = EXCLUDED.intent,
                    churn_risk = EXCLUDED.churn_risk,
                    impact_score = EXCLUDED.impact_score,
                    priority = EXCLUDED.priority,
                    suggested_reply = EXCLUDED.suggested_reply,
                    needs_review = EXCLUDED.needs_review;
            """, (
                tenant_id, actual_comment_id,
                sentiment, sentiment_score, intent,
                toxic, churn_risk, impact_score, priority,
                True, suggested_reply
            ))

            # 3. Clean up and re-insert granular aspects
            cur.execute("""
                DELETE FROM comment_aspect
                WHERE tenant_id = %s AND comment_id = %s;
            """, (tenant_id, actual_comment_id))

            for asp in aspects:
                asp_name = asp.get("aspect") or asp.get("name") or "experience"
                asp_sent = (asp.get("sentiment") or sentiment).upper()
                asp_score = float(asp.get("score") or sentiment_score)
                asp_evidence = asp.get("evidence") or masked_text[:60]
                cur.execute("""
                    INSERT INTO comment_aspect (
                        tenant_id, comment_id, aspect, sentiment, score, evidence
                    ) VALUES (%s, %s, %s, %s, %s, %s);
                """, (tenant_id, actual_comment_id, asp_name, asp_sent, asp_score, asp_evidence))

            # 4. Insert cryptographic audit ledger entry
            row_hash = hashlib.sha256(f"{tenant_id}:{actual_comment_id}:{content_hash}".encode()).hexdigest()
            cur.execute("""
                INSERT INTO audit_event (
                    tenant_id, actor_id, actor_type, action, entity_type,
                    entity_id, before_state, after_state, prev_hash, row_hash
                ) VALUES (
                    %s, 'system-ai-pipeline', 'SYSTEM', 'INGEST_AND_ANALYZE', 'COMMENT',
                    %s, '{}'::jsonb, %s::jsonb,
                    '0000000000000000000000000000000000000000000000000000000000000000',
                    %s
                );
            """, (
                tenant_id, actual_comment_id,
                json.dumps({"sentiment": sentiment, "priority": priority, "content_hash": content_hash}),
                row_hash
            ))

        conn.commit()
        logger.info(f"Successfully persisted comment {actual_comment_id} ({platform}:{platform_comment_id}) into database.")
        return {
            "status": "SAVED",
            "comment_id": actual_comment_id,
            "platform_comment_id": platform_comment_id,
            "platform": platform,
            "priority": priority,
            "sentiment": sentiment
        }
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to persist comment into PostgreSQL: {e}", exc_info=True)
        raise e
    finally:
        conn.close()


def format_time_ago(dt):
    if not dt:
        return "Recent"
    try:
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        diff = now - dt
        seconds = max(0, int(diff.total_seconds()))
        if seconds < 60:
            return "Just now"
        elif seconds < 3600:
            return f"{seconds // 60}m ago"
        elif seconds < 86400:
            return f"{seconds // 3600}h ago"
        elif seconds < 2592000:
            return f"{seconds // 86400}d ago"
        else:
            months = seconds // 2592000
            return f"{months} month{'s' if months > 1 else ''} ago"
    except Exception:
        return "Recent"


def get_all_comments_from_db(tenant_id: str = DEFAULT_TENANT_ID, limit: int = 200) -> List[Dict[str, Any]]:
    """
    Retrieves stored comments, their sentiment analysis, granular aspects,
    and channel/video attribution from PostgreSQL.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT 
                    c.id,
                    c.platform,
                    c.platform_comment_id,
                    c.author_hash,
                    c.masked_text,
                    c.like_count AS likes,
                    c.reply_count AS replies,
                    c.first_seen_at,
                    c.platform_created_at,
                    c.custom_attributes,
                    ca.sentiment,
                    ca.sentiment_score,
                    ca.intent,
                    ca.toxic,
                    ca.churn_risk,
                    ca.impact_score,
                    ca.priority,
                    ca.needs_review,
                    ca.suggested_reply
                FROM comment c
                LEFT JOIN comment_analysis ca 
                    ON c.tenant_id = ca.tenant_id AND c.id = ca.comment_id
                WHERE c.tenant_id = %s
                ORDER BY c.first_seen_at DESC, c.platform_created_at DESC
                LIMIT %s;
            """, (tenant_id, limit))
            rows = cur.fetchall()

            # Retrieve aspects for each comment
            results = []
            for r in rows:
                c_id = str(r["id"])
                cur.execute("""
                    SELECT aspect AS name, sentiment, score, evidence
                    FROM comment_aspect
                    WHERE tenant_id = %s AND comment_id = %s;
                """, (tenant_id, c_id))
                aspects = cur.fetchall()

                attrs = r.get("custom_attributes") or {}
                channel_title = attrs.get("channel_title") or "YouTube"
                video_title = attrs.get("video_title") or ""
                video_id = attrs.get("video_id") or ""
                video_url = attrs.get("video_url") or (f"https://www.youtube.com/watch?v={video_id}" if video_id else "")
                time_ago = format_time_ago(r.get("platform_created_at"))

                results.append({
                    "id": c_id,
                    "platform": r["platform"].capitalize() if r["platform"] else "YouTube",
                    "platformCommentId": r["platform_comment_id"],
                    "authorHash": r["author_hash"],
                    "maskedText": r["masked_text"],
                    "hasPii": ("<PHONE>" in (r["masked_text"] or "") or "<EMAIL>" in (r["masked_text"] or "") or "<PERSON>" in (r["masked_text"] or "")),
                    "sentiment": r["sentiment"] or "NEUTRAL",
                    "sentimentScore": float(r["sentiment_score"]) if r["sentiment_score"] is not None else 0.0,
                    "aspects": [dict(a) for a in aspects] if aspects else [{"name": "overall", "sentiment": r["sentiment"] or "NEUTRAL"}],
                    "toxic": bool(r["toxic"]),
                    "churnRisk": float(r["churn_risk"]) if r["churn_risk"] is not None else 0.2,
                    "impactScore": float(r["impact_score"]) if r["impact_score"] is not None else 50.0,
                    "priority": r["priority"] or "P2",
                    "likes": r["likes"],
                    "replies": r["replies"],
                    "timeAgo": time_ago,
                    "channelTitle": channel_title,
                    "videoTitle": video_title,
                    "videoId": video_id,
                    "videoUrl": video_url,
                    "aiSuggestedReply": r["suggested_reply"] or "Thank you for your feedback!",
                    "status": "NEEDS_REVIEW" if r["needs_review"] else "RESOLVED"
                })

            return results
    except Exception as e:
        logger.error(f"Error querying comments from database: {e}", exc_info=True)
        return []
    finally:
        conn.close()


def save_source_watermark(tenant_id: str, source_id: str, platform: str, last_comment_ts: str, page_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Saves the newest comment watermark for incremental polling in table source_watermark.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO source_watermark (
                    id, tenant_id, source_id, platform, last_comment_ts, page_token, last_run_at, status
                ) VALUES (
                    gen_random_uuid(), %s, %s, %s, %s, %s, now(), 'ACTIVE'
                )
                ON CONFLICT (tenant_id, source_id, platform)
                DO UPDATE SET
                    last_comment_ts = EXCLUDED.last_comment_ts,
                    page_token = EXCLUDED.page_token,
                    last_run_at = now()
                RETURNING id, last_comment_ts;
            """, (tenant_id, source_id, platform.upper(), last_comment_ts, page_token))
            row = cur.fetchone()
            conn.commit()
            return {"status": "SUCCESS", "watermark_id": str(row[0]), "last_comment_ts": str(row[1])}
    except Exception as e:
        conn.rollback()
        logger.error(f"Failed to save source watermark: {e}")
        return {"status": "ERROR", "detail": str(e)}
    finally:
        conn.close()


def get_source_watermarks(tenant_id: str = DEFAULT_TENANT_ID) -> List[Dict[str, Any]]:
    """
    Retrieves all registered watermarks across platforms and channels.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT source_id, platform, last_comment_ts, page_token, last_run_at, status
                FROM source_watermark
                WHERE tenant_id = %s;
            """, (tenant_id,))
            return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        logger.error(f"Error fetching watermarks: {e}")
        return []
    finally:
        conn.close()

