"""collect command — run the full pipeline for a lane.

Supports multiple source types:
  - web (default)  — PublicWebSource (CourtListener, Brave, RSS, etc.)
  - json           — ManualInputSource from .json file
  - csv            — CsvImportSource from .csv file
  - auto           — detect from file extension

When --source is not provided, defaults to live web collection.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.config import load_rules
from app.dedupe import deduplicate
from app.enrich.company_enrichment import enrich_companies
from app.filters.company_type import apply_company_type_filter
from app.enrich.contact_enrichment import enrich_contacts
from app.enrich.opencorporates import enrich_leads_opencorporates
from app.enrich.pacer_verify import enrich_leads_pacer
from app.enrich.sec_edgar import enrich_leads_sec_edgar
from app.enrich.web_enrichment import enrich_leads_from_web
from app.models import DiscardRecord, Lead, LeadLane, SearchFilters, SourceLog
from app.rules import apply_rules
from app.scoring import score_leads
from app.sources.base import BaseSource

logger = logging.getLogger(__name__)

VALID_LANES = {e.value for e in LeadLane}


def _resolve_source(source_file: Path | None, source_type: str | None) -> BaseSource:
    """Pick the right source collector based on file path and/or explicit type."""
    from app.sources.csv_import import CsvImportSource
    from app.sources.manual_input import ManualInputSource

    # Explicit type override
    if source_type == "web":
        from app.sources.public_web import PublicWebSource
        return PublicWebSource()

    if source_type == "csv":
        if not source_file:
            raise ValueError("--source is required when --source-type is csv")
        return CsvImportSource(filepath=source_file)

    if source_type == "json":
        return ManualInputSource(filepath=source_file)

    # Auto-detect from extension
    if source_file:
        ext = source_file.suffix.lower()
        if ext == ".csv":
            return CsvImportSource(filepath=source_file)
        if ext in (".json", ".jsonl"):
            return ManualInputSource(filepath=source_file)
        # Unknown extension — try JSON
        logger.warning("Unknown file extension '%s', defaulting to JSON loader", ext)
        return ManualInputSource(filepath=source_file)

    # No source file — default to live web collection
    from app.sources.public_web import PublicWebSource
    return PublicWebSource()


def run_collect(
    lane: str,
    limit: int | None = None,
    min_quality: str | None = None,
    fmt: str = "json",
    source_file: Path | None = None,
    source_type: str | None = None,
    output_file: Path | None = None,
    discards_file: Path | None = None,
    search_filters: SearchFilters | None = None,
) -> tuple[list[Lead], list[SourceLog]]:
    """Execute the collect pipeline:
    source → normalize → enrich → rules → dedupe → score → output.
    """
    if lane not in VALID_LANES:
        raise ValueError(f"Invalid lane '{lane}'. Must be one of: {VALID_LANES}")

    filters = search_filters or SearchFilters()
    rules = load_rules()

    # 1. Collect from source
    # Over-fetch raw signals to account for discard/dedup/quality attrition.
    # Historical yield rate is roughly 40-60%, so 3x gives comfortable headroom.
    # The final limit is re-applied after filtering in step 7.
    OVERFETCH = 3
    collect_limit = (limit * OVERFETCH) if limit else None
    source = _resolve_source(source_file, source_type)
    leads, source_log = source.collect(lane=lane, limit=collect_limit, filters=filters)
    source_logs = [source_log]

    if not leads:
        logger.warning("No leads collected for lane '%s'", lane)
        _output_leads([], fmt, output_file)
        return [], source_logs

    logger.info("Collected %d raw leads from %s", len(leads), source.name)

    # 1b. Company type filter — applied before enrichment to avoid wasting API calls
    type_filter_discards: list[DiscardRecord] = []
    if filters.company_types:
        leads, rejected = apply_company_type_filter(leads, filters.company_types)
        label = "+".join(filters.company_types)
        type_filter_discards = [
            DiscardRecord(
                lead_id=ld.lead_id,
                company_name=ld.company_name,
                lead_lane=ld.lead_lane.value,
                state=ld.state,
                quality_tier=ld.quality_tier.value,
                website=ld.website,
                business_phone=ld.business_phone,
                reason=f"Company type does not match filter: {label}",
                rule="company_type_filter",
            )
            for ld in rejected
        ]
        logger.info(
            "Company type filter [%s]: %d leads remain, %d rejected",
            label, len(leads), len(rejected),
        )
        if not leads:
            logger.warning("No leads remain after company type filter — all %d rejected", len(rejected))
            _output_leads([], fmt, output_file)
            if discards_file and type_filter_discards:
                _output_discards(type_filter_discards, discards_file)
            return [], source_logs

    # 2. Enrich
    leads = enrich_companies(leads)
    leads = enrich_contacts(leads)

    # 2b. Web enrichment — find websites/phones for leads missing them
    leads = enrich_leads_from_web(leads)

    # 2c. Entity verification — confirm company identity via OpenCorporates
    leads = enrich_leads_opencorporates(leads)

    # 2d. SEC EDGAR — detect public companies (triggers discard rule)
    leads = enrich_leads_sec_edgar(leads)

    # 2e. PACER verification — deeper case validation (bankruptcy lane only, needs credentials)
    leads = enrich_leads_pacer(leads)

    # 3. Apply rules (recomputes quality tier from fields, then discards)
    leads, discards = apply_rules(leads, rules)

    # 4. Deduplicate
    leads = deduplicate(leads)

    # 5. Score and rank
    leads = score_leads(leads, rules)

    # 6. Apply min-quality filter if requested
    if min_quality:
        tier_order = {"best_case": 0, "mid_level": 1, "weak": 2}
        min_rank = tier_order.get(min_quality, 2)
        leads = [ld for ld in leads if tier_order.get(ld.quality_tier.value, 9) <= min_rank]

    # 7. Apply limit after filtering
    if limit and len(leads) > limit:
        leads = leads[:limit]

    # Update source log with final kept count
    source_logs[0].leads_kept = len(leads)

    # 8. Output
    _output_leads(leads, fmt, output_file)

    # Merge company type filter discards into the main discard list
    all_discards = type_filter_discards + discards

    # 9. Write discards if requested
    if discards_file and all_discards:
        _output_discards(all_discards, discards_file)

    return leads, source_logs


def _output_leads(leads: list[Lead], fmt: str, output_file: Path | None) -> None:
    """Write kept leads to stdout or file."""
    data = [ld.model_dump(mode="json") for ld in leads]

    if fmt == "json":
        json_str = json.dumps(data, indent=2, default=str)
        if output_file:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            output_file.write_text(json_str, encoding="utf-8")
            logger.info("Output written to %s", output_file)
        else:
            print(json_str)
    else:
        print(f"Collected {len(leads)} leads")
        for ld in leads:
            print(f"  [{ld.quality_tier.value}] {ld.company_name} ({ld.state}) — score {ld.confidence_score}")


def _output_discards(discards: list[DiscardRecord], discards_file: Path) -> None:
    """Write discard records to a JSON file for review."""
    data = [d.model_dump(mode="json") for d in discards]
    discards_file.parent.mkdir(parents=True, exist_ok=True)
    discards_file.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    logger.info("Discards written to %s (%d records)", discards_file, len(discards))
