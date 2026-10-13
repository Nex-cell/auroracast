"""Database access helpers for the TimescaleDB feature store."""

from pathlib import Path

import psycopg

from auroracast.config import db_conninfo

SQL_DIR = Path(__file__).resolve().parent / "sql"


def connect() -> psycopg.Connection:
    return psycopg.connect(db_conninfo())


def ensure_schema(conn: psycopg.Connection) -> None:
    """Apply every schema file in sql/ in name order. Files must be idempotent (IF NOT EXISTS)."""
    for path in sorted(SQL_DIR.glob("*.sql")):
        conn.execute(path.read_text())
    conn.commit()
