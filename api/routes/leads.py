"""Leads endpoint — inspect a single lead with recomputed scores."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from api.run_store import get_run
from app.config import load_rules
from app.models import Lead
from app.rules import assign_quality_tier
from app.scoring import calculate_confidence

router = APIRouter()


@router.get("/{lead_id}")
def get_lead_detail(lead_id: str, run_id: str = Query(...)) -> dict:
    """Deep-inspect a single lead. Recomputes quality tier and score."""
    run = get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    # Find lead in run data
    target_data: dict | None = None
    for ld in run["leads"]:
        if ld.get("lead_id") == lead_id:
            target_data = ld
            break

    if target_data is None:
        raise HTTPException(status_code=404, detail=f"Lead not found: {lead_id}")

    # Rehydrate as Lead model and recompute
    lead = Lead(**target_data)
    rules = load_rules()
    lead.quality_tier = assign_quality_tier(lead)
    score, breakdown, reasons = calculate_confidence(lead, rules)
    lead.confidence_score = score
    lead.score_breakdown = breakdown
    lead.score_reasons = reasons

    return {
        "lead_record": lead.model_dump(mode="json"),
        "quality_tier": lead.quality_tier.value,
        "confidence_score": lead.confidence_score,
        "score_breakdown": lead.score_breakdown,
        "score_reasons": lead.score_reasons,
        "source_provenance": {
            "source_type": lead.source_type.value,
            "source_url": lead.source_url,
        },
        "rule_flags": {
            "private_company_confirmed": lead.private_company_confirmed,
            "public_company_confirmed": lead.public_company_confirmed,
            "trustee_related": lead.trustee_related,
        },
        "notes": lead.notes,
    }
