"""Background task runner for pipeline execution.

Uses ThreadPoolExecutor because the pipeline is synchronous (blocking
requests calls). Max 2 workers to avoid hammering external APIs.
"""

from __future__ import annotations

import json
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

from api.models import CollectRequest
from api.run_store import update_run
from app.config import DATA_OUTPUT
from app.models import DiscardRecord, SearchFilters

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=2)


def submit_collect(run_id: str, request: CollectRequest, source_path: Path | None = None) -> None:
    """Submit a pipeline collect run to the thread pool."""
    _executor.submit(_execute_collect, run_id, request, source_path)


def _execute_collect(run_id: str, request: CollectRequest, source_path: Path | None) -> None:
    """Run the pipeline in a background thread. Updates the run store on completion."""
    from app.commands.collect import run_collect
    from app.exporter import export_workbook

    update_run(run_id, status="running")

    try:
        output_file = DATA_OUTPUT / f"run_{run_id}_kept.json"
        discards_file = DATA_OUTPUT / f"run_{run_id}_discards.json"

        # Build search filters from request
        filter_kwargs: dict = {}
        if request.chapters:
            filter_kwargs["chapters"] = [c.strip() for c in request.chapters.split(",")]
        if request.lookback_days is not None:
            filter_kwargs["lookback_days"] = request.lookback_days
        if request.include_individuals is not None:
            filter_kwargs["include_individuals"] = request.include_individuals
        if request.company_types:
            filter_kwargs["company_types"] = [t.strip() for t in request.company_types.split(",")]
        search_filters = SearchFilters(**filter_kwargs) if filter_kwargs else None

        leads, source_logs = run_collect(
            lane=request.lane,
            limit=request.limit,
            min_quality=request.min_quality,
            fmt="json",
            source_file=source_path,
            source_type=request.source_type,
            output_file=output_file,
            discards_file=discards_file if request.save_discards else None,
            search_filters=search_filters,
        )

        # Read discards back from file (run_collect writes them, doesn't return them)
        discards: list[dict] = []
        if request.save_discards and discards_file.exists():
            raw = json.loads(discards_file.read_text(encoding="utf-8"))
            discards = raw if isinstance(raw, list) else []

        # Optional Excel export
        xlsx_path: Path | None = None
        if request.export_xlsx and leads:
            xlsx_path = DATA_OUTPUT / f"run_{run_id}.xlsx"
            export_workbook(leads, source_logs, xlsx_path)

        raw_signal_count = source_logs[0].leads_found if source_logs else 0

        update_run(
            run_id,
            status="completed",
            completed_at=datetime.now(timezone.utc).isoformat(),
            raw_signal_count=raw_signal_count,
            kept_count=len(leads),
            discard_count=len(discards),
            output_json_path=str(output_file),
            discard_json_path=str(discards_file) if request.save_discards else None,
            xlsx_path=str(xlsx_path) if xlsx_path else None,
            leads=[ld.model_dump(mode="json") for ld in leads],
            discards=discards,
            source_logs=[sl.model_dump(mode="json") for sl in source_logs],
        )

        logger.info("Run %s completed: %d kept, %d discarded", run_id, len(leads), len(discards))

    except Exception as exc:
        logger.exception("Run %s failed: %s", run_id, exc)
        update_run(
            run_id,
            status="failed",
            completed_at=datetime.now(timezone.utc).isoformat(),
            error=str(exc),
        )
