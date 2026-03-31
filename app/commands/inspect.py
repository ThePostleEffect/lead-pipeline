"""inspect command — deep-inspect a single lead by ID."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from app.config import load_rules
from app.models import Lead
from app.rules import assign_quality_tier
from app.scoring import calculate_confidence

logger = logging.getLogger(__name__)


def run_inspect(input_path: Path, lead_id: str) -> dict | None:
    """Look up a single lead by ID and print its full inspection record.

    Recomputes quality_tier and score from current fields to show ground truth.
    """
    raw = json.loads(input_path.read_text(encoding="utf-8"))
    leads = [Lead(**record) for record in raw]

    target: Lead | None = None
    for lead in leads:
        if lead.lead_id == lead_id:
            target = lead
            break

    if target is None:
        output = {"error": f"Lead not found: {lead_id}"}
        print(json.dumps(output, indent=2))
        return None

    # Recompute quality tier and score from fields (never trust stored values)
    rules = load_rules()
    target.quality_tier = assign_quality_tier(target)
    score, breakdown, reasons = calculate_confidence(target, rules)
    target.confidence_score = score
    target.score_breakdown = breakdown
    target.score_reasons = reasons

    inspection = {
        "lead_record": target.model_dump(mode="json"),
        "quality_tier": target.quality_tier.value,
        "confidence_score": target.confidence_score,
        "score_breakdown": target.score_breakdown,
        "score_reasons": target.score_reasons,
        "source_provenance": {
            "source_type": target.source_type.value,
            "source_url": target.source_url,
        },
        "rule_flags": {
            "private_company_confirmed": target.private_company_confirmed,
            "public_company_confirmed": target.public_company_confirmed,
            "trustee_related": target.trustee_related,
        },
        "notes": target.notes,
    }

    print(json.dumps(inspection, indent=2, default=str))
    return inspection
