"""Rules engine — discard rules, quality-tier assignment, lane validation.

Quality tier is ALWAYS computed from fields — never trusted from input.
"""

from __future__ import annotations

import logging
from typing import Any

from app.config import get_excluded_states
from app.models import DiscardRecord, Lead, LeadLane, QualityTier

logger = logging.getLogger(__name__)


# ── Quality-tier assignment ─────────────────────────────────────────────

def assign_quality_tier(lead: Lead) -> QualityTier:
    """Compute quality tier from actual field values — never trust input.

    Best-case: company_name, website, business_phone, reason_qualified,
               named_contact, contact_title — all present.
    Mid-level: company_name, website, business_phone, reason_qualified — all present.
    Weak:      anything else.
    """
    has_core = all([
        lead.company_name.strip(),
        lead.website.strip(),
        lead.business_phone.strip(),
        lead.reason_qualified.strip(),
    ])
    if not has_core:
        return QualityTier.WEAK

    has_contact = all([
        lead.named_contact and lead.named_contact.strip(),
        lead.contact_title and lead.contact_title.strip(),
    ])
    if has_contact:
        return QualityTier.BEST_CASE

    return QualityTier.MID_LEVEL


def recompute_quality_tiers(leads: list[Lead]) -> list[Lead]:
    """Recompute quality_tier for every lead from its fields.

    Call this whenever loading leads from external JSON to ensure
    quality_tier reflects actual field state, not stale input values.
    """
    for lead in leads:
        lead.quality_tier = assign_quality_tier(lead)
    return leads


# ── Discard rules ───────────────────────────────────────────────────────

def _make_discard(lead: Lead, reason: str, rule: str) -> DiscardRecord:
    """Build a DiscardRecord carrying full lead data for display."""
    return DiscardRecord(
        reason=reason,
        rule=rule,
        lead_id=lead.lead_id,
        company_name=lead.company_name,
        lead_lane=lead.lead_lane.value,
        portfolio_type=lead.portfolio_type,
        state=lead.state,
        city=lead.city,
        quality_tier=lead.quality_tier.value,
        confidence_score=lead.confidence_score,
        website=lead.website,
        business_phone=lead.business_phone,
        reason_qualified=lead.reason_qualified,
        notes=lead.notes,
        source_type=lead.source_type.value,
        source_url=lead.source_url,
        named_contact=lead.named_contact,
        contact_title=lead.contact_title,
        employee_estimate=lead.employee_estimate,
        distress_signal=lead.distress_signal,
        financing_signal=lead.financing_signal,
        bankruptcy_chapter=lead.bankruptcy_chapter,
        private_company_confirmed=lead.private_company_confirmed,
        public_company_confirmed=lead.public_company_confirmed,
        trustee_related=lead.trustee_related,
        collected_at=lead.collected_at,
    )


def check_discard(lead: Lead, rules: dict[str, Any]) -> DiscardRecord | None:
    """Apply all discard rules. Return a DiscardRecord if the lead should be
    thrown away, or None if it should be kept."""

    # Rule 1: weak quality
    if lead.quality_tier == QualityTier.WEAK:
        return _make_discard(
            lead,
            reason="Quality tier is weak — missing critical fields",
            rule="weak_quality",
        )

    # Rule 2: excluded state for lane
    excluded = get_excluded_states(rules, lead.lead_lane.value)
    if lead.state.upper() in excluded:
        return _make_discard(
            lead,
            reason=f"State {lead.state} excluded for lane {lead.lead_lane.value}",
            rule="excluded_state",
        )

    # Rule 3: public company
    if lead.public_company_confirmed:
        return _make_discard(
            lead,
            reason="Public company — only private companies allowed",
            rule="public_company",
        )

    # Rule 4: trustee
    if lead.trustee_related:
        return _make_discard(
            lead,
            reason="Trustee-related — excluded entirely",
            rule="trustee",
        )

    # Rule 5: non-target bankruptcy chapter
    if lead.lead_lane == LeadLane.BANKRUPTCY:
        ch = (lead.bankruptcy_chapter or "").strip()
        if ch not in ("13", "7"):
            return _make_discard(
                lead,
                reason=f"Bankruptcy lane targets Ch.13 (Ch.7 allowed as potential Ch.13) — got chapter '{ch}' or unknown",
                rule="non_target_bankruptcy_chapter",
            )

    return None


def apply_rules(leads: list[Lead], rules: dict[str, Any]) -> tuple[list[Lead], list[DiscardRecord]]:
    """Run all discard rules over a list of leads.

    Always recomputes quality_tier from fields before evaluating rules.
    Returns (kept_leads, discard_records).
    """
    kept: list[Lead] = []
    discarded: list[DiscardRecord] = []

    for lead in leads:
        # Always compute quality tier from fields — never trust input
        lead.quality_tier = assign_quality_tier(lead)

        record = check_discard(lead, rules)
        if record:
            lead.status = "discarded"
            discarded.append(record)
            logger.info("Discarded %s (%s): %s", lead.lead_id, lead.company_name, record.reason)
        else:
            kept.append(lead)

    logger.info("Rules applied: %d kept, %d discarded", len(kept), len(discarded))
    return kept, discarded
