"""Company enrichment — heuristic-based enrichment from available fields.

Works without external APIs. Enriches leads by analyzing text fields for:
- public company indicators
- distress signals
- financing signals
- website validation
"""

from __future__ import annotations

import logging
import re

from app.models import Lead
from app.utils.urls import normalize_url

logger = logging.getLogger(__name__)

# ── Public company detection ────────────────────────────────────────────

_PUBLIC_INDICATORS: list[str] = [
    "nyse", "nasdaq", "publicly traded", "publicly listed",
    "stock ticker", "listed on", "market cap", "sec filing",
    "10-k", "10-q", "annual report filed", "exchange listed",
    "ticker symbol", "stock exchange",
]

_PUBLIC_NAME_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b[A-Z]{1,5}\b.*\b(NYSE|NASDAQ)\b", re.IGNORECASE),
]


def _detect_public_company(lead: Lead) -> bool:
    """Heuristic: detect likely public companies from text fields."""
    if lead.public_company_confirmed:
        return True

    text = f"{lead.company_name} {lead.notes} {lead.reason_qualified}".lower()
    if any(re.search(r"\b" + re.escape(ind) + r"\b", text) for ind in _PUBLIC_INDICATORS):
        return True

    full_text = f"{lead.company_name} {lead.notes} {lead.reason_qualified}"
    for pattern in _PUBLIC_NAME_PATTERNS:
        if pattern.search(full_text):
            return True

    return False


# ── Distress signal detection ───────────────────────────────────────────

_DISTRESS_KEYWORDS: dict[str, str] = {
    "chapter 7": "Chapter 7 bankruptcy filing",
    "chapter 11": "Chapter 11 restructuring",
    "chapter 13": "Chapter 13 bankruptcy filing",
    "foreclosure": "Foreclosure proceedings",
    "loan default": "Loan default",
    "defaulted": "Defaulted obligation",
    "delinquent": "Delinquent payments",
    "charged off": "Charged-off debt",
    "charged-off": "Charged-off debt",
    "liquidation": "Asset liquidation",
    "receivership": "Receivership",
    "distressed": "Distressed assets",
    "insolvency": "Insolvency",
    "insolvent": "Insolvent entity",
    "winding down": "Winding down operations",
    "creditor": "Creditor action",
    "judgment": "Judgment or lien",
    "lien": "Lien filed",
}


def _detect_distress(lead: Lead) -> str:
    """Extract distress signals from text fields using word-boundary matching."""
    text = f"{lead.notes} {lead.reason_qualified}".lower()
    found = [
        desc for keyword, desc in _DISTRESS_KEYWORDS.items()
        if re.search(r"\b" + re.escape(keyword) + r"\b", text)
    ]
    return "; ".join(sorted(set(found))) if found else ""


# ── Financing signal detection ──────────────────────────────────────────

_FINANCING_KEYWORDS: dict[str, str] = {
    "bridge loan": "Seeking bridge loan",
    "bridge funding": "Seeking bridge funding",
    "working capital": "Needs working capital",
    "line of credit": "Seeking line of credit",
    "revolving line": "Seeking revolving credit line",
    "inventory financing": "Needs inventory financing",
    "capital raise": "Capital raise in progress",
    "seeking funding": "Actively seeking funding",
    "seeking capital": "Actively seeking capital",
    "operating capital": "Needs operating capital",
    "credit facility": "Seeking credit facility",
    "term loan": "Seeking term loan",
    "mezzanine": "Seeking mezzanine financing",
    "factoring": "Seeking accounts receivable factoring",
    "asset-based": "Seeking asset-based lending",
    "asset based": "Seeking asset-based lending",
}


def _detect_financing(lead: Lead) -> str:
    """Extract financing signals from text fields using word-boundary matching."""
    text = f"{lead.notes} {lead.reason_qualified}".lower()
    found = [
        desc for keyword, desc in _FINANCING_KEYWORDS.items()
        if re.search(r"\b" + re.escape(keyword) + r"\b", text)
    ]
    return "; ".join(sorted(set(found))) if found else ""


# ── Private company confirmation ────────────────────────────────────────

def _infer_private(lead: Lead) -> bool:
    """If neither confirmed, assume private unless public indicators found."""
    if lead.private_company_confirmed:
        return True
    if lead.public_company_confirmed:
        return False
    # No explicit flag — infer private if no public indicators
    return not _detect_public_company(lead)


# ── Public API ──────────────────────────────────────────────────────────

def enrich_company(lead: Lead) -> Lead:
    """Enrich a single lead with company-level data from available fields."""

    # Normalize website
    if lead.website:
        lead.website = normalize_url(lead.website)

    # Public company detection
    if _detect_public_company(lead):
        lead.public_company_confirmed = True
        lead.private_company_confirmed = False
    elif not lead.private_company_confirmed and not lead.public_company_confirmed:
        lead.private_company_confirmed = _infer_private(lead)

    # Distress signal enrichment (don't overwrite explicit signals)
    if not lead.distress_signal:
        detected = _detect_distress(lead)
        if detected:
            lead.distress_signal = detected
            logger.debug("Distress signal detected for %s: %s", lead.company_name, detected)

    # Financing signal enrichment (don't overwrite explicit signals)
    if not lead.financing_signal:
        detected = _detect_financing(lead)
        if detected:
            lead.financing_signal = detected
            logger.debug("Financing signal detected for %s: %s", lead.company_name, detected)

    return lead


def enrich_companies(leads: list[Lead]) -> list[Lead]:
    """Batch-enrich a list of leads with company-level data."""
    enriched = [enrich_company(ld) for ld in leads]
    logger.info("Company enrichment complete for %d leads", len(enriched))
    return enriched
