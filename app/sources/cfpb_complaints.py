"""CFPB Consumer Complaint collector — discovers distressed lenders/servicers.

Uses the CFPB Consumer Complaints API to find companies with high complaint
volumes in debt-related product categories. High complaint counts signal
operational or financial distress, often correlated with elevated charge-off
rates and potential portfolio sales.

Relevant charged-off subtypes surfaced:
  - Auto deficiency balances (Vehicle loan complaints)
  - Title-loan paper (Payday/title loan complaints)
  - Retail installment / consumer paper (Consumer loan complaints)
  - General charged-off debt (Debt collection complaints)

API docs: https://www.consumerfinance.gov/data-research/consumer-complaints/
No API key required.
"""

from __future__ import annotations

import logging
import time
from collections import Counter
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://www.consumerfinance.gov/data-research/consumer-complaints/search/api/v1/"
REQUEST_TIMEOUT = 30
POLITE_DELAY = 0.5  # seconds between product queries

# Complaint history is sparse at short windows — enforce a minimum lookback
# so aggregation is meaningful even when the user sets lookback_days=30.
MIN_LOOKBACK_DAYS = 90

# Minimum complaints to flag a company as a lead signal
MIN_COMPLAINT_THRESHOLD = 3

# Product categories relevant to charged-off debt
_RELEVANT_PRODUCTS = [
    "Debt collection",
    "Credit card or prepaid card",
    "Vehicle loan or lease",
    "Consumer Loan",
    "Payday loan, title loan, or personal loan",
]

# States excluded for the charged-off lane
_EXCLUDED_STATES = {"TX", "NC", "SC", "PA", "AZ", "CA"}

# Giant national banks / CRAs — too large to be actionable leads
_SKIP_COMPANIES = {
    "EQUIFAX", "EQUIFAX, INC.",
    "EXPERIAN", "EXPERIAN INFORMATION SOLUTIONS INC.",
    "TRANSUNION", "TRANSUNION INTERMEDIATE HOLDINGS, INC.",
    "BANK OF AMERICA", "BANK OF AMERICA, NATIONAL ASSOCIATION",
    "JPMORGAN CHASE", "JPMORGAN CHASE & CO.",
    "WELLS FARGO", "WELLS FARGO & COMPANY",
    "CITIBANK", "CITIBANK, N.A.",
    "CAPITAL ONE", "CAPITAL ONE FINANCIAL CORPORATION",
    "DISCOVER", "DISCOVER BANK",
    "U.S. BANCORP", "PNC BANK, N.A.", "PNC FINANCIAL SERVICES GROUP, INC.",
    "TRUIST FINANCIAL CORPORATION",
    "SYNCHRONY FINANCIAL",
    "ALLY FINANCIAL INC.",
    "AMERICAN EXPRESS COMPANY",
    "NAVY FEDERAL CREDIT UNION",
}


def _should_skip(company: str) -> bool:
    """Check if a company is on the skip list (case-insensitive)."""
    return company.strip().upper() in _SKIP_COMPANIES


def _portfolio_subtype(products: list[str]) -> str:
    """Infer charged-off portfolio subtype from complaint products."""
    product_lower = {p.lower() for p in products}
    if any("vehicle" in p for p in product_lower):
        return "auto_deficiency"
    if any("payday" in p or "title" in p for p in product_lower):
        return "title_loan"
    if any("credit card" in p for p in product_lower):
        return "consumer_paper"
    return "charged_off_general"


def collect_cfpb_complaints(
    lane: str, limit: int | None = None, filters=None,
) -> list[dict]:
    """Collect charged-off leads from CFPB complaint data.

    Only fires for the charged_off lane.
    High complaint volumes in debt-related products = distressed company signal.
    Returns raw signal dicts for the pipeline to normalize/enrich/score.
    """
    from app.models import SearchFilters

    if filters is None:
        filters = SearchFilters()

    if lane != "charged_off":
        return []

    lookback = max(filters.lookback_days, MIN_LOOKBACK_DAYS)
    since = (datetime.utcnow() - timedelta(days=lookback)).strftime("%Y-%m-%d")

    # Fetch complaints across relevant product categories
    all_complaints: list[dict] = []

    for product in _RELEVANT_PRODUCTS:
        params = {
            "product": product,
            "date_received_min": since,
            "size": 500,
            "sort": "created_date_desc",
            "no_aggs": "true",
        }

        try:
            logger.debug("CFPB: querying product='%s' since %s", product, since)
            resp = requests.get(
                BASE_URL, params=params, timeout=REQUEST_TIMEOUT,
                headers={"Accept": "application/json"},
            )

            if resp.status_code == 429:
                logger.warning("CFPB: rate limited, skipping remaining products")
                break

            resp.raise_for_status()
            data = resp.json()

            hits = data.get("hits", {}).get("hits", [])
            for hit in hits:
                source = hit.get("_source", {})
                all_complaints.append(source)

            logger.debug(
                "CFPB: %d complaints for product='%s'",
                len(hits), product,
            )

        except requests.RequestException as exc:
            logger.error("CFPB query failed for product '%s': %s", product, exc)
            continue

        time.sleep(POLITE_DELAY)

    if not all_complaints:
        logger.info("CFPB: no complaints found (lookback %d days)", lookback)
        return []

    logger.info("CFPB: fetched %d total complaints, aggregating by company", len(all_complaints))

    # Aggregate by company
    company_data: dict[str, list[dict]] = {}
    for complaint in all_complaints:
        company = complaint.get("company", "").strip()
        if not company or _should_skip(company):
            continue
        company_data.setdefault(company, []).append(complaint)

    # Rank by complaint count (most = strongest distress signal)
    ranked = sorted(company_data.items(), key=lambda x: len(x[1]), reverse=True)

    results: list[dict] = []
    for company_name, complaints in ranked:
        count = len(complaints)
        if count < MIN_COMPLAINT_THRESHOLD:
            continue

        # Primary state = most common state in complaints for this company
        states = [c.get("state", "") for c in complaints if c.get("state")]
        primary_state = Counter(states).most_common(1)[0][0] if states else ""

        if primary_state in _EXCLUDED_STATES:
            continue

        # Determine portfolio subtype from complaint products
        products = [c.get("product", "") for c in complaints]
        subtype = _portfolio_subtype(products)

        # Top complaint issues for notes
        issues = Counter(
            c.get("issue", "") for c in complaints if c.get("issue")
        ).most_common(2)
        issue_note = "; ".join(f"{iss} ({cnt})" for iss, cnt in issues)

        # URL-safe company name for CFPB search link
        company_query = company_name.replace(" ", "+")

        results.append({
            "company_name": company_name,
            "state": primary_state,
            "portfolio_type": subtype,
            "reason_qualified": (
                f"{count} CFPB complaints in debt-related products "
                f"(last {lookback}d) — potential distressed portfolio"
            ),
            "source_url": (
                f"https://www.consumerfinance.gov/data-research/"
                f"consumer-complaints/search/?company={company_query}"
            ),
            "notes": (
                f"{count} complaints. Top issues: {issue_note}"
                if issue_note
                else f"{count} complaints in debt-related products"
            ),
            "distress_signal": f"{count} CFPB complaints ({lookback}d window)",
            "private_company_confirmed": True,
        })

        if limit and len(results) >= limit:
            break

    if results:
        logger.info("CFPB: found %d distressed company signals", len(results))
    else:
        logger.info(
            "CFPB: no companies met complaint threshold (%d+)",
            MIN_COMPLAINT_THRESHOLD,
        )

    return results
