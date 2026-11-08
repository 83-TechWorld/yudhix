"""Background schedule: checks every analyzed video for new comments.

Each workspace picks an interval (default every 6 hours) or turns it off. Every few minutes the
scheduler finds videos whose last check is older than their workspace's interval and runs a
"fetch new comments" job for each, one at a time, so the AI model is never flooded.

Safe with several API replicas: a Postgres advisory lock lets only one of them run a round.
"""
import logging
import threading
from typing import Dict, List, Optional

from app.core import config
from app.core.database import cursor, fetch_all, fetch_one
from app.db import get_db_connection
from app.truth import pipeline, youtube

logger = logging.getLogger(__name__)
SCHEDULER_LOCK = 724_002   # pg advisory lock key (724_001 is the migration lock)
BATCH = 20                 # most videos checked in one round
ACTOR = "system-scheduler"
INTERVALS = (1, 3, 6, 12, 24, 48, 168)  # hours offered in settings

_started = False


def start() -> None:
    """Start the background thread once per process (no-op when disabled)."""
    global _started
    if _started or not config.SCHEDULER_ENABLED:
        return
    _started = True
    stop = threading.Event()
    threading.Thread(target=_loop, args=(stop,), name="comment-scheduler", daemon=True).start()
    logger.info("Comment scheduler started: looking for due videos every %ss", config.SCHEDULER_TICK_SECONDS)


def _loop(stop: threading.Event) -> None:
    stop.wait(30)  # let startup (migrations) finish
    while not stop.is_set():
        try:
            run_round()
        except Exception:
            logger.exception("Comment scheduler round failed")
        stop.wait(config.SCHEDULER_TICK_SECONDS)


def run_round() -> int:
    """Check every due video once. Returns how many were checked (0 if another replica holds the lock)."""
    if not youtube.has_api_key():
        return 0
    conn = get_db_connection()
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT pg_try_advisory_lock(%s)", (SCHEDULER_LOCK,))
            if not cur.fetchone()[0]:
                return 0
            try:
                checked = 0
                for v in due_videos():
                    job = pipeline.start_comment_check(v["tenant_id"], v["video_id"], ACTOR, trigger="SCHEDULE")
                    if job["kind"] == "COMMENTS" and job["status"] == "QUEUED":
                        pipeline.run_job(job["id"], v["tenant_id"])
                        checked += 1
                if checked:
                    logger.info("Comment scheduler checked %s videos", checked)
                return checked
            finally:
                cur.execute("SELECT pg_advisory_unlock(%s)", (SCHEDULER_LOCK,))
    finally:
        conn.close()


def due_videos(limit: int = BATCH) -> List[Dict]:
    return [{"tenant_id": str(r["tenant_id"]), "video_id": r["video_id"]} for r in fetch_all(
        """SELECT v.tenant_id, v.video_id
           FROM video_truth_analysis v
           JOIN tenant t ON t.id = v.tenant_id AND t.status = 'ACTIVE'
           LEFT JOIN comment_watch w ON w.tenant_id = v.tenant_id
           WHERE COALESCE(w.enabled, true)
             AND COALESCE(v.comments_checked_at, v.analyzed_at, v.created_at)
                 < now() - make_interval(hours => COALESCE(w.interval_hours, %s))
           ORDER BY COALESCE(v.comments_checked_at, v.analyzed_at, v.created_at)
           LIMIT %s""", (config.SCHEDULER_DEFAULT_HOURS, limit))]


# ----------------------------------------------------------------------------- workspace setting

def get_setting(tenant_id: str) -> Dict:
    row = fetch_one("SELECT * FROM comment_watch WHERE tenant_id = %s", (tenant_id,)) or {}
    last = fetch_one(
        """SELECT max(finished_at) AS at FROM video_analysis_job
           WHERE tenant_id = %s AND kind = 'COMMENTS' AND trigger = 'SCHEDULE' AND status = 'COMPLETED'""",
        (tenant_id,))
    hours = row.get("interval_hours") or config.SCHEDULER_DEFAULT_HOURS
    return {
        "enabled": row.get("enabled", True) and config.SCHEDULER_ENABLED,
        "intervalHours": hours,
        "intervals": list(INTERVALS),
        "serverEnabled": config.SCHEDULER_ENABLED,
        "youtubeConnected": youtube.has_api_key(),
        "lastRunAt": last["at"].isoformat() if last and last.get("at") else None,
    }


def save_setting(tenant_id: str, actor: str, enabled: Optional[bool], interval_hours: Optional[int]) -> Dict:
    if interval_hours is not None and interval_hours not in INTERVALS:
        raise ValueError(f"Pick one of: {', '.join(str(h) for h in INTERVALS)} hours.")
    with cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO comment_watch (tenant_id, enabled, interval_hours, updated_by)
               VALUES (%s, COALESCE(%s, true), COALESCE(%s, %s), %s)
               ON CONFLICT (tenant_id) DO UPDATE SET
                   enabled = COALESCE(%s, comment_watch.enabled),
                   interval_hours = COALESCE(%s, comment_watch.interval_hours),
                   updated_by = EXCLUDED.updated_by, updated_at = now()""",
            (tenant_id, enabled, interval_hours, config.SCHEDULER_DEFAULT_HOURS, actor, enabled, interval_hours))
    return get_setting(tenant_id)
