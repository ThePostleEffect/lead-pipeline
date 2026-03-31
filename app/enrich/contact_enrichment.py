"""Contact enrichment — title normalization and basic validation."""

from __future__ import annotations

import logging
import re

from app.models import Lead

logger = logging.getLogger(__name__)

# ── Title normalization ─────────────────────────────────────────────────

# Abbreviation → full title (exact match, case-insensitive)
_TITLE_EXPANSIONS: dict[str, str] = {
    "vp": "Vice President",
    "svp": "Senior Vice President",
    "evp": "Executive Vice President",
    "avp": "Assistant Vice President",
    "ceo": "Chief Executive Officer",
    "cfo": "Chief Financial Officer",
    "coo": "Chief Operating Officer",
    "cto": "Chief Technology Officer",
    "cio": "Chief Investment Officer",
    "cmo": "Chief Marketing Officer",
    "cro": "Chief Revenue Officer",
    "dir": "Director",
    "mgr": "Manager",
    "pres": "President",
    "gm": "General Manager",
    "md": "Managing Director",
}

# Prefix abbreviations to expand within a longer title
_PREFIX_EXPANSIONS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"\bVP\b"), "Vice President"),
    (re.compile(r"\bSVP\b"), "Senior Vice President"),
    (re.compile(r"\bEVP\b"), "Executive Vice President"),
    (re.compile(r"\bAVP\b"), "Assistant Vice President"),
    (re.compile(r"\bDir\b\.?", re.IGNORECASE), "Director"),
    (re.compile(r"\bMgr\b\.?", re.IGNORECASE), "Manager"),
    (re.compile(r"\bGM\b"), "General Manager"),
]


def _normalize_title(title: str) -> str:
    """Normalize a contact title — expand abbreviations, clean whitespace."""
    stripped = title.strip()
    if not stripped:
        return ""

    # Exact abbreviation match
    lower = stripped.lower()
    if lower in _TITLE_EXPANSIONS:
        return _TITLE_EXPANSIONS[lower]

    # Expand abbreviation prefixes within compound titles (e.g. "VP of Sales")
    result = stripped
    for pattern, expansion in _PREFIX_EXPANSIONS:
        result = pattern.sub(expansion, result)

    # Clean up extra whitespace
    result = re.sub(r"\s+", " ", result).strip()
    return result


# ── Contact name cleaning ───────────────────────────────────────────────

def _clean_contact_name(name: str) -> str:
    """Basic name cleaning — strip whitespace, normalize spacing."""
    cleaned = re.sub(r"\s+", " ", name.strip())
    # Title-case if all-upper or all-lower
    if cleaned.isupper() or cleaned.islower():
        cleaned = cleaned.title()
    return cleaned


# ── Public API ──────────────────────────────────────────────────────────

def enrich_contact(lead: Lead) -> Lead:
    """Enrich a single lead with contact-level normalization."""
    if lead.named_contact:
        lead.named_contact = _clean_contact_name(lead.named_contact)

    if lead.contact_title:
        lead.contact_title = _normalize_title(lead.contact_title)

    return lead


def enrich_contacts(leads: list[Lead]) -> list[Lead]:
    """Batch-enrich a list of leads with contact normalization."""
    enriched = [enrich_contact(ld) for ld in leads]
    logger.info("Contact enrichment complete for %d leads", len(enriched))
    return enriched
