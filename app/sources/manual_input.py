"""Manual input source — loads leads from a JSON file in data/input/."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.config import DATA_INPUT
from app.models import Lead, LeadLane, SearchFilters, SourceLog, SourceType
from app.sources.base import BaseSource
from app.utils.phones import normalize_phone
from app.utils.states import normalize_state
from app.utils.urls import normalize_url

logger = logging.getLogger(__name__)


class ManualInputSource(BaseSource):
    name = "manual_input"
    source_type = "manual"

    def __init__(self, filepath: Path | None = None) -> None:
        if filepath is None:
            raise ValueError(
                "ManualInputSource requires a filepath. "
                "Use --source to provide a JSON file, or --source-type web for live collection."
            )
        self.filepath = filepath

    def collect(self, lane: str, limit: int | None = None, filters: SearchFilters | None = None) -> tuple[list[Lead], SourceLog]:
        """Load leads from JSON, filter to the requested lane, normalize fields."""
        if not self.filepath.exists():
            logger.warning("Input file not found: %s", self.filepath)
            return [], SourceLog(
                source_name=self.name,
                source_type=SourceType.MANUAL,
                source_url=str(self.filepath),
                notes=f"File not found: {self.filepath}",
            )

        raw = json.loads(self.filepath.read_text(encoding="utf-8"))
        logger.info("Loaded %d raw records from %s", len(raw), self.filepath)

        leads: list[Lead] = []
        for record in raw:
            # Skip records not matching the requested lane
            if record.get("lead_lane") != lane:
                continue

            lead = Lead(
                company_name=record.get("company_name", ""),
                lead_lane=LeadLane(record["lead_lane"]),
                portfolio_type=record.get("portfolio_type", ""),
                private_company_confirmed=record.get("private_company_confirmed", False),
                public_company_confirmed=record.get("public_company_confirmed", False),
                trustee_related=record.get("trustee_related", False),
                state=normalize_state(record.get("state", "")),
                city=record.get("city", ""),
                website=normalize_url(record.get("website", "")),
                business_phone=normalize_phone(record.get("business_phone", "")),
                reason_qualified=record.get("reason_qualified", ""),
                source_type=SourceType(record.get("source_type", "manual")),
                source_url=record.get("source_url", ""),
                notes=record.get("notes", ""),
                named_contact=record.get("named_contact"),
                contact_title=record.get("contact_title"),
                employee_estimate=record.get("employee_estimate"),
                distress_signal=record.get("distress_signal"),
                financing_signal=record.get("financing_signal"),
                bankruptcy_chapter=record.get("bankruptcy_chapter"),
            )
            leads.append(lead)

        if limit and len(leads) > limit:
            leads = leads[:limit]

        source_log = SourceLog(
            source_name=self.name,
            source_type=SourceType.MANUAL,
            source_url=str(self.filepath),
            leads_found=len(raw),
            leads_kept=len(leads),
            notes=f"Filtered to lane={lane}",
        )

        logger.info("ManualInput: %d leads for lane '%s'", len(leads), lane)
        return leads, source_log
