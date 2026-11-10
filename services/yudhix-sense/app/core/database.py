"""Connection helpers, startup migration and the hash-chained audit ledger."""
import hashlib
import json
import logging
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from psycopg2.extras import RealDictCursor

from app.db import get_db_connection

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "migrations"
GENESIS_HASH = "0" * 64


@contextmanager
def cursor(commit: bool = False) -> Iterator[RealDictCursor]:
    """Yield a dict cursor. Commits on success when commit=True, always rolls back on error."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
        if commit:
            conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def fetch_all(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    with cursor() as cur:
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def fetch_one(sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    with cursor() as cur:
        cur.execute(sql, params)
        row = cur.fetchone()
        return dict(row) if row else None


# Base schema owned by the Java services (their Flyway V1 files). The container image copies them
# into app/migrations/base/ so a brand-new database (Docker, Kubernetes, managed Postgres on Zoho)
# can be bootstrapped by this service alone. Order matters: later files reference earlier tables.
BASE_ORDER = ["tenant", "ledger", "dharma", "catalog", "radar", "link", "pulse", "resolve", "loop", "notify", "meter"]
MIGRATION_LOCK = 724_001  # pg_advisory_lock key: only one replica migrates at a time


def run_migrations() -> None:
    """Bootstrap the base schema on an empty database, then apply app/migrations/V*.sql (idempotent).
    Safe with many replicas starting at once: everything runs under one advisory lock."""
    from app.db import get_db_connection as connect
    conn = connect()
    try:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_lock(%s)", (MIGRATION_LOCK,))
            try:
                _bootstrap_base_schema(cur)
                for path in sorted(MIGRATIONS_DIR.glob("V*.sql")):
                    cur.execute("BEGIN")
                    try:
                        cur.execute(path.read_text())
                        cur.execute("COMMIT")
                    except Exception:
                        cur.execute("ROLLBACK")
                        raise
                    logger.info("Applied migration %s", path.name)
            finally:
                cur.execute("SELECT pg_advisory_unlock(%s)", (MIGRATION_LOCK,))
    finally:
        conn.close()


def _bootstrap_base_schema(cur) -> None:
    cur.execute("SELECT to_regclass('public.tenant') IS NOT NULL AS ready")
    if cur.fetchone()[0]:
        return
    base_dir = MIGRATIONS_DIR / "base"
    files = [base_dir / f"V1__init_{name}_schema.sql" for name in BASE_ORDER]
    missing = [f.name for f in files if not f.exists()]
    if missing:
        raise RuntimeError(f"Empty database and base schema files are missing: {missing}. "
                           f"Build the image from the repository root (see deploy/README.md).")
    logger.info("Empty database: creating the base schema (%d files)", len(files))
    cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; CREATE EXTENSION IF NOT EXISTS "pgcrypto";')
    for f in files:
        cur.execute(f.read_text())
        logger.info("Base schema: %s", f.name)


def append_audit(cur, tenant_id: str, actor_id: str, actor_type: str, action: str,
                 entity_type: str, entity_id: str, after_state: Dict[str, Any],
                 before_state: Optional[Dict[str, Any]] = None) -> str:
    """Append an audit event linked to the tenant's previous event.

    row_hash = SHA-256(prev_hash || tenant_id || action || entity_id || payload)
    Uses an advisory lock per tenant so concurrent writers cannot fork the chain.
    """
    cur.execute("SELECT pg_advisory_xact_lock(hashtext(%s))", (f"audit:{tenant_id}",))
    cur.execute(
        "SELECT row_hash FROM audit_event WHERE tenant_id = %s ORDER BY id DESC LIMIT 1",
        (tenant_id,),
    )
    row = cur.fetchone()
    prev_hash = (row["row_hash"] if isinstance(row, dict) else row[0]) if row else GENESIS_HASH
    payload = json.dumps(after_state, sort_keys=True, default=str)
    row_hash = hashlib.sha256(f"{prev_hash}|{tenant_id}|{action}|{entity_id}|{payload}".encode()).hexdigest()
    cur.execute(
        """INSERT INTO audit_event (tenant_id, actor_id, actor_type, action, entity_type, entity_id,
                                    before_state, after_state, prev_hash, row_hash)
           VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s, %s)""",
        (tenant_id, actor_id, actor_type, action, entity_type, str(entity_id),
         json.dumps(before_state or {}, default=str), payload, prev_hash, row_hash),
    )
    return row_hash
