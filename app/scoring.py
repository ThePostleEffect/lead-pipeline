"""Scoring engine — transparent, rule-based confidence scoring with full breakdown.

Score breakdown (max 100):
  company_name present        +15
  website present              +15
  business_phone present       +15
  reason_qualified present     +15
  named_contact present        +10
  contact_title present        +10
  employee_estimate 10-50      +10
  distress_signal present      +5
  financing_signal present     +5

Every scored lead carries:
  confidence_score   float    the 0-100 score
  score_breakdown    list     structured [{field, points, reason}, ...]
  score_reasons      list     human-readable ["+15 website present", ...]
"""

from __future__ import annotations

import logging
from typing import Any

from app.config import get_preferred_employee_range, get_scoring_weights
from app.models import Lead

logger = logging.getLogger(__name__)

# Fallback weights if rules.yaml is missing scoring section
_DEFAULT_WEIGHTS: dict[str, int] = {
    "company_name": 15,
    "website": 15,
    "business_phone": 15,
    "reason_qualified": 15,
    "named_contact": 10,
    "contact_title": 10,
    "preferred_employee_range": 10,
    "distress_signal": 5,
    "financing_signal": 5,
}


def _has(value: str | None) -> bool:
    return bool(value and value.strip())


def calculate_confidence(
    lead: Lead, rules: dict[str, Any],
) -> tuple[float, list[dict[str, Any]], list[str]]:
    """Calculate a 0-100 confidence score with full explainable breakdown.

    Returns:
        (score, breakdown, reasons)
        - breakdown: list of {"field": str, "points": int, "reason": str}
        - reasons:   list of human-readable strings like "+15 website present"
    """
    weights = get_scoring_weights(rules) or _DEFAULT_WEIGHTS
    emp_min, emp_max = get_preferred_employee_range(rules)

    score = 0.0
    breakdown: list[dict[str, Any]] = []
    reasons: list[str] = []

    def _award(field: str, points: int, reason: str) -> None:
        nonlocal score
        score += points
        breakdown.append({"field": field, "points": points, "reason": reason})
        reasons.append(f"+{points} {reason}")

    if _has(lead.company_name):
        _award("company_name", weights.get("company_name", 15), "company_name present")
    if _has(lead.website):
        _award("website", weights.get("website", 15), "website present")
    if _has(lead.business_phone):
        _award("business_phone", weights.get("business_phone", 15), "business_phone present")
    if _has(lead.reason_qualified):
        _award("reason_qualified", weights.get("reason_qualified", 15), "reason_qualified present")
    if _has(lead.named_contact):
        _award("named_contact", weights.get("named_contact", 10), "named_contact present")
    if _has(lead.contact_title):
        _award("contact_title", weights.get("contact_title", 10), "contact_title present")
    if lead.employee_estimate is not None and emp_min <= lead.employee_estimate <= emp_max:
        _award(
            "preferred_employee_range",
            weights.get("preferred_employee_range", 10),
            f"employee_estimate ({lead.employee_estimate}) in preferred range {emp_min}-{emp_max}",
        )
    if _has(lead.distress_signal):
        _award("distress_signal", weights.get("distress_signal", 5), "distress_signal present")
    if _has(lead.financing_signal):
        _award("financing_signal", weights.get("financing_signal", 5), "financing_signal present")

    return min(score, 100.0), breakdown, reasons


def score_leads(leads: list[Lead], rules: dict[str, Any]) -> list[Lead]:
    """Score every lead and return them sorted best-first.

    Populates confidence_score, score_breakdown, and score_reasons on each lead.
    """
    for lead in leads:
        score, breakdown, reasons = calculate_confidence(lead, rules)
        lead.confidence_score = score
        lead.score_breakdown = breakdown
        lead.score_reasons = reasons

    # Sort: best_case before mid_level, then by confidence descending
    tier_order = {"best_case": 0, "mid_level": 1, "weak": 2}
    leads.sort(key=lambda ld: (tier_order.get(ld.quality_tier.value, 9), -ld.confidence_score))

    logger.info("Scored %d leads", len(leads))
    return leads
