"""Deduplication — multi-key identity matching with strength-based resolution.

Dedup key priority (checked in order):
  1. Normalized website domain  (strongest identity signal)
  2. Normalized business phone   (strong identity signal)
  3. Normalized company_name + state  (fallback)

When two leads collide on any key:
  - keep the stronger lead (best_case > mid_level > weak)
  - if same tier, prefer higher confidence_score
  - if still tied, prefer lead with more populated fields
"""

from __future__ import annotations

import logging
import re

from app.models import Lead
from app.utils.urls import extract_domain

logger = logging.getLogger(__name__)

_TIER_RANK: dict[str, int] = {"best_case": 0, "mid_level": 1, "weak": 2}

# Fields counted for the populated-fields tiebreaker
_TIEBREAK_FIELDS: list[str] = [
    "company_name", "website", "business_phone", "reason_qualified",
    "named_contact", "contact_title", "employee_estimate",
    "distress_signal", "financing_signal", "city", "source_url",
]


# ── Key extraction ──────────────────────────────────────────────────────

def _domain_key(lead: Lead) -> str:
    """Extract normalized domain from website."""
    return extract_domain(lead.website)


def _phone_key(lead: Lead) -> str:
    """Normalize phone to 10 digits for dedup."""
    digits = re.sub(r"\D", "", lead.business_phone)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    return digits if len(digits) == 10 else ""


def _name_state_key(lead: Lead) -> str:
    """Normalize company_name + state as fallback key."""
    name = re.sub(r"[^a-z0-9]", "", lead.company_name.lower())
    state = lead.state.strip().upper()
    if name and state:
        return f"{name}|{state}"
    return ""


# ── Strength comparison ─────────────────────────────────────────────────

def _field_count(lead: Lead) -> int:
    """Count non-empty fields for tiebreaking."""
    count = 0
    for field in _TIEBREAK_FIELDS:
        val = getattr(lead, field, None)
        if val is not None and (not isinstance(val, str) or val.strip()):
            count += 1
    return count


def _is_stronger(candidate: Lead, existing: Lead) -> bool:
    """Return True if candidate should replace existing."""
    c_tier = _TIER_RANK.get(candidate.quality_tier.value, 9)
    e_tier = _TIER_RANK.get(existing.quality_tier.value, 9)

    if c_tier != e_tier:
        return c_tier < e_tier

    if candidate.confidence_score != existing.confidence_score:
        return candidate.confidence_score > existing.confidence_score

    return _field_count(candidate) > _field_count(existing)


# ── Index management ────────────────────────────────────────────────────

def _register(lead: Lead, idx: int,
              by_domain: dict[str, int],
              by_phone: dict[str, int],
              by_name_state: dict[str, int]) -> None:
    """Register all of a lead's keys in the lookup indices."""
    domain = _domain_key(lead)
    phone = _phone_key(lead)
    ns = _name_state_key(lead)
    if domain:
        by_domain[domain] = idx
    if phone:
        by_phone[phone] = idx
    if ns:
        by_name_state[ns] = idx


def _unregister(lead: Lead, idx: int,
                by_domain: dict[str, int],
                by_phone: dict[str, int],
                by_name_state: dict[str, int]) -> None:
    """Remove a lead's keys from the lookup indices."""
    domain = _domain_key(lead)
    phone = _phone_key(lead)
    ns = _name_state_key(lead)
    if domain and by_domain.get(domain) == idx:
        del by_domain[domain]
    if phone and by_phone.get(phone) == idx:
        del by_phone[phone]
    if ns and by_name_state.get(ns) == idx:
        del by_name_state[ns]


# ── Public API ──────────────────────────────────────────────────────────

def deduplicate(leads: list[Lead]) -> list[Lead]:
    """Remove duplicates using multi-key matching.

    Checks domain → phone → name+state in priority order.
    On collision, keeps the stronger lead.
    """
    by_domain: dict[str, int] = {}
    by_phone: dict[str, int] = {}
    by_name_state: dict[str, int] = {}
    unique: list[Lead] = []

    for lead in leads:
        domain = _domain_key(lead)
        phone = _phone_key(lead)
        ns = _name_state_key(lead)

        # Check for collision in priority order
        match_idx: int | None = None
        match_key_type = ""
        if domain and domain in by_domain:
            match_idx = by_domain[domain]
            match_key_type = "domain"
        elif phone and phone in by_phone:
            match_idx = by_phone[phone]
            match_key_type = "phone"
        elif ns and ns in by_name_state:
            match_idx = by_name_state[ns]
            match_key_type = "name+state"

        if match_idx is not None:
            existing = unique[match_idx]
            if _is_stronger(lead, existing):
                logger.info(
                    "Dedupe: replacing '%s' with stronger '%s' (matched on %s)",
                    existing.company_name, lead.company_name, match_key_type,
                )
                _unregister(existing, match_idx, by_domain, by_phone, by_name_state)
                unique[match_idx] = lead
                _register(lead, match_idx, by_domain, by_phone, by_name_state)
            else:
                logger.info(
                    "Dedupe: discarding '%s' — duplicate of '%s' (matched on %s)",
                    lead.company_name, existing.company_name, match_key_type,
                )
        else:
            idx = len(unique)
            unique.append(lead)
            _register(lead, idx, by_domain, by_phone, by_name_state)

    removed = len(leads) - len(unique)
    if removed:
        logger.info("Dedupe removed %d duplicate(s) from %d leads", removed, len(leads))
    return unique
