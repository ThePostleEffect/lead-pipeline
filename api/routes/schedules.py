"""Schedule endpoints — CRUD for recurring pipeline runs."""

from __future__ import annotations

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api.schedule_store import (
    create_schedule,
    delete_schedule,
    get_schedule,
    list_schedules,
    update_schedule,
)

router = APIRouter()


# ── Request schemas ────────────────────────────────────────────────────

class CreateScheduleRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    lane: Literal["charged_off", "bankruptcy", "performing", "capital_seeking"]
    interval_hours: int = Field(24, ge=1, le=8760)  # 1 hour to 1 year
    params: dict = Field(default_factory=dict)


class UpdateScheduleRequest(BaseModel):
    name: Optional[str] = None
    lane: Optional[Literal["charged_off", "bankruptcy", "performing", "capital_seeking"]] = None
    interval_hours: Optional[int] = Field(None, ge=1, le=8760)
    params: Optional[dict] = None
    enabled: Optional[bool] = None


# ── Endpoints ──────────────────────────────────────────────────────────

@router.get("")
def get_all_schedules() -> list[dict]:
    """List all schedules."""
    return list_schedules()


@router.post("", status_code=201)
def create_new_schedule(body: CreateScheduleRequest) -> dict:
    """Create a new recurring schedule."""
    return create_schedule(
        name=body.name,
        lane=body.lane,
        interval_hours=body.interval_hours,
        params=body.params,
    )


@router.get("/{schedule_id}")
def get_single_schedule(schedule_id: str) -> dict:
    """Get a single schedule by ID."""
    sched = get_schedule(schedule_id)
    if sched is None:
        raise HTTPException(status_code=404, detail=f"Schedule not found: {schedule_id}")
    return sched


@router.patch("/{schedule_id}")
def update_existing_schedule(schedule_id: str, body: UpdateScheduleRequest) -> dict:
    """Update a schedule (toggle enabled, change interval, etc.)."""
    updates = body.model_dump(exclude_none=True)
    if not updates:
        sched = get_schedule(schedule_id)
        if sched is None:
            raise HTTPException(status_code=404, detail=f"Schedule not found: {schedule_id}")
        return sched

    result = update_schedule(schedule_id, **updates)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Schedule not found: {schedule_id}")
    return result


@router.delete("/{schedule_id}", status_code=204)
def delete_existing_schedule(schedule_id: str) -> None:
    """Delete a schedule."""
    existed = delete_schedule(schedule_id)
    if not existed:
        raise HTTPException(status_code=404, detail=f"Schedule not found: {schedule_id}")
