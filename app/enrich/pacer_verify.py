"""PACER case verification — deeper bankruptcy validation.

Uses the PACER Case Locator to verify bankruptcy cases discovered
by CourtListener. Adds richer case metadata (filing date, chapter,
case status, judge, trustee info) for higher confidence scoring.

PACER is a VERIFICATION layer behind CourtListener, not a lead source.
CourtListener discovers signals → PACER confirms and enriches case data.

Requirements:
- PACER account (register at https://pacer.uscourts.gov/)
- Set PACER_USERNAME and PACER_PASSWORD environment variables
- PACER charges $0.10 per page of search results
- Free for accounts under $30/quarter

Authentication flow:
1. POST to PACER login endpoint with credentials
2. Receive auth token (NextGen)
3. Use token for Case Locator API queries

Without credentials, this module gracefully skips verification.
"""

from __future__ import annotations

import logging
import os
import re
import time

import requests

from app.models import Lead

logger = logging.getLogger(__name__)

# PACER NextGen authentication
_LOGIN_URL = "https://pacer.login.uscourts.gov/services/cso-auth"
_CASE_LOCATOR_URL = "https://pcl.uscourts.gov/pcl-public-api/rest"

REQUEST_TIMEOUT = 20
POLITE_DELAY = 1.0  # conservative — PACER is paid

# Session-level auth token cache
_auth_token: str | None = None
_auth_failed: bool = False


def _get_credentials() -> tuple[str | None, str | None]:
    """Get PACER credentials from environment."""
    return (
        os.environ.get("PACER_USERNAME"),
        os.environ.get("PACER_PASSWORD"),
    )


def _authenticate() -> str | None:
    """Authenticate with PACER and return auth token.

    Returns None if credentials missing or auth fails.
    """
    global _auth_token, _auth_failed

    if _auth_failed:
        return None
    if _auth_token:
        return _auth_token

    username, password = _get_credentials()
    if not username or not password:
        logger.debug("PACER: credentials not configured, skipping verification")
        _auth_failed = True
        return None

    try:
        resp = requests.post(
            _LOGIN_URL,
            json={"loginId": username, "password": password},
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            timeout=REQUEST_TIMEOUT,
        )

        if resp.status_code != 200:
            logger.warning("PACER: authentication failed (HTTP %d)", resp.status_code)
            _auth_failed = True
            return None

        data = resp.json()
        token = data.get("nextGenCSO", data.get("loginResult", ""))
        if token:
            _auth_token = token
            logger.info("PACER: authenticated successfully")
            return token

        logger.warning("PACER: no auth token in response")
        _auth_failed = True
        return None

    except requests.RequestException as exc:
        logger.warning("PACER: authentication request failed: %s", exc)
        _auth_failed = True
        return None


def _extract_docket_number(lead: Lead) -> str:
    """Extract a docket number from lead notes/source_url for PACER lookup."""
    notes = lead.notes or ""
    # Look for pattern like "Docket 8:26-bk-01639" or "26-10371"
    match = re.search(r'Docket\s+([\d:]+[-\w]+)', notes)
    if match:
        return match.group(1)
    return ""


def _search_case(docket_number: str, token: str) -> dict | None:
    """Search PACER Case Locator for a specific docket.

    Returns case metadata dict or None if not found.
    """
    if not docket_number:
        return None

    try:
        resp = requests.get(
            f"{_CASE_LOCATOR_URL}/cases",
            params={
                "caseNumberFull": docket_number,
                "caseType": "bk",
            },
            headers={
                "Accept": "application/json",
                "X-NEXT-GEN-CSO": token,
            },
            timeout=REQUEST_TIMEOUT,
        )

        if resp.status_code == 401:
            logger.warning("PACER: auth expired during case search")
            return None
        if resp.status_code != 200:
            logger.debug("PACER: case search HTTP %d for %s", resp.status_code, docket_number)
            return None

        data = resp.json()
        cases = data.get("content", [])
        if cases:
            return cases[0]
        return None

    except requests.RequestException as exc:
        logger.debug("PACER case search failed: %s", exc)
        return None


def verify_case(lead: Lead) -> dict:
    """Verify a bankruptcy case via PACER.

    Returns:
    {
        "verified": bool,
        "case_status": str,     # open, closed, dismissed, etc.
        "chapter": str,         # 7, 11, 13
        "date_filed": str,
        "judge": str,
        "pacer_url": str,
    }
    """
    result = {
        "verified": False,
        "case_status": "",
        "chapter": "",
        "date_filed": "",
        "judge": "",
        "pacer_url": "",
    }

    token = _authenticate()
    if not token:
        return result

    docket_number = _extract_docket_number(lead)
    if not docket_number:
        return result

    case_data = _search_case(docket_number, token)
    if not case_data:
        return result

    result["verified"] = True
    result["case_status"] = case_data.get("caseStatus", "")
    result["chapter"] = str(case_data.get("chapter", ""))
    result["date_filed"] = case_data.get("dateFiled", "")
    result["judge"] = case_data.get("judgeName", "")

    court_id = case_data.get("courtId", "")
    case_id = case_data.get("caseId", "")
    if court_id and case_id:
        result["pacer_url"] = f"https://ecf.{court_id}.uscourts.gov/cgi-bin/DktRpt.pl?{case_id}"

    return result


def enrich_leads_pacer(leads: list[Lead]) -> list[Lead]:
    """Batch PACER case verification for bankruptcy leads.

    Only processes leads in the bankruptcy lane.
    Requires PACER_USERNAME and PACER_PASSWORD env vars.
    Gracefully skips if credentials not configured.
    """
    # Only verify bankruptcy leads
    bk_leads = [ld for ld in leads if ld.lead_lane.value == "bankruptcy"]
    if not bk_leads:
        return leads

    # Check authentication first (one call for whole batch)
    token = _authenticate()
    if not token:
        logger.info("PACER: skipping verification (credentials not configured)")
        return leads

    logger.info("PACER: verifying %d bankruptcy leads", len(bk_leads))

    verified_count = 0
    for lead in bk_leads:
        result = verify_case(lead)

        if result["verified"]:
            verified_count += 1
            parts = [f"PACER verified: status={result['case_status']}"]
            if result["chapter"]:
                parts.append(f"ch{result['chapter']}")
            if result["judge"]:
                parts.append(f"judge={result['judge']}")
            if result["pacer_url"]:
                parts.append(result["pacer_url"])

            pacer_note = ", ".join(parts)
            if lead.notes:
                lead.notes = f"{lead.notes} | {pacer_note}"
            else:
                lead.notes = pacer_note

        time.sleep(POLITE_DELAY)

    logger.info("PACER complete: %d/%d cases verified", verified_count, len(bk_leads))
    return leads
