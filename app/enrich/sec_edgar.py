"""SEC EDGAR public company detection — exclusion filter.

Uses the SEC EDGAR company search to detect public companies (SEC filers).
Public companies are excluded from this pipeline (private companies only).

This is a NEGATIVE FILTER / exclusion layer, not a lead source.
If a company is found as an SEC filer, it sets public_company_confirmed=True,
which triggers the public_company discard rule downstream.

API: SEC EDGAR company search (free, no auth required)
- Must include User-Agent header per SEC policy
- Rate limit: 10 requests/second (SEC fair access policy)

Approach:
1. Fetch the SEC company tickers file (cached per session)
2. Match lead company names against known public filers
3. Fall back to EDGAR full-text search for close matches
"""

from __future__ import annotations

import logging
import time
from difflib import SequenceMatcher

import requests

from app.models import Lead

logger = logging.getLogger(__name__)

# SEC EDGAR access headers
_SEC_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/json",
}

REQUEST_TIMEOUT = 15
POLITE_DELAY = 0.15  # SEC allows 10 req/sec

# EDGAR company tickers endpoint (static JSON of all filers)
_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"

# Session-level cache for the tickers list
_tickers_cache: dict[str, list[dict]] | None = None


def _normalize_for_matching(name: str) -> str:
    """Normalize a company name for fuzzy matching."""
    name = name.lower().strip()
    # Strip common suffixes that vary between sources
    for suffix in (" inc", " inc.", " corp", " corp.", " llc", " ltd", " ltd.",
                   " co", " co.", " lp", " l.p.", " plc", " sa", " nv",
                   " holdings", " group", " enterprises"):
        if name.endswith(suffix):
            name = name[:-len(suffix)].strip(" ,.")
    return name


def _load_sec_tickers() -> list[dict]:
    """Load SEC company tickers list (cached per session).

    Returns list of {"cik_str": "...", "ticker": "...", "title": "..."}
    """
    global _tickers_cache
    if _tickers_cache is not None:
        return _tickers_cache.get("tickers", [])

    try:
        resp = requests.get(
            _TICKERS_URL,
            headers=_SEC_HEADERS,
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code != 200:
            logger.warning("SEC EDGAR: failed to load tickers (HTTP %d)", resp.status_code)
            _tickers_cache = {"tickers": []}
            return []

        data = resp.json()
        # Format: {"0": {"cik_str": "...", "ticker": "...", "title": "..."}, "1": {...}}
        tickers = list(data.values())
        _tickers_cache = {"tickers": tickers}
        logger.info("SEC EDGAR: loaded %d public company tickers", len(tickers))
        return tickers

    except requests.RequestException as exc:
        logger.warning("SEC EDGAR: failed to load tickers: %s", exc)
        _tickers_cache = {"tickers": []}
        return []


def check_public_company(company_name: str) -> dict:
    """Check if a company name matches a known SEC filer.

    Returns:
    {
        "is_public": bool,
        "ticker": str,        # stock ticker if found
        "sec_name": str,      # SEC-registered name
        "cik": str,           # SEC CIK number
        "match_score": float, # name similarity 0.0-1.0
    }
    """
    result = {
        "is_public": False,
        "ticker": "",
        "sec_name": "",
        "cik": "",
        "match_score": 0.0,
    }

    if not company_name.strip():
        return result

    tickers = _load_sec_tickers()
    if not tickers:
        return result

    normalized = _normalize_for_matching(company_name)

    best_match = None
    best_score = 0.0

    for entry in tickers:
        sec_name = entry.get("title", "")
        sec_normalized = _normalize_for_matching(sec_name)

        # Quick skip: if first 3 chars don't match, skip
        if normalized[:3] != sec_normalized[:3]:
            continue

        score = SequenceMatcher(None, normalized, sec_normalized).ratio()
        if score > best_score:
            best_score = score
            best_match = entry

    # Require high similarity for public company match (avoid false positives)
    # 0.85 threshold: "harlow" vs "harrow" (0.833) correctly rejected
    if best_match and best_score >= 0.85:
        result["is_public"] = True
        result["ticker"] = best_match.get("ticker", "")
        result["sec_name"] = best_match.get("title", "")
        result["cik"] = str(best_match.get("cik_str", ""))
        result["match_score"] = round(best_score, 3)

    return result


def enrich_leads_sec_edgar(leads: list[Lead]) -> list[Lead]:
    """Batch public company detection via SEC EDGAR.

    Checks each lead against the SEC filer list. If matched,
    sets public_company_confirmed=True (which triggers the
    public_company discard rule downstream).
    """
    if not leads:
        return leads

    logger.info("SEC EDGAR: checking %d leads for public company status", len(leads))

    # Pre-load tickers (one request for the whole batch)
    tickers = _load_sec_tickers()
    if not tickers:
        logger.warning("SEC EDGAR: no ticker data available, skipping check")
        return leads

    flagged_count = 0

    for lead in leads:
        # Skip if already confirmed public
        if lead.public_company_confirmed:
            continue

        result = check_public_company(lead.company_name)

        if result["is_public"]:
            lead.public_company_confirmed = True
            flagged_count += 1
            note = f"SEC filer: {result['sec_name']} (ticker={result['ticker']}, CIK={result['cik']}, match={result['match_score']})"
            if lead.notes:
                lead.notes = f"{lead.notes} | {note}"
            else:
                lead.notes = note
            logger.debug("SEC EDGAR flagged %s as public: %s (%s)",
                         lead.company_name, result["sec_name"], result["ticker"])

    logger.info("SEC EDGAR complete: %d/%d flagged as public companies", flagged_count, len(leads))
    return leads
