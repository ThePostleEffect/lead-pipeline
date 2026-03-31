"""rank command — sort leads by quality_tier and confidence_score."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.models import Lead

logger = logging.getLogger(__name__)


def run_rank(input_path: Path) -> list[Lead]:
    """Load leads, sort best_case above mid_level, then by confidence desc."""
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    leads = [Lead(**record) for record in raw]

    tier_order = {"best_case": 0, "mid_level": 1, "weak": 2}
    leads.sort(key=lambda ld: (tier_order.get(ld.quality_tier.value, 9), -ld.confidence_score))

    logger.info("Ranked %d leads", len(leads))

    data = [ld.model_dump(mode="json") for ld in leads]
    print(json.dumps(data, indent=2, default=str))

    return leads
