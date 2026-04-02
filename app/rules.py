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

    Phone is the primary actionability signal — if you can call them, the
    lead has value regardless of what other fields are missing.

    Best-case: company_name + website + business_phone + reason_qualified
               + named_contact + contact_title — fully enriched.
    Mid-level: company_name + business_phone — minimum actionable lead.
    Weak:      missing company_name or business_phone — not actionable.
    """
    # Without a company name or phone number the lead isn't actionable
    if not lead.company_name.strip() or not lead.business_phone.strip():
        return QualityTier.WEAK

    # Has phone — check for full enrichment to reach best-case
    has_full_core = all([
        lead.website.strip(),
        lead.reason_qualified.strip(),
    ])
    if has_full_core:
        has_contact = all([
            lead.named_contact and lead.named_contact.strip(),
            lead.contact_title and lead.contact_title.strip(),
        ])
        return QualityTier.BEST_CASE if has_contact else QualityTier.MID_LEVEL

    # Has company + phone but missing website/reason — still mid-level (phone is enough to act)
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
        email=lead.email,
        score_breakdown=lead.score_breakdown,
        score_reasons=lead.score_reasons,
    )


def check_discard(lead: Lead, rules: dict[str, Any]) -> DiscardRecord | None:
    """Apply all discard rules. Return a DiscardRecord if the lead should be
    thrown away, or None if it should be kept.

    Hard rules (apply to all quality tiers): public company, trustee, excluded state.
    Soft rules (skip for mid-level+): weak quality gate, non-target bankruptcy chapter.
    """
    is_actionable = lead.quality_tier in (QualityTier.MID_LEVEL, QualityTier.BEST_CASE)

    # Rule 1: weak quality — only applies to weak leads
    if lead.quality_tier == QualityTier.WEAK:
        return _make_discard(
            lead,
            reason="Quality tier is weak — missing critical fields (company name, website, phone, or reason)",
            rule="weak_quality",
        )

    # Rule 2: public company — hard discard regardless of quality
    if lead.public_company_confirmed:
        return _make_discard(
            lead,
            reason="Public company — only private companies targeted",
            rule="public_company",
        )

    # Rule 3: trustee — hard discard regardless of quality
    if lead.trustee_related:
        return _make_discard(
            lead,
            reason="Trustee-related entity — excluded entirely",
            rule="trustee",
        )

    # Rule 4: excluded state — hard rule, applies regardless of quality
    excluded = get_excluded_states(rules, lead.lead_lane.value)
    if lead.state.upper() in excluded:
        return _make_discard(
            lead,
            reason=f"State {lead.state} excluded for lane {lead.lead_lane.value}",
            rule="excluded_state",
        )

    # Rule 5: non-target bankruptcy chapter — soft rule, skip for mid-level+ leads
    if not is_actionable and lead.lead_lane == LeadLane.BANKRUPTCY:
        ch = (lead.bankruptcy_chapter or "").strip()
        if ch not in ("13", "7"):
            return _make_discard(
                lead,
                reason=f"Bankruptcy lane targets Ch.13/7 — got chapter '{ch}' or unknown",
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
