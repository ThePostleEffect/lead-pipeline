"""Public web source — framework for public-source data collection.

This module provides the scaffolding for collecting leads from public data
sources. Each sub-collector targets a specific type of public data.

Active sub-collectors:
  - CourtListener bankruptcy filings (bankruptcy lane)
  - Court RSS bankruptcy feeds (bankruptcy lane)
  - FDIC Failed Banks (charged_off lane)
  - CFPB Consumer Complaints (charged_off lane)

To add a new sub-collector, implement a function with this signature:

    def collect_from_source(lane: str, limit: int | None) -> list[dict]

Then register it in the ACTIVE_COLLECTORS list below.
"""

from __future__ import annotations

import logging

from app.models import Lead, LeadLane, SearchFilters, SourceLog, SourceType
from app.sources.base import BaseSource
from app.utils.phones import normalize_phone
from app.utils.states import normalize_state
from app.utils.urls import normalize_url

logger = logging.getLogger(__name__)


# ── Sub-collector registry ──────────────────────────────────────────────
# Each entry is (name, callable) where callable returns a list of raw dicts.
# Uncomment and add real implementations as sources become available.

from app.sources.courtlistener import collect_courtlistener_bankruptcy
from app.sources.court_rss import collect_court_rss
from app.sources.fdic_failed_banks import collect_fdic_failed_banks
from app.sources.cfpb_complaints import collect_cfpb_complaints

ACTIVE_COLLECTORS: list[tuple[str, object]] = [
    # Bankruptcy lane
    ("courtlistener_bankruptcy", collect_courtlistener_bankruptcy),
    ("court_rss", collect_court_rss),
    # Charged-off lane
    ("fdic_failed_banks", collect_fdic_failed_banks),
    ("cfpb_complaints", collect_cfpb_complaints),
]


def _normalize_raw(raw: dict, lane: str) -> Lead:
    """Convert a raw dict from any sub-collector into a normalized Lead."""
    return Lead(
        company_name=raw.get("company_name", ""),
        lead_lane=LeadLane(lane),
        portfolio_type=raw.get("portfolio_type", ""),
        private_company_confirmed=raw.get("private_company_confirmed", False),
        public_company_confirmed=raw.get("public_company_confirmed", False),
        trustee_related=raw.get("trustee_related", False),
        state=normalize_state(raw.get("state", "")),
        city=raw.get("city", ""),
        website=normalize_url(raw.get("website", "")),
        business_phone=normalize_phone(raw.get("business_phone", "")),
        reason_qualified=raw.get("reason_qualified", ""),
        source_type=SourceType.PUBLIC_WEB,
        source_url=raw.get("source_url", ""),
        notes=raw.get("notes", ""),
        named_contact=raw.get("named_contact") or None,
        contact_title=raw.get("contact_title") or None,
        employee_estimate=raw.get("employee_estimate"),
        distress_signal=raw.get("distress_signal") or None,
        financing_signal=raw.get("financing_signal") or None,
        bankruptcy_chapter=raw.get("bankruptcy_chapter") or None,
    )


class PublicWebSource(BaseSource):
    """Aggregate collector that runs all active public-source sub-collectors."""

    name = "public_web"
    source_type = "public_web"

    def collect(self, lane: str, limit: int | None = None, filters: SearchFilters | None = None) -> tuple[list[Lead], SourceLog]:
        if not ACTIVE_COLLECTORS:
            logger.info("PublicWebSource: no active sub-collectors registered")
            return [], SourceLog(
                source_name=self.name,
                source_type=SourceType.PUBLIC_WEB,
                notes="No active sub-collectors — register implementations in ACTIVE_COLLECTORS",
            )

        filters = filters or SearchFilters()
        all_leads: list[Lead] = []
        collector_notes: list[str] = []

        for coll_name, coll_fn in ACTIVE_COLLECTORS:
            try:
                raw_results = coll_fn(lane, limit, filters)  # type: ignore[operator]
                leads = [_normalize_raw(r, lane) for r in raw_results]
                all_leads.extend(leads)
                collector_notes.append(f"{coll_name}: {len(leads)} leads")
                logger.info("Sub-collector '%s' returned %d leads", coll_name, len(leads))
            except Exception as exc:
                logger.error("Sub-collector '%s' failed: %s", coll_name, exc)
                collector_notes.append(f"{coll_name}: ERROR — {exc}")

        if limit and len(all_leads) > limit:
            all_leads = all_leads[:limit]

        source_log = SourceLog(
            source_name=self.name,
            source_type=SourceType.PUBLIC_WEB,
            leads_found=len(all_leads),
            leads_kept=len(all_leads),
            notes="; ".join(collector_notes) if collector_notes else "No results",
        )

        return all_leads, source_log
