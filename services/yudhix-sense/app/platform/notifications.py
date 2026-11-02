"""In-app notifications. One row per recipient, so read state is per person."""
import logging
from typing import Dict, Iterable, List, Optional

from app.core.database import cursor, fetch_all, fetch_one

logger = logging.getLogger(__name__)


def notify(tenant_id: str, kind: str, title: str, body: str = "", link: Optional[str] = None,
           user_ids: Optional[Iterable[str]] = None, roles: Optional[Iterable[str]] = None,
           exclude: Optional[str] = None) -> int:
    """Send to explicit users and/or every active member holding one of `roles`.
    Never raises: a failed notification must not fail the action that caused it."""
    try:
        recipients = set(user_ids or [])
        if roles:
            rows = fetch_all("""SELECT keycloak_user_id FROM tenant_user
                                WHERE tenant_id = %s AND active AND roles && %s::text[]""", (tenant_id, list(roles)))
            recipients.update(r["keycloak_user_id"] for r in rows)
        recipients.discard(exclude)
        recipients.discard(None)
        if not recipients:
            return 0
        with cursor(commit=True) as cur:
            for uid in recipients:
                cur.execute("""INSERT INTO app_notification (tenant_id, user_id, kind, title, body, link)
                               VALUES (%s, %s, %s, %s, %s, %s)""", (tenant_id, uid, kind, title[:200], body, link))
        return len(recipients)
    except Exception:
        logger.exception("Notification %s for tenant %s failed", kind, tenant_id)
        return 0


def _row(r: Dict) -> Dict:
    return {"id": r["id"], "kind": r["kind"], "title": r["title"], "body": r["body"], "link": r["link"],
            "read": r["read_at"] is not None, "createdAt": r["created_at"].isoformat()}


def list_for(tenant_id: str, user_id: str, limit: int = 30) -> Dict:
    rows = fetch_all("""SELECT * FROM app_notification WHERE tenant_id = %s AND user_id = %s
                        ORDER BY created_at DESC LIMIT %s""", (tenant_id, user_id, limit))
    unread = fetch_one("""SELECT count(*) AS n FROM app_notification
                          WHERE tenant_id = %s AND user_id = %s AND read_at IS NULL""", (tenant_id, user_id))["n"]
    return {"items": [_row(r) for r in rows], "unread": int(unread)}


def mark_read(tenant_id: str, user_id: str, ids: Optional[List[int]] = None) -> None:
    with cursor(commit=True) as cur:
        if ids:
            cur.execute("""UPDATE app_notification SET read_at = now()
                           WHERE tenant_id = %s AND user_id = %s AND id = ANY(%s) AND read_at IS NULL""",
                        (tenant_id, user_id, ids))
        else:
            cur.execute("""UPDATE app_notification SET read_at = now()
                           WHERE tenant_id = %s AND user_id = %s AND read_at IS NULL""", (tenant_id, user_id))
