"""Reset the demo workspace so every recording starts the same (development database only).

    ../../services/yudhix-sense/.venv/bin/python prepare_demo.py

Removes the sample document from an earlier recording and clears "checked against older facts" flags.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "services" / "yudhix-sense"))

from app.core.database import cursor  # noqa: E402

DEMO_TENANT = "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"  # PlayStation (Demo)

with cursor(commit=True) as cur:
    cur.execute("DELETE FROM knowledge_document WHERE tenant_id = %s AND filename LIKE %s RETURNING filename",
                (DEMO_TENANT, "%(demo)%"))
    removed = [r["filename"] for r in cur.fetchall()]
    cur.execute("UPDATE video_truth_analysis SET facts_stale = false WHERE tenant_id = %s", (DEMO_TENANT,))
print("Demo workspace ready." + (f" Removed: {', '.join(removed)}" if removed else ""))

# Approvals scene: make sure a couple of replies are waiting for review (drafted against misinformation comments).
from app.core.database import fetch_all  # noqa: E402
from app.workflow import service  # noqa: E402
from app.workflow.state import Actor  # noqa: E402

ADMIN = Actor("314c7634-074a-45e1-b55e-1e1c27c8a762", "admin")
REPLY = ("Thanks for raising this. To clarify: after a one-time online pairing, the detachable disc drive plays discs "
         "offline, with no constant connection needed. Source: PS5 Disc Drive Offline Policy.")
waiting = fetch_all("SELECT id FROM reply WHERE tenant_id = %s AND status IN ('IN_REVIEW', 'PENDING_APPROVAL', 'SUBMITTED')",
                    (DEMO_TENANT,))
if len(waiting) < 2:
    comments = fetch_all(
        """SELECT c.id FROM comment c
           JOIN comment_claim_link l ON l.tenant_id = c.tenant_id AND l.comment_id = c.id
           JOIN video_claim vc ON vc.id = l.claim_id
           WHERE c.tenant_id = %s AND c.status = 'ACTIVE' AND vc.verdict IN ('MISLEADING', 'FALSE')
             AND NOT EXISTS (SELECT 1 FROM reply r WHERE r.comment_id = c.id)
           ORDER BY c.like_count DESC LIMIT %s""", (DEMO_TENANT, 2 - len(waiting)))
    for c in comments:
        try:
            r = service.create_reply(DEMO_TENANT, ADMIN, str(c["id"]), REPLY)
            service.transition(DEMO_TENANT, ADMIN, r["id"], "submit")
            print("Reply waiting for approval:", r["id"])
        except Exception as e:
            print("Couldn't prepare a reply:", e)
