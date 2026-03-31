"""Company type filter — screens leads by industry category.

Applies keyword matching against company_name, notes, reason_qualified,
and portfolio_type to classify companies by what they do. Used to narrow
a run to only a specific class of business (e.g. credit extenders).

To add a new category, add an entry to COMPANY_TYPE_KEYWORDS.
Each entry is a list of lowercase substrings to match (any match = pass).
"""

from __future__ import annotations

import re
import logging

from app.models import Lead

logger = logging.getLogger(__name__)

# ── Category definitions ────────────────────────────────────────────────
#
# Keys are the filter tokens users pass (e.g. "credit_extenders").
# Values are (name_keywords, text_keywords):
#   name_keywords  — checked against company_name (word-boundary match)
#   text_keywords  — checked against notes + reason_qualified + portfolio_type
#                    (substring match, broader)
#
# A lead passes if ANY keyword in EITHER list hits.

COMPANY_TYPE_KEYWORDS: dict[str, tuple[list[str], list[str]]] = {
    "credit_extenders": (
        # Company name word-boundary patterns — kept specific to avoid false positives
        [
            r"\bbank\b", r"\bbanking\b", r"\bbankers?\b", r"\bbankcorp\b",
            r"\bcredit union\b", r"\bfcu\b",
            r"\blending\b", r"\blender\b",
            r"\bloans?\b",
            r"\bfinancial\b", r"\bfinance\b",
            r"\bmortgage\b",
            r"\bsavings\b", r"\bthrift\b",
            r"\bacceptance\b",            # common in auto finance (Westlake Acceptance)
            r"\bcapital finance\b", r"\bcapital bank\b", r"\bcapital credit\b",
            r"\bfactoring\b",
            r"\binstallment\b",
            r"\bauto finance\b", r"\bauto credit\b", r"\bauto loan\b",
            r"\btitle loan\b", r"\bpayday\b",
            r"\bservicing\b",             # loan servicers
            r"\bdebt\b",                  # debt buyers/collectors
            r"\bcollections?\b",
            r"\bnational association\b",  # national banks (full name)
            r"\bN\.?B\.?\b",             # NB / N.B. = National Bank abbreviation
            r"\bconsumer finance\b", r"\bconsumer credit\b",
            r"\bportfolio recovery\b", r"\bportfolio management\b",
        ],
        # Notes / reason / portfolio_type substring patterns (broader — context is cleaner)
        [
            "bank failure",
            "charged_off", "charged off",
            "auto deficiency", "title_loan", "consumer_paper",
            "debt collection", "vehicle loan", "consumer loan",
            "payday", "installment",
            "fdic cert",                  # always a bank
        ],
    ),
    "auto_dealers": (
        [
            r"\bauto\b",                  # Auto Sales, Auto Group, Auto Center
            r"\bautomotive\b",
            r"\bdealer\b", r"\bdealership\b",
            r"\bcars?\b",                 # Cars LLC, Car Group
            r"\btruck\b", r"\btrucks\b",
            r"\bbhph\b",                  # buy here pay here
            r"\bmotors?\b",               # ABC Motors
            r"\bauto sales\b",            # very common BHPH pattern
            r"\bused car\b", r"\bused cars\b",
            r"\bpre.?owned\b",            # pre-owned / preowned
            r"\bcar lot\b",
            r"\bvehicle\b",               # Vehicle Sales, Vehicle Group
            r"\bford\b", r"\bchevrolet\b", r"\btoyota\b",
            r"\bhonda\b", r"\bnissan\b", r"\bdodge\b",
        ],
        ["vehicle loan", "auto deficiency", "repossession", "auto dealer"],
    ),
    "real_estate": (
        [
            r"\bmortgage\b",
            r"\brealty\b", r"\breal estate\b",
            r"\bproperties\b", r"\bproperty\b",
            r"\bhomes?\b", r"\bhousing\b",
            r"\breit\b",
        ],
        ["mortgage", "foreclosure", "real estate"],
    ),
    "healthcare": (
        [
            r"\bhealth\b", r"\bhealthcare\b",
            r"\bmedical\b", r"\bclinic\b",
            r"\bhospital\b", r"\bphysician\b",
            r"\bdental\b", r"\btherapy\b",
            r"\bpharmacy\b",
        ],
        ["medical debt", "healthcare"],
    ),
}

# ── Compiled patterns cache ─────────────────────────────────────────────

_compiled: dict[str, tuple[list[re.Pattern], list[str]]] = {}


def _get_patterns(category: str) -> tuple[list[re.Pattern], list[str]]:
    """Return compiled regex patterns for a category (cached)."""
    if category not in _compiled:
        name_raw, text_raw = COMPANY_TYPE_KEYWORDS[category]
        _compiled[category] = (
            [re.compile(p, re.IGNORECASE) for p in name_raw],
            [t.lower() for t in text_raw],
        )
    return _compiled[category]


# ── Public API ──────────────────────────────────────────────────────────

def matches_company_type(lead: Lead, category: str) -> bool:
    """Return True if a lead matches the given company type category."""
    if category not in COMPANY_TYPE_KEYWORDS:
        logger.warning("Unknown company type category: '%s' — skipping filter", category)
        return True  # Unknown category = don't filter out

    name_patterns, text_keywords = _get_patterns(category)

    # Check company name with word-boundary patterns
    for pat in name_patterns:
        if pat.search(lead.company_name):
            return True

    # Check text fields with substring patterns
    # Normalize underscores to spaces so "auto_deficiency" matches "auto deficiency"
    text = " ".join(filter(None, [
        lead.notes,
        lead.reason_qualified,
        (lead.portfolio_type or "").replace("_", " "),
        lead.distress_signal or "",
    ])).lower()

    for kw in text_keywords:
        if kw in text:
            return True

    return False


def apply_company_type_filter(
    leads: list[Lead],
    company_types: list[str],
) -> tuple[list[Lead], list[Lead]]:
    """Filter leads to only those matching ANY of the given company type categories.

    Returns (kept_leads, rejected_leads).
    If company_types is empty, returns all leads unchanged with empty rejected list.
    """
    if not company_types:
        return leads, []

    kept: list[Lead] = []
    rejected: list[Lead] = []

    for lead in leads:
        if any(matches_company_type(lead, ct) for ct in company_types):
            kept.append(lead)
        else:
            rejected.append(lead)

    if rejected:
        logger.info(
            "Company type filter %s: kept %d, rejected %d",
            company_types, len(kept), len(rejected),
        )

    return kept, rejected
