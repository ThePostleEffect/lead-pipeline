"""SQLite-backed run storage — persists runs across server restarts.

Each run holds metadata, kept leads, discards, and source logs.
Leads/discards/source_logs stored as JSON text columns.
Per-thread connections via threading.local() for safe use with ThreadPoolExecutor.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from api.models import RunResponse

_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "pipeline.db"
_local = threading.local()
_db_initialized = False

_META_COLUMNS = {
    "status", "completed_at", "raw_signal_count", "kept_count",
    "discard_count", "output_json_path", "discard_json_path",
    "xlsx_path", "error",
}
_JSON_COLUMNS = {"leads", "discards", "source_logs"}

_META_SELECT = (
    "run_id, lane, status, created_at, completed_at, "
    "raw_signal_count, kept_count, discard_count, "
    "output_json_path, discard_json_path, xlsx_path, error"
)


def _get_conn() -> sqlite3.Connection:
    """Return a per-thread SQLite connection, creating it if needed."""
    global _db_initialized
    conn = getattr(_local, "conn", None)
    if conn is None:
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(_DB_PATH), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        _local.conn = conn
    if not _db_initialized:
        _init_db(conn)
        _db_initialized = True
    return conn


def _init_db(conn: sqlite3.Connection) -> None:
    """Create tables if they don't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS runs (
            run_id            TEXT PRIMARY KEY,
            lane              TEXT NOT NULL,
            status            TEXT NOT NULL DEFAULT 'pending',
            created_at        TEXT NOT NULL,
            completed_at      TEXT,
            raw_signal_count  INTEGER,
            kept_count        INTEGER,
            discard_count     INTEGER,
            output_json_path  TEXT,
            discard_json_path TEXT,
            xlsx_path         TEXT,
            error             TEXT,
            leads             TEXT NOT NULL DEFAULT '[]',
            discards          TEXT NOT NULL DEFAULT '[]',
            source_logs       TEXT NOT NULL DEFAULT '[]'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS schedules (
            schedule_id    TEXT PRIMARY KEY,
            name           TEXT NOT NULL,
            lane           TEXT NOT NULL,
            interval_hours INTEGER NOT NULL DEFAULT 24,
            params         TEXT NOT NULL DEFAULT '{}',
            enabled        INTEGER NOT NULL DEFAULT 1,
            last_run_at    TEXT,
            next_run_at    TEXT NOT NULL,
            created_at     TEXT NOT NULL
        )
    """)
    conn.commit()


def _row_to_run_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert a full DB row into the dict shape callers expect."""
    meta = RunResponse(
        run_id=row["run_id"],
        lane=row["lane"],
        status=row["status"],
        created_at=row["created_at"],
        completed_at=row["completed_at"],
        raw_signal_count=row["raw_signal_count"],
        kept_count=row["kept_count"],
        discard_count=row["discard_count"],
        output_json_path=row["output_json_path"],
        discard_json_path=row["discard_json_path"],
        xlsx_path=row["xlsx_path"],
        error=row["error"],
    )
    return {
        "meta": meta,
        "leads": json.loads(row["leads"]),
        "discards": json.loads(row["discards"]),
        "source_logs": json.loads(row["source_logs"]),
    }


def create_run(lane: str) -> str:
    """Create a new run entry with status 'pending'. Returns run_id."""
    run_id = f"RUN-{uuid4().hex[:10].upper()}"
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    conn.execute(
        "INSERT INTO runs (run_id, lane, status, created_at) VALUES (?, ?, ?, ?)",
        (run_id, lane, "pending", now),
    )
    conn.commit()
    return run_id


def get_run(run_id: str) -> dict[str, Any] | None:
    """Get a run's full data (meta + leads + discards + source_logs)."""
    conn = _get_conn()
    row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    if row is None:
        return None
    return _row_to_run_dict(row)


def get_run_meta(run_id: str) -> RunResponse | None:
    """Get only the run metadata (skips large JSON blob columns)."""
    conn = _get_conn()
    row = conn.execute(
        f"SELECT {_META_SELECT} FROM runs WHERE run_id = ?",
        (run_id,),
    ).fetchone()
    if row is None:
        return None
    return RunResponse(**dict(row))


def update_run(run_id: str, **kwargs: Any) -> None:
    """Update run metadata and/or data fields.

    Keyword args matching RunResponse fields update metadata columns.
    Special keys 'leads', 'discards', 'source_logs' are JSON-serialized.
    """
    if not kwargs:
        return

    sets: list[str] = []
    values: list[Any] = []

    for key, value in kwargs.items():
        if key in _JSON_COLUMNS:
            sets.append(f"{key} = ?")
            values.append(json.dumps(value, default=str))
        elif key in _META_COLUMNS:
            sets.append(f"{key} = ?")
            values.append(value)

    if not sets:
        return

    values.append(run_id)
    conn = _get_conn()
    conn.execute(f"UPDATE runs SET {', '.join(sets)} WHERE run_id = ?", values)
    conn.commit()


def list_runs() -> list[RunResponse]:
    """Return metadata for all runs, newest first."""
    conn = _get_conn()
    rows = conn.execute(
        f"SELECT {_META_SELECT} FROM runs ORDER BY created_at DESC"
    ).fetchall()
    return [RunResponse(**dict(row)) for row in rows]
