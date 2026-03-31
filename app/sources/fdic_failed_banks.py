"""FDIC Failed Banks collector — discovers banks with liquidated loan portfolios.

Uses the FDIC BankFind Suite API to find recently failed banks. When a bank
fails, the FDIC liquidates its assets including charged-off loan portfolios,
which are often sold to debt buyers at discount.

API docs: https://banks.data.fdic.gov/docs/
No API key required.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://banks.data.fdic.gov/api/failures"
REQUEST_TIMEOUT = 30

# Bank failures are rare events — use a long minimum lookback so the
# collector isn't empty during quiet periods.
MIN_LOOKBACK_DAYS = 730  # 2 years

# States excluded for the charged-off lane (from rules)
_EXCLUDED_STATES = {"TX", "NC", "SC", "PA", "AZ", "CA"}


def _parse_fdic_date(date_str: str) -> str:
    """Convert FDIC date format (M/DD/YYYY) to ISO-ish YYYY-MM-DD."""
    try:
        dt = datetime.strptime(date_str.strip(), "%m/%d/%Y")
        return dt.strftime("%Y-%m-%d")
    except (ValueError, AttributeError):
        return date_str


def collect_fdic_failed_banks(
    lane: str, limit: int | None = None, filters=None,
) -> list[dict]:
    """Collect charged-off leads from FDIC failed bank data.

    Only fires for the charged_off lane.
    Failed banks = forced portfolio liquidation = charged-off paper available.
    Returns raw signal dicts for the pipeline to normalize/enrich/score.
    """
    from app.models import SearchFilters

    if filters is None:
        filters = SearchFilters()

    if lane != "charged_off":
        return []

    # Bank failures are rare — enforce a minimum lookback window
    effective_lookback = max(filters.lookback_days, MIN_LOOKBACK_DAYS)
    since = (datetime.utcnow() - timedelta(days=effective_lookback)).strftime("%Y-%m-%d")

    # FDIC API: no date filter needed — we fetch recent failures sorted by
    # date and filter client-side. The API's date filter uses M/DD/YYYY
    # format which is fragile, so we just sort descending and take what we need.
    params = {
        "sort_by": "FAILDATE",
        "sort_order": "DESC",
        "limit": min(limit or 100, 100),
        "offset": 0,
    }

    try:
        logger.info("FDIC: searching failed banks (last %d days)", effective_lookback)
        resp = requests.get(BASE_URL, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except requests.RequestException as exc:
        logger.error("FDIC API failed: %s", exc)
        return []

    cutoff = datetime.utcnow() - timedelta(days=effective_lookback)
    results: list[dict] = []

    for entry in data.get("data", []):
        row = entry.get("data", {})

        # Field mapping: NAME = bank name, PSTALP = state, CITY = city
        bank_name = (row.get("NAME") or "").strip()
        if not bank_name:
            continue

        state = (row.get("PSTALP") or "").strip().upper()
        if state in _EXCLUDED_STATES:
            continue

        # Parse and check date
        raw_date = row.get("FAILDATE", "")
        fail_date = _parse_fdic_date(raw_date)
        try:
            dt = datetime.strptime(raw_date.strip(), "%m/%d/%Y")
            if dt < cutoff:
                # Past our lookback window — since results are sorted desc, stop
                break
        except (ValueError, AttributeError):
            pass

        city = (row.get("CITY") or "").strip()
        cert = row.get("CERT", "")
        cost = row.get("COST")
        resolution = row.get("RESTYPE1") or row.get("RESTYPE") or ""
        acquiring = (row.get("BIDNAME") or "").strip()
        assets = row.get("QBFASSET")

        notes_parts = [f"FDIC Cert #{cert}"]
        if resolution:
            notes_parts.append(f"Resolution: {resolution}")
        if acquiring:
            notes_parts.append(f"Acquired by: {acquiring}")
        if cost:
            notes_parts.append(f"Est. cost: ${cost:,}K")
        if assets:
            notes_parts.append(f"Total assets: ${assets:,}K")

        results.append({
            "company_name": bank_name,
            "state": state,
            "city": city,
            "portfolio_type": "charged_off_bank_failure",
            "reason_qualified": (
                f"FDIC bank failure on {fail_date} — "
                "loan portfolios being liquidated"
            ),
            "source_url": "https://www.fdic.gov/resources/resolutions/bank-failures/failed-bank-list/",
            "notes": ". ".join(notes_parts),
            "distress_signal": f"Bank failure ({fail_date})",
            "private_company_confirmed": True,
        })

        if limit and len(results) >= limit:
            break

    if results:
        logger.info("FDIC: found %d failed bank signals", len(results))
    else:
        logger.info(
            "FDIC: no recent bank failures found (lookback %d days)",
            effective_lookback,
        )

    return results
