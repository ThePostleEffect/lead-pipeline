"""Runs endpoints — trigger pipeline runs and retrieve results."""

from __future__ import annotations

import shutil
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from api.models import CollectRequest, RunListItem, RunResponse
from api.run_store import create_run, get_run, get_run_meta, list_runs
from api.tasks import submit_collect
from app.config import DATA_INPUT

router = APIRouter()


@router.post("/collect", status_code=202, response_model=RunResponse)
async def start_collect(
    lane: str = Form(...),
    limit: Optional[int] = Form(None),
    min_quality: Optional[str] = Form(None),
    source_type: Optional[str] = Form(None),
    save_discards: bool = Form(True),
    export_xlsx: bool = Form(False),
    chapters: Optional[str] = Form(None),
    lookback_days: Optional[int] = Form(None),
    include_individuals: Optional[bool] = Form(None),
    company_types: Optional[str] = Form(None),
    source_file: Optional[UploadFile] = File(None),
) -> RunResponse:
    """Start a pipeline collect run. Returns immediately with run_id."""
    request = CollectRequest(
        lane=lane,
        limit=limit,
        min_quality=min_quality,
        source_type=source_type,
        save_discards=save_discards,
        export_xlsx=export_xlsx,
        chapters=chapters,
        lookback_days=lookback_days,
        include_individuals=include_individuals,
        company_types=company_types,
    )

    run_id = create_run(lane=request.lane)

    # Handle uploaded source file
    upload_path: Path | None = None
    if source_file and source_file.filename:
        ext = Path(source_file.filename).suffix or ".json"
        upload_path = DATA_INPUT / f"upload_{run_id}{ext}"
        upload_path.parent.mkdir(parents=True, exist_ok=True)
        with open(upload_path, "wb") as f:
            shutil.copyfileobj(source_file.file, f)

    submit_collect(run_id, request, upload_path)

    meta = get_run_meta(run_id)
    return meta


@router.get("", response_model=list[RunListItem])
def get_all_runs() -> list[RunListItem]:
    """List all runs (metadata only), newest first."""
    metas = list_runs()
    return [
        RunListItem(
            run_id=m.run_id,
            lane=m.lane,
            status=m.status,
            created_at=m.created_at,
            completed_at=m.completed_at,
            kept_count=m.kept_count,
            discard_count=m.discard_count,
        )
        for m in metas
    ]


@router.get("/{run_id}", response_model=RunResponse)
def get_run_status(run_id: str) -> RunResponse:
    """Get run metadata / status."""
    meta = get_run_meta(run_id)
    if meta is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return meta


@router.get("/{run_id}/leads")
def get_run_leads(run_id: str) -> list[dict]:
    """Get kept leads from a completed run."""
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    if run["meta"].status == "running":
        raise HTTPException(status_code=409, detail="Run still in progress")
    if run["meta"].status == "failed":
        raise HTTPException(status_code=400, detail=f"Run failed: {run['meta'].error}")
    return run["leads"]


@router.get("/{run_id}/discards")
def get_run_discards(run_id: str) -> list[dict]:
    """Get discarded leads from a completed run."""
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    if run["meta"].status == "running":
        raise HTTPException(status_code=409, detail="Run still in progress")
    return run["discards"]


@router.get("/{run_id}/source-logs")
def get_run_source_logs(run_id: str) -> list[dict]:
    """Get source logs from a completed run."""
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return run["source_logs"]
