"""CourtListener bankruptcy signal collector.

Uses the CourtListener Search API (v4) to discover recent business bankruptcy
filings. These are SIGNAL sources — we extract company names and case info,
then rely on the enrichment pipeline to find websites, phones, and contacts.

Requires a free CourtListener account and API token.
Set the token via environment variable: COURTLISTENER_API_KEY

API docs: https://www.courtlistener.com/help/api/rest/
"""

from __future__ import annotations

import logging
import os
import re
import time
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://www.courtlistener.com/api/rest/v4"
DEFAULT_LOOKBACK_DAYS = 30
REQUEST_TIMEOUT = 45
MAX_PAGES = 5  # Safety limit on pagination

# Business entity indicators — used to filter search results
_ENTITY_TERMS = "LLC OR Inc OR Corp OR Corporation OR Company OR Partners OR Holdings OR Enterprises OR Group OR LP"

# All federal bankruptcy court IDs for the court filter
_BANKR_COURTS = (
    "almb,alnb,alsb,akb,azb,areb,arwb,cacb,caeb,canb,casb,cob,ctb,deb,dcb,"
    "flmb,flnb,flsb,gamb,ganb,gasb,hib,idb,ilcb,ilnb,ilsb,innb,insb,ianb,"
    "iasb,ksb,kyeb,kywb,laeb,lamb,lawb,meb,mdb,mab,mieb,miwb,mnb,msnb,mssb,"
    "moeb,mowb,mtb,neb,nvb,nhb,njb,nmb,nyeb,nynb,nysb,nywb,nceb,ncmb,ncwb,"
    "ndb,ohnb,ohsb,okeb,oknb,okwb,orb,paeb,pamb,pawb,rib,scb,sdb,tneb,tnmb,"
    "tnwb,txeb,txnb,txsb,txwb,utb,vtb,vaeb,vawb,waeb,wawb,wvnb,wvsb,wieb,"
    "wiwb,wyb"
)


def _get_api_key() -> str | None:
    return os.environ.get("COURTLISTENER_API_KEY")


def _get_headers() -> dict[str, str]:
    headers = {"Accept": "application/json"}
    key = _get_api_key()
    if key:
        headers["Authorization"] = f"Token {key}"
    return headers


def _extract_state_from_court(court_id: str) -> str:
    """Extract 2-letter state code from CourtListener court ID.

    Court IDs follow patterns like "alnb" (AL Northern Bankruptcy),
    "nysb" (NY Southern Bankruptcy), "txeb" (TX Eastern Bankruptcy).
    """
    if not court_id:
        return ""

    state_prefixes = {
        "al": "AL", "ak": "AK", "az": "AZ", "ar": "AR", "ca": "CA",
        "co": "CO", "ct": "CT", "de": "DE", "dc": "DC", "fl": "FL",
        "ga": "GA", "hi": "HI", "id": "ID", "il": "IL", "in": "IN",
        "ia": "IA", "ks": "KS", "ky": "KY", "la": "LA", "me": "ME",
        "md": "MD", "ma": "MA", "mi": "MI", "mn": "MN", "ms": "MS",
        "mo": "MO", "mt": "MT", "ne": "NE", "nv": "NV", "nh": "NH",
        "nj": "NJ", "nm": "NM", "ny": "NY", "nc": "NC", "nd": "ND",
        "oh": "OH", "ok": "OK", "or": "OR", "pa": "PA", "ri": "RI",
        "sc": "SC", "sd": "SD", "tn": "TN", "tx": "TX", "ut": "UT",
        "vt": "VT", "va": "VA", "wa": "WA", "wv": "WV", "wi": "WI",
        "wy": "WY", "pr": "PR", "vi": "VI", "gu": "GU",
    }

    # Strip trailing 'b' (bankruptcy indicator)
    base = court_id.rstrip("b")
    prefix = base[:2].lower()
    return state_prefixes.get(prefix, "")


def _is_adversary_proceeding(case_name: str, docket_number: str) -> bool:
    """Detect adversary proceedings (lawsuits within bankruptcy, not filings)."""
    if " v. " in case_name or " vs. " in case_name or " v " in case_name:
        return True
    if docket_number and "-ap-" in docket_number.lower():
        return True
    return False


def _has_trustee_indicator(case_name: str, trustee_str: str) -> bool:
    """Check if this case is trustee-driven (we exclude trustees)."""
    lower = case_name.lower()
    if "trustee" in lower and ("capacity as" in lower or "chapter 7 trustee" in lower):
        return True
    # trustee_str from search results — skip if trustee is prominently named
    # But don't skip just because a trustee is assigned (most Ch7 cases have one)
    return False


def _clean_company_name(raw_name: str) -> str:
    """Clean a case name from court records into a usable company name."""
    name = raw_name.strip()

    # Remove common legal prefixes
    for prefix in ("In re:", "In re", "In the Matter of:", "In the Matter of"):
        if name.lower().startswith(prefix.lower()):
            name = name[len(prefix):].strip()

    # Handle "X and Y" multi-debtor cases — take the first entity
    if " and " in name:
        parts = name.split(" and ", 1)
        # Only split if both parts look like entities
        if any(ind in parts[0] for ind in ("LLC", "Inc", "Corp", "Company", "LP", "Partners")):
            name = parts[0].strip()

    # Remove common suffixes
    for suffix in (", Debtor", ", Debtors", " - Debtor", " - Debtors",
                   ", Chapter 7", ", Chapter 11", ", Chapter 13",
                   ", et al.", ", et al"):
        if name.lower().endswith(suffix.lower()):
            name = name[:-len(suffix)].strip()

    # Remove leading/trailing punctuation
    name = name.strip(" ,;:-")

    return name


def _chapter_from_result(result: dict) -> str:
    """Extract bankruptcy chapter from search result."""
    ch = result.get("chapter", "")
    if ch and str(ch) in ("7", "11", "12", "13"):
        return str(ch)
    # Try to infer from case name or short descriptions
    case_name = result.get("caseName", "").lower()
    if "chapter 11" in case_name:
        return "11"
    if "chapter 7" in case_name:
        return "7"
    if "chapter 13" in case_name:
        return "13"
    return ""


def _portfolio_type_from_chapter(chapter: str) -> str:
    return {
        "7": "bankruptcy_ch7",
        "11": "bankruptcy_ch11",
        "13": "bankruptcy_ch13",
        "12": "bankruptcy_ch12",
    }.get(chapter, "bankruptcy_general")


def _build_reason(chapter: str, date_filed: str, court: str) -> str:
    parts = []
    if chapter:
        parts.append(f"Chapter {chapter} bankruptcy filing")
    else:
        parts.append("Bankruptcy filing")
    if date_filed:
        parts.append(f"filed {date_filed}")
    if court:
        parts.append(f"in {court}")
    return " — ".join(parts)


def _paginated_search(
    query: str,
    lookback_days: int,
    limit: int | None,
    seen_dockets: set[str],
    target_chapters: set[str],
    require_entity: bool,
) -> list[dict]:
    """Run a paginated CourtListener search and return raw lead dicts.

    Args:
        query: Search query string (entity terms for business search, chapter terms for individual search)
        lookback_days: How far back to search
        limit: Max results to return
        seen_dockets: Shared set for cross-search dedup
        target_chapters: Which chapters to keep (e.g. {"13", "7"})
        require_entity: If True, skip results without business entity indicators in case name
    """
    headers = _get_headers()
    since = (datetime.utcnow() - timedelta(days=lookback_days)).strftime("%Y-%m-%d")

    params: dict = {
        "q": query,
        "type": "r",
        "filed_after": since,
        "court": _BANKR_COURTS,
    }

    results: list[dict] = []
    url = f"{BASE_URL}/search/"
    pages_fetched = 0

    while url and pages_fetched < MAX_PAGES:
        try:
            logger.debug("CourtListener search: page %d, query='%s'", pages_fetched + 1, query[:60])
            resp = requests.get(url, headers=headers, params=params, timeout=REQUEST_TIMEOUT)

            if resp.status_code == 401:
                logger.error("CourtListener: auth failed — check COURTLISTENER_API_KEY")
                break
            if resp.status_code == 429:
                logger.warning("CourtListener: rate limited, backing off 5s")
                time.sleep(5)
                continue

            resp.raise_for_status()
            data = resp.json()

        except requests.RequestException as exc:
            logger.error("CourtListener search failed: %s", exc)
            break

        for result in data.get("results", []):
            case_name = result.get("caseName", "")
            docket_id = str(result.get("docket_id", ""))
            docket_number = result.get("docketNumber", "")
            trustee_str = result.get("trustee_str", "")

            if docket_id in seen_dockets:
                continue
            seen_dockets.add(docket_id)

            if _is_adversary_proceeding(case_name, docket_number):
                continue

            if _has_trustee_indicator(case_name, trustee_str):
                continue

            # For business entity search, require entity indicators
            if require_entity and not _ENTITY_PATTERN.search(case_name):
                continue

            company_name = _clean_company_name(case_name)
            if not company_name:
                continue

            court_id = result.get("court_id", "")
            court_name = result.get("court", "")
            state = _extract_state_from_court(court_id)
            date_filed = result.get("dateFiled", "")
            chapter = _chapter_from_result(result)
            portfolio_type = _portfolio_type_from_chapter(chapter)

            if chapter not in target_chapters:
                continue

            reason = _build_reason(chapter, date_filed, court_name)
            source_url = f"https://www.courtlistener.com{result.get('docket_absolute_url', '')}"
            distress = f"Chapter {chapter} bankruptcy filing" if chapter else "Bankruptcy filing"

            # Tag individual vs business for downstream context
            has_entity = bool(_ENTITY_PATTERN.search(case_name))

            results.append({
                "company_name": company_name,
                "state": state,
                "portfolio_type": portfolio_type,
                "bankruptcy_chapter": chapter,
                "reason_qualified": reason,
                "source_url": source_url,
                "notes": f"Docket {docket_number}. Case: {case_name}."
                         + ("" if has_entity else " [Individual filer]"),
                "distress_signal": distress,
                "private_company_confirmed": has_entity,
            })

            if limit and len(results) >= limit:
                return results

        url = data.get("next")
        params = {}
        pages_fetched += 1

        if url:
            time.sleep(0.5)

    return results


# Compiled regex for entity detection (reused in multiple places)
_ENTITY_PATTERN = re.compile(
    r'\b(LLC|Inc|Corp|Corporation|Company|Partners|Holdings|'
    r'Enterprises|Group|LP|L\.P\.|LLP|Co\.|Ltd)\b',
    re.IGNORECASE,
)


def collect_courtlistener_bankruptcy(lane: str, limit: int | None = None, filters=None) -> list[dict]:
    """Entry point for the PublicWebSource registry.

    Only fires for the bankruptcy lane. Runs two search passes:
    1. Business entities (LLC, Inc, Corp, etc.) — all target chapters
    2. Chapter 13 individuals (if include_individuals=True) — Ch.13 filings
       that may represent sole proprietors or individuals with business debts

    Returns raw signal dicts that the pipeline normalizes, enriches, filters, and scores.
    """
    from app.models import SearchFilters
    if filters is None:
        filters = SearchFilters()

    if lane != "bankruptcy":
        return []

    api_key = _get_api_key()
    if not api_key:
        logger.warning(
            "COURTLISTENER_API_KEY not set. "
            "Get a free token at https://www.courtlistener.com/ "
            "and set it as an environment variable."
        )
        return []

    target_chapters = set(filters.chapters)
    lookback = filters.lookback_days
    seen_dockets: set[str] = set()
    all_results: list[dict] = []

    # Pass 1: Business entity filings (LLC, Inc, Corp, etc.)
    logger.info(
        "CourtListener: searching business entity bankruptcies (chapters %s, last %d days)",
        ",".join(sorted(target_chapters)), lookback,
    )
    biz_results = _paginated_search(
        query=_ENTITY_TERMS,
        lookback_days=lookback,
        limit=limit,
        seen_dockets=seen_dockets,
        target_chapters=target_chapters,
        require_entity=True,
    )
    all_results.extend(biz_results)
    logger.info("CourtListener: %d business entity signals", len(biz_results))

    # Pass 2: Ch.13 individual filers (if enabled and Ch.13 is a target)
    if filters.include_individuals and "13" in target_chapters:
        remaining = (limit - len(all_results)) if limit else None
        if remaining is None or remaining > 0:
            logger.info("CourtListener: searching Ch.13 individual filers (last %d days)", lookback)
            individual_results = _paginated_search(
                query='"chapter 13" AND "voluntary petition"',
                lookback_days=lookback,
                limit=remaining,
                seen_dockets=seen_dockets,
                target_chapters={"13"},
                require_entity=False,
            )
            all_results.extend(individual_results)
            logger.info("CourtListener: %d Ch.13 individual signals", len(individual_results))

    if all_results:
        logger.info("CourtListener: %d total bankruptcy signals", len(all_results))
    else:
        logger.warning("CourtListener: no bankruptcy results found")

    return all_results
