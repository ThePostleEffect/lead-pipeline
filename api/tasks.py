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
from api.run_store import get_seen_keys, index_run_leads, push_global_discards, update_run
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

        # Load prior-run dedup keys before running so we can flag repeats
        seen_keys = get_seen_keys()

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

        # Cross-run deduplication — flag leads seen in previous runs
        from app.dedupe import lead_keys as get_lead_keys
        cross_run_discards: list[dict] = []
        if leads and seen_keys:
            still_unique = []
            for lead in leads:
                matched = get_lead_keys(lead) & set(seen_keys.keys())
                if matched:
                    key = next(iter(matched))
                    prior_run_id, prior_lane = seen_keys[key]
                    cross_run_discards.append({
                        "lead_id": lead.lead_id,
                        "company_name": lead.company_name,
                        "lead_lane": lead.lead_lane.value,
                        "state": lead.state,
                        "quality_tier": lead.quality_tier.value,
                        "website": lead.website,
                        "business_phone": lead.business_phone,
                        "reason": f"Previously collected in {prior_run_id} ({prior_lane} lane)",
                        "rule": "cross_run_duplicate",
                    })
                    logger.info(
                        "Cross-run dedup: '%s' already in %s (%s lane)",
                        lead.company_name, prior_run_id, prior_lane,
                    )
                else:
                    still_unique.append(lead)
            leads = still_unique

        # Read discards back from file (run_collect writes them, doesn't return them)
        discards: list[dict] = []
        if request.save_discards and discards_file.exists():
            raw = json.loads(discards_file.read_text(encoding="utf-8"))
            discards = raw if isinstance(raw, list) else []

        # Merge cross-run discards and re-write the file if needed
        if cross_run_discards:
            discards.extend(cross_run_discards)
            if request.save_discards:
                discards_file.parent.mkdir(parents=True, exist_ok=True)
                discards_file.write_text(
                    json.dumps(discards, indent=2, default=str), encoding="utf-8"
                )

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

        # Push discards to rolling vault (capped at 100 across all runs)
        if discards:
            push_global_discards(discards)

        # Index kept leads so future runs can detect cross-run duplicates
        if leads:
            key_entries: list[tuple[str, str, str]] = []
            for lead in leads:
                for key_str in get_lead_keys(lead):
                    key_type, key_value = key_str.split(":", 1)
                    key_entries.append((key_type, key_value, lead.company_name))
            if key_entries:
                index_run_leads(run_id, request.lane, key_entries)

        logger.info("Run %s completed: %d kept, %d discarded", run_id, len(leads), len(discards))

    except Exception as exc:
        logger.exception("Run %s failed: %s", run_id, exc)
        update_run(
            run_id,
            status="failed",
            completed_at=datetime.now(timezone.utc).isoformat(),
            error=str(exc),
        )
