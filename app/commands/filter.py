"""filter command — filter existing leads by various criteria."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.models import Lead

logger = logging.getLogger(__name__)


def load_leads(input_path: Path) -> list[Lead]:
    """Load leads from a JSON file."""
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    return [Lead(**record) for record in raw]


def run_filter(
    input_path: Path,
    lane: str | None = None,
    state: str | None = None,
    min_quality: str | None = None,
    min_confidence: float | None = None,
    private_only: bool = False,
) -> list[Lead]:
    """Filter leads from a JSON file by the given criteria."""
    leads = load_leads(input_path)
    original_count = len(leads)

    if lane:
        leads = [ld for ld in leads if ld.lead_lane.value == lane]

    if state:
        leads = [ld for ld in leads if ld.state.upper() == state.upper()]

    if min_quality:
        tier_order = {"best_case": 0, "mid_level": 1, "weak": 2}
        min_rank = tier_order.get(min_quality, 2)
        leads = [ld for ld in leads if tier_order.get(ld.quality_tier.value, 9) <= min_rank]

    if min_confidence is not None:
        leads = [ld for ld in leads if ld.confidence_score >= min_confidence]

    if private_only:
        leads = [ld for ld in leads if ld.private_company_confirmed and not ld.public_company_confirmed]

    logger.info("Filtered %d → %d leads", original_count, len(leads))

    data = [ld.model_dump(mode="json") for ld in leads]
    print(json.dumps(data, indent=2, default=str))

    return leads
