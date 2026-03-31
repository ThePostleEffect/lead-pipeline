"""summarize command — compact structured output for OpenClaw."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.models import Lead

logger = logging.getLogger(__name__)

# Fields included in the summary view
SUMMARY_FIELDS: list[str] = [
    "company_name",
    "lead_lane",
    "state",
    "website",
    "business_phone",
    "named_contact",
    "contact_title",
    "reason_qualified",
    "quality_tier",
    "confidence_score",
    "source_url",
]


def run_summarize(input_path: Path, top: int | None = None) -> list[dict]:
    """Print a compact summary of the top leads."""
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    leads = [Lead(**record) for record in raw]

    # Sort best-first
    tier_order = {"best_case": 0, "mid_level": 1, "weak": 2}
    leads.sort(key=lambda ld: (tier_order.get(ld.quality_tier.value, 9), -ld.confidence_score))

    if top and len(leads) > top:
        leads = leads[:top]

    summaries: list[dict] = []
    for lead in leads:
        data = lead.model_dump(mode="json")
        summary = {}
        for field in SUMMARY_FIELDS:
            val = data.get(field)
            if hasattr(val, "value"):
                val = val.value
            summary[field] = val if val else None
        summaries.append(summary)

    print(json.dumps(summaries, indent=2, default=str))
    return summaries
