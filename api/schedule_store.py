"""SQLite-backed schedule storage — CRUD for recurring run schedules.

Shares the same database and connection pool as run_store.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from api.run_store import _get_conn


def _row_to_dict(row) -> dict[str, Any]:
    """Convert a sqlite3.Row to a plain dict with proper types."""
    return {
        "schedule_id": row["schedule_id"],
        "name": row["name"],
        "lane": row["lane"],
        "interval_hours": row["interval_hours"],
        "params": json.loads(row["params"]),
        "enabled": bool(row["enabled"]),
        "last_run_at": row["last_run_at"],
        "next_run_at": row["next_run_at"],
        "created_at": row["created_at"],
    }


def create_schedule(
    name: str,
    lane: str,
    interval_hours: int = 24,
    params: dict | None = None,
) -> dict[str, Any]:
    """Create a new schedule. Returns the full schedule dict."""
    schedule_id = f"SCHED-{uuid4().hex[:8].upper()}"
    now = datetime.now(timezone.utc)
    next_run = now + timedelta(hours=interval_hours)

    conn = _get_conn()
    conn.execute(
        """INSERT INTO schedules
           (schedule_id, name, lane, interval_hours, params, enabled, next_run_at, created_at)
           VALUES (?, ?, ?, ?, ?, 1, ?, ?)""",
        (
            schedule_id,
            name,
            lane,
            interval_hours,
            json.dumps(params or {}),
            next_run.isoformat(),
            now.isoformat(),
        ),
    )
    conn.commit()
    return get_schedule(schedule_id)  # type: ignore[return-value]


def get_schedule(schedule_id: str) -> dict[str, Any] | None:
    """Get a single schedule by ID."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT * FROM schedules WHERE schedule_id = ?", (schedule_id,)
    ).fetchone()
    return _row_to_dict(row) if row else None


def list_schedules() -> list[dict[str, Any]]:
    """Return all schedules, newest first."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM schedules ORDER BY created_at DESC"
    ).fetchall()
    return [_row_to_dict(r) for r in rows]


def update_schedule(schedule_id: str, **kwargs: Any) -> dict[str, Any] | None:
    """Update schedule fields. Returns updated schedule or None if not found."""
    allowed = {"name", "lane", "interval_hours", "params", "enabled", "next_run_at"}
    sets: list[str] = []
    values: list[Any] = []

    for key, value in kwargs.items():
        if key not in allowed:
            continue
        if key == "params":
            sets.append("params = ?")
            values.append(json.dumps(value))
        elif key == "enabled":
            sets.append("enabled = ?")
            values.append(1 if value else 0)
        else:
            sets.append(f"{key} = ?")
            values.append(value)

    if not sets:
        return get_schedule(schedule_id)

    values.append(schedule_id)
    conn = _get_conn()
    conn.execute(
        f"UPDATE schedules SET {', '.join(sets)} WHERE schedule_id = ?", values
    )
    conn.commit()
    return get_schedule(schedule_id)


def delete_schedule(schedule_id: str) -> bool:
    """Delete a schedule. Returns True if it existed."""
    conn = _get_conn()
    cursor = conn.execute(
        "DELETE FROM schedules WHERE schedule_id = ?", (schedule_id,)
    )
    conn.commit()
    return cursor.rowcount > 0


def mark_schedule_ran(schedule_id: str) -> None:
    """Update last_run_at and advance next_run_at after a scheduled run fires."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT interval_hours FROM schedules WHERE schedule_id = ?",
        (schedule_id,),
    ).fetchone()
    if not row:
        return

    now = datetime.now(timezone.utc)
    next_run = now + timedelta(hours=row["interval_hours"])

    conn.execute(
        "UPDATE schedules SET last_run_at = ?, next_run_at = ? WHERE schedule_id = ?",
        (now.isoformat(), next_run.isoformat(), schedule_id),
    )
    conn.commit()


def get_due_schedules() -> list[dict[str, Any]]:
    """Return all enabled schedules whose next_run_at is in the past."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _get_conn()
    rows = conn.execute(
        "SELECT * FROM schedules WHERE enabled = 1 AND next_run_at <= ?",
        (now,),
    ).fetchall()
    return [_row_to_dict(r) for r in rows]
