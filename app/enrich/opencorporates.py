"""OpenCorporates entity verification — confirm company identity.

Uses the free OpenCorporates API to:
- Verify a company name exists as a registered entity
- Confirm jurisdiction/state matches
- Flag inactive/dissolved companies
- Provide a legal name for better matching

This is a VERIFICATION layer, not a lead source. It improves confidence
in entity identity and reduces bad website/domain matches.

API: https://api.opencorporates.com/v0.4/companies/search
Free tier: no API key needed, rate limited (~5 req/sec).
Optional: set OPENCORPORATES_API_KEY for higher limits.
"""

from __future__ import annotations

import logging
import os
import time
from difflib import SequenceMatcher

import requests

from app.models import Lead

logger = logging.getLogger(__name__)

BASE_URL = "https://api.opencorporates.com/v0.4"
REQUEST_TIMEOUT = 15
POLITE_DELAY = 0.5
MIN_NAME_SIMILARITY = 0.55  # minimum name match ratio to consider a hit


def _get_api_key() -> str | None:
    return os.environ.get("OPENCORPORATES_API_KEY")


def _headers() -> dict[str, str]:
    return {"Accept": "application/json"}


def _state_to_jurisdiction(state: str) -> str:
    """Convert 2-letter state code to OpenCorporates jurisdiction code."""
    if state and len(state) == 2:
        return f"us_{state.lower()}"
    return ""


def _name_similarity(a: str, b: str) -> float:
    """Fuzzy match ratio between two company names (case-insensitive)."""
    return SequenceMatcher(None, a.lower().strip(), b.lower().strip()).ratio()


def _search_company(company_name: str, jurisdiction: str = "") -> list[dict]:
    """Search OpenCorporates for companies matching the name.

    Returns list of company result dicts from the API.
    Requires OPENCORPORATES_API_KEY env var (free accounts available).
    """
    api_key = _get_api_key()
    if not api_key:
        return []

    params: dict[str, str] = {"q": company_name, "api_token": api_key}
    if jurisdiction:
        params["jurisdiction_code"] = jurisdiction

    try:
        resp = requests.get(
            f"{BASE_URL}/companies/search",
            headers=_headers(),
            params=params,
            timeout=REQUEST_TIMEOUT,
        )

        if resp.status_code == 429:
            logger.warning("OpenCorporates: rate limited, backing off")
            time.sleep(2)
            return []
        if resp.status_code == 403:
            logger.warning("OpenCorporates: access denied (API key may be needed)")
            return []
        if resp.status_code != 200:
            logger.debug("OpenCorporates: HTTP %d for '%s'", resp.status_code, company_name)
            return []

        data = resp.json()
        companies = data.get("results", {}).get("companies", [])
        return [c.get("company", {}) for c in companies]

    except requests.RequestException as exc:
        logger.debug("OpenCorporates search failed: %s", exc)
        return []


def verify_entity(lead: Lead) -> dict:
    """Verify a lead's company against OpenCorporates.

    Returns a dict with verification results:
    {
        "verified": bool,       # entity found with good name match
        "legal_name": str,      # official registered name (if found)
        "jurisdiction": str,    # registered jurisdiction
        "status": str,          # Active, Dissolved, etc.
        "match_score": float,   # name similarity 0.0-1.0
        "opencorporates_url": str,
        "inactive": bool,       # True if dissolved/inactive
    }
    """
    result = {
        "verified": False,
        "legal_name": "",
        "jurisdiction": "",
        "status": "",
        "match_score": 0.0,
        "opencorporates_url": "",
        "inactive": False,
    }

    if not lead.company_name.strip():
        return result

    jurisdiction = _state_to_jurisdiction(lead.state)

    # Search with jurisdiction first (more precise)
    companies = _search_company(lead.company_name, jurisdiction)

    # If no results with jurisdiction, try without
    if not companies and jurisdiction:
        companies = _search_company(lead.company_name)

    if not companies:
        return result

    # Find best name match
    best_match = None
    best_score = 0.0

    for company in companies[:5]:  # check top 5 results
        name = company.get("name", "")
        score = _name_similarity(lead.company_name, name)
        if score > best_score:
            best_score = score
            best_match = company

    if not best_match or best_score < MIN_NAME_SIMILARITY:
        return result

    status = best_match.get("current_status", "").lower()
    result["verified"] = True
    result["legal_name"] = best_match.get("name", "")
    result["jurisdiction"] = best_match.get("jurisdiction_code", "")
    result["status"] = best_match.get("current_status", "")
    result["match_score"] = round(best_score, 3)
    result["opencorporates_url"] = best_match.get("opencorporates_url", "")
    result["inactive"] = status in ("dissolved", "inactive", "withdrawn", "revoked",
                                     "cancelled", "terminated", "suspended")

    return result


def enrich_leads_opencorporates(leads: list[Lead]) -> list[Lead]:
    """Batch entity verification via OpenCorporates.

    Adds verification data to lead notes. Does NOT change company_name
    or other core fields — this is verification only.
    """
    if not leads:
        return leads

    if not _get_api_key():
        logger.info("OpenCorporates: OPENCORPORATES_API_KEY not set, skipping verification")
        return leads

    logger.info("OpenCorporates: verifying %d leads", len(leads))

    verified_count = 0
    inactive_count = 0

    for i, lead in enumerate(leads):
        result = verify_entity(lead)

        if result["verified"]:
            verified_count += 1
            parts = [f"OC verified: {result['legal_name']}"]
            if result["status"]:
                parts.append(f"status={result['status']}")
            if result["opencorporates_url"]:
                parts.append(result["opencorporates_url"])

            oc_note = " | ".join(parts)
            if lead.notes:
                lead.notes = f"{lead.notes} | {oc_note}"
            else:
                lead.notes = oc_note

            if result["inactive"]:
                inactive_count += 1

        if (i + 1) % 10 == 0:
            logger.info("OpenCorporates progress: %d/%d checked, %d verified",
                        i + 1, len(leads), verified_count)

        time.sleep(POLITE_DELAY)

    logger.info(
        "OpenCorporates complete: %d/%d verified, %d flagged inactive",
        verified_count, len(leads), inactive_count,
    )

    return leads
