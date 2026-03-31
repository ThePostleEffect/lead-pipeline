"""CSV import source — loads leads from a CSV file.

Supports any CSV where headers map to Lead model fields.
Handles common variations (extra whitespace, missing columns, BOM markers).
"""

from __future__ import annotations

import csv
import logging
from pathlib import Path

from app.models import Lead, LeadLane, SearchFilters, SourceLog, SourceType
from app.sources.base import BaseSource
from app.utils.phones import normalize_phone
from app.utils.states import normalize_state
from app.utils.urls import normalize_url

logger = logging.getLogger(__name__)

# Map loose CSV header names to Lead field names
_HEADER_ALIASES: dict[str, str] = {
    "company": "company_name",
    "name": "company_name",
    "lane": "lead_lane",
    "type": "portfolio_type",
    "portfolio": "portfolio_type",
    "phone": "business_phone",
    "contact": "named_contact",
    "contact_name": "named_contact",
    "title": "contact_title",
    "employees": "employee_estimate",
    "size": "employee_estimate",
    "reason": "reason_qualified",
    "qualification": "reason_qualified",
    "url": "source_url",
    "source": "source_url",
    "private": "private_company_confirmed",
    "public": "public_company_confirmed",
    "trustee": "trustee_related",
    "distress": "distress_signal",
    "financing": "financing_signal",
    "chapter": "bankruptcy_chapter",
    "bk_chapter": "bankruptcy_chapter",
}


def _resolve_header(raw: str) -> str:
    """Map a raw CSV header to a Lead field name."""
    cleaned = raw.strip().lower().replace(" ", "_")
    return _HEADER_ALIASES.get(cleaned, cleaned)


def _parse_bool(val: str) -> bool:
    return val.strip().lower() in ("true", "yes", "1", "y")


def _parse_int(val: str) -> int | None:
    val = val.strip()
    if not val:
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


class CsvImportSource(BaseSource):
    """Load leads from a CSV file."""

    name = "csv_import"
    source_type = "manual"

    def __init__(self, filepath: Path) -> None:
        self.filepath = filepath

    def collect(self, lane: str, limit: int | None = None, filters: SearchFilters | None = None) -> tuple[list[Lead], SourceLog]:
        if not self.filepath.exists():
            logger.warning("CSV file not found: %s", self.filepath)
            return [], SourceLog(
                source_name=self.name,
                source_type=SourceType.MANUAL,
                source_url=str(self.filepath),
                notes=f"File not found: {self.filepath}",
            )

        # Read CSV, handle BOM
        text = self.filepath.read_text(encoding="utf-8-sig")
        reader = csv.DictReader(text.splitlines())

        # Resolve headers
        if reader.fieldnames is None:
            logger.warning("CSV has no headers: %s", self.filepath)
            return [], SourceLog(
                source_name=self.name,
                source_type=SourceType.MANUAL,
                source_url=str(self.filepath),
                notes="CSV has no headers",
            )

        header_map = {raw: _resolve_header(raw) for raw in reader.fieldnames}

        raw_count = 0
        leads: list[Lead] = []

        for row in reader:
            raw_count += 1
            # Remap keys
            record: dict[str, str] = {}
            for raw_key, value in row.items():
                mapped = header_map.get(raw_key, raw_key)
                record[mapped] = (value or "").strip()

            # Skip rows not matching the requested lane
            row_lane = record.get("lead_lane", "")
            if row_lane and row_lane != lane:
                continue

            # Skip rows with no company name
            if not record.get("company_name"):
                continue

            try:
                lead = Lead(
                    company_name=record.get("company_name", ""),
                    lead_lane=LeadLane(lane),
                    portfolio_type=record.get("portfolio_type", ""),
                    private_company_confirmed=_parse_bool(record.get("private_company_confirmed", "")),
                    public_company_confirmed=_parse_bool(record.get("public_company_confirmed", "")),
                    trustee_related=_parse_bool(record.get("trustee_related", "")),
                    state=normalize_state(record.get("state", "")),
                    city=record.get("city", ""),
                    website=normalize_url(record.get("website", "")),
                    business_phone=normalize_phone(record.get("business_phone", "")),
                    reason_qualified=record.get("reason_qualified", ""),
                    source_type=SourceType.MANUAL,
                    source_url=record.get("source_url", ""),
                    notes=record.get("notes", ""),
                    named_contact=record.get("named_contact") or None,
                    contact_title=record.get("contact_title") or None,
                    employee_estimate=_parse_int(record.get("employee_estimate", "")),
                    distress_signal=record.get("distress_signal") or None,
                    financing_signal=record.get("financing_signal") or None,
                    bankruptcy_chapter=record.get("bankruptcy_chapter") or None,
                )
                leads.append(lead)
            except Exception as exc:
                logger.warning("Skipping malformed CSV row %d: %s", raw_count, exc)
                continue

        if limit and len(leads) > limit:
            leads = leads[:limit]

        source_log = SourceLog(
            source_name=self.name,
            source_type=SourceType.MANUAL,
            source_url=str(self.filepath),
            leads_found=raw_count,
            leads_kept=len(leads),
            notes=f"CSV import, filtered to lane={lane}",
        )

        logger.info("CsvImport: %d leads for lane '%s' from %s", len(leads), lane, self.filepath)
        return leads, source_log
