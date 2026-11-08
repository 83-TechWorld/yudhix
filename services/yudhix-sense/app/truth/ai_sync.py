"""Sync a workspace's knowledge base with its AI connection.

The knowledge base (facts and uploaded documents) always lives in this database; it is the source
of truth and what the quote check compares against. "Syncing" builds the AI's view of it: one
vector per fact from the workspace's embedding model, kept in knowledge_embedding under that
model's name. So:
  - every workspace has its own index per AI connection, and reconnecting the same provider and
    model reuses it: only facts added or changed since are sent;
  - facts uploaded while AI was off are "pending" and are synced the next time AI is on;
  - switching provider builds a second index and keeps the first, so switching back is instant;
  - deleting a fact or document deletes its vectors.
Providers without an embeddings API (Claude, Groq, DeepSeek) use the local embedding model for this.
"""
import hashlib
import logging
from typing import Dict, Optional

from app.core import llm
from app.core.database import cursor, fetch_all, fetch_one
from app.truth.retrieval import KnowledgeIndex, _doc_text

logger = logging.getLogger(__name__)


def status(tenant_id: str) -> Dict:
    with llm.use_tenant(tenant_id):
        model = llm.embedder_name()
        engine = llm.describe()
    facts = fetch_all("SELECT * FROM product_knowledge WHERE tenant_id = %s", (tenant_id,))
    hashes = {str(f["id"]): hashlib.sha256(_doc_text(f).encode()).hexdigest() for f in facts}
    indexes = []
    for r in fetch_all("""SELECT model, count(*) AS n, max(created_at) AS at FROM knowledge_embedding
                          WHERE tenant_id = %s GROUP BY model ORDER BY max(created_at) DESC""", (tenant_id,)):
        indexes.append({"model": r["model"], "facts": int(r["n"]), "updatedAt": r["at"].isoformat() if r["at"] else None,
                        "current": r["model"] == model})
    synced = 0
    if model:
        synced = sum(1 for r in fetch_all(
            "SELECT knowledge_id, content_hash FROM knowledge_embedding WHERE tenant_id = %s AND model = %s",
            (tenant_id, model)) if hashes.get(str(r["knowledge_id"])) == r["content_hash"])
    last = fetch_one("SELECT * FROM ai_sync_run WHERE tenant_id = %s ORDER BY started_at DESC LIMIT 1", (tenant_id,))
    return {
        "engine": engine,
        "model": model,
        "canSync": bool(model),
        "reason": None if model else _why_not(engine),
        "total": len(facts),
        "synced": synced,
        "pending": len(facts) - synced if model else len(facts),
        "indexes": indexes,
        "running": bool(last and last["status"] == "RUNNING"),
        "lastRun": _run(last) if last else None,
    }


def _why_not(engine: Dict) -> str:
    if engine["mode"] == "CLOUD":
        return (f"{engine['label']} has no embeddings API. Install the local embedding model "
                "(ollama pull nomic-embed-text) and the knowledge base syncs with it; claims are still checked by "
                f"{engine['label']}.")
    if engine["mode"] == "LOCAL":
        return "The local embedding model isn't installed. Run: ollama pull nomic-embed-text"
    return "No AI is connected. Facts are searched by keywords until you connect one in Settings > AI."


def _run(r: Dict) -> Dict:
    return {"id": r["id"], "model": r["model"], "trigger": r["trigger"], "status": r["status"], "total": r["total"],
            "embedded": r["embedded"], "error": r["error"],
            "startedAt": r["started_at"].isoformat() if r.get("started_at") else None,
            "finishedAt": r["finished_at"].isoformat() if r.get("finished_at") else None}


def run(tenant_id: str, actor: Optional[str], trigger: str) -> Dict:
    """Embed every fact that isn't synced with the current AI connection yet. Safe to call any time."""
    before = status(tenant_id)
    if not before["canSync"] or before["running"] and _recent_running(tenant_id):
        return before
    with cursor(commit=True) as cur:
        cur.execute("""INSERT INTO ai_sync_run (tenant_id, model, trigger, total, started_by)
                       VALUES (%s, %s, %s, %s, %s) RETURNING id""",
                    (tenant_id, before["model"], trigger, before["total"], actor))
        run_id = cur.fetchone()["id"]
    error = None
    try:
        with llm.use_tenant(tenant_id):
            if before["pending"]:
                KnowledgeIndex.build(tenant_id, fetch_all("SELECT * FROM product_knowledge WHERE tenant_id = %s",
                                                          (tenant_id,)))
    except Exception as e:
        logger.exception("AI sync failed for %s", tenant_id)
        error = f"{type(e).__name__}: {e}"
    after = status(tenant_id)
    embedded = max(0, before["pending"] - after["pending"])
    if after["pending"] and not error:
        error = f"{after['pending']} facts couldn't be synced (the embedding model didn't answer). Try again."
    with cursor(commit=True) as cur:
        cur.execute("""UPDATE ai_sync_run SET status = %s, embedded = %s, error = %s, finished_at = now()
                       WHERE id = %s""", ("FAILED" if error else "DONE", embedded, error, run_id))
        if embedded:  # fact search changed: claims checked before can now be re-checked
            cur.execute("UPDATE video_truth_analysis SET facts_stale = true WHERE tenant_id = %s", (tenant_id,))
    return status(tenant_id)


def _recent_running(tenant_id: str) -> bool:
    return bool(fetch_one("""SELECT 1 FROM ai_sync_run WHERE tenant_id = %s AND status = 'RUNNING'
                             AND started_at > now() - interval '15 minutes'""", (tenant_id,)))
