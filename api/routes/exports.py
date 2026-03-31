"""Export endpoints — generate downloadable Excel/JSON files."""

from __future__ import annotations

import json
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from api.models import ExportRequest
from api.run_store import get_run
from app.config import DATA_OUTPUT
from app.exporter import export_workbook
from app.models import Lead, SourceLog

router = APIRouter()


@router.post("/xlsx")
def export_xlsx(request: ExportRequest) -> StreamingResponse:
    """Generate an Excel workbook from a completed run and return as download."""
    run = get_run(request.run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {request.run_id}")
    if run["meta"].status != "completed":
        raise HTTPException(status_code=400, detail="Run is not completed")
    if not run["leads"]:
        raise HTTPException(status_code=400, detail="No leads to export")

    # Rehydrate leads and source logs
    leads = [Lead(**ld) for ld in run["leads"]]
    source_logs = [SourceLog(**sl) for sl in run["source_logs"]]

    # Generate xlsx
    xlsx_path = DATA_OUTPUT / f"run_{request.run_id}.xlsx"
    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    export_workbook(leads, source_logs, xlsx_path)

    return StreamingResponse(
        open(xlsx_path, "rb"),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f'attachment; filename="run_{request.run_id}.xlsx"',
        },
    )


@router.post("/json")
def export_json(request: ExportRequest) -> StreamingResponse:
    """Export kept leads as a downloadable JSON file."""
    run = get_run(request.run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {request.run_id}")
    if run["meta"].status != "completed":
        raise HTTPException(status_code=400, detail="Run is not completed")

    content = json.dumps(run["leads"], indent=2, default=str)
    buf = BytesIO(content.encode("utf-8"))

    return StreamingResponse(
        buf,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="run_{request.run_id}_leads.json"',
        },
    )
