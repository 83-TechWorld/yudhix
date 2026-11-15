"""Read-only database access. The report service never writes: every session is read-only."""
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

import psycopg2
from psycopg2.extras import RealDictCursor

from app import config


def connect():
    return psycopg2.connect(
        dbname=config.PG_DB, user=config.PG_USER, password=config.PG_PASSWORD,
        host=config.PG_HOST, port=config.PG_PORT, connect_timeout=5,
        options="-c default_transaction_read_only=on -c statement_timeout=20000",
        application_name="yudhix-report",
    )


@contextmanager
def cursor() -> Iterator[RealDictCursor]:
    conn = connect()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            yield cur
    finally:
        conn.rollback()
        conn.close()


def fetch_all(sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    with cursor() as cur:
        cur.execute(sql, params)
        return [dict(r) for r in cur.fetchall()]


def fetch_one(sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
    rows = fetch_all(sql, params)
    return rows[0] if rows else None
