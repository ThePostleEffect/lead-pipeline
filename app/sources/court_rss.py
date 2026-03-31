"""Court RSS feed collector — supplemental bankruptcy signal discovery.

Fetches RSS feeds from federal bankruptcy court PACER systems to discover
new bankruptcy filings. These are freely accessible, no authentication needed.

Supplements CourtListener with fresher, broader signal coverage.
RSS feeds typically show last 24 hours of docket activity.

Feed URL format:
  https://ecf.{court_id}.uscourts.gov/cgi-bin/rss_outside.pl

Uses stdlib xml.etree.ElementTree (no extra dependencies).
"""

from __future__ import annotations

import logging
import re
import time
import xml.etree.ElementTree as ET
from datetime import datetime

import requests

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 20
POLITE_DELAY = 1.0  # be polite to court servers

# Major bankruptcy courts with high business filing volume
# Each entry: (court_id, state_code, court_label)
_TRACKED_COURTS = [
    ("deb", "DE", "D. Delaware"),
    ("nysb", "NY", "S.D. New York"),
    ("txsb", "TX", "S.D. Texas"),
    ("cacb", "CA", "C.D. California"),
    ("flsb", "FL", "S.D. Florida"),
    ("ilnb", "IL", "N.D. Illinois"),
    ("njb", "NJ", "D. New Jersey"),
    ("vaeb", "VA", "E.D. Virginia"),
    ("gasb", "GA", "S.D. Georgia (placeholder)"),  # Placeholder — not all courts have RSS
]

# Business entity indicators in case titles
_ENTITY_PATTERNS = re.compile(
    r'\b(LLC|Inc|Corp|Corporation|Company|Partners|Holdings|'
    r'Enterprises|Group|LP|L\.P\.|LLP|Co\.|Ltd)\b',
    re.IGNORECASE,
)

# Bankruptcy petition indicators in RSS descriptions
_PETITION_KEYWORDS = [
    "voluntary petition",
    "chapter 7",
    "chapter 11",
    "chapter 13",
    "chapter 12",
    "bankruptcy petition",
    "petition filed",
]


def _build_feed_url(court_id: str) -> str:
    """Build the PACER RSS feed URL for a court."""
    return f"https://ecf.{court_id}.uscourts.gov/cgi-bin/rss_outside.pl"


def _fetch_feed(url: str) -> str | None:
    """Fetch an RSS feed and return raw XML."""
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": "LeadPipeline/1.0"},
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code != 200:
            logger.debug("Court RSS: HTTP %d from %s", resp.status_code, url)
            return None
        return resp.text
    except requests.RequestException as exc:
        logger.debug("Court RSS: failed to fetch %s: %s", url, exc)
        return None


def _parse_rss(xml_text: str) -> list[dict]:
    """Parse RSS XML into a list of item dicts."""
    items: list[dict] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        logger.debug("Court RSS: XML parse error: %s", exc)
        return items

    # Handle both RSS 2.0 (<channel><item>) and Atom (<entry>)
    channel = root.find("channel")
    if channel is not None:
        for item in channel.findall("item"):
            items.append({
                "title": (item.findtext("title") or "").strip(),
                "link": (item.findtext("link") or "").strip(),
                "description": (item.findtext("description") or "").strip(),
                "pubDate": (item.findtext("pubDate") or "").strip(),
            })
    else:
        # Try Atom format
        ns = {"atom": "http://www.w3.org/2005/Atom"}
        for entry in root.findall("atom:entry", ns):
            link_el = entry.find("atom:link", ns)
            items.append({
                "title": (entry.findtext("atom:title", "", ns) or "").strip(),
                "link": link_el.get("href", "") if link_el is not None else "",
                "description": (entry.findtext("atom:summary", "", ns) or "").strip(),
                "pubDate": (entry.findtext("atom:updated", "", ns) or "").strip(),
            })

    return items


def _is_adversary_or_trustee(title: str) -> bool:
    """Filter out adversary proceedings and trustee-driven actions."""
    lower = title.lower()
    # Adversary proceedings (lawsuits within bankruptcy)
    if " v. " in title or " vs. " in title or " v " in title:
        return True
    if "-ap-" in lower:
        return True
    # Trustee-driven cases
    if "trustee" in lower and ("capacity as" in lower or "chapter 7 trustee" in lower):
        return True
    return False


def _is_business_bankruptcy(title: str, description: str) -> bool:
    """Check if an RSS item looks like a business bankruptcy filing."""
    # Skip adversary proceedings and trustee actions
    if _is_adversary_or_trustee(title):
        return False

    text = f"{title} {description}".lower()

    # Must have a business entity indicator
    if not _ENTITY_PATTERNS.search(title):
        return False

    # Must look like a bankruptcy petition (not a routine docket entry)
    if any(kw in text for kw in _PETITION_KEYWORDS):
        return True

    # Also accept items that look like new case filings
    if "in re:" in text and ("bk-" in text or "bankruptcy" in text):
        return True

    return False


def _clean_case_name(title: str) -> str:
    """Extract company name from an RSS title like '4:26-bk-12345 In re: Company LLC'."""
    name = title.strip()

    # Remove leading docket number
    name = re.sub(r'^[\d:]+[-\w]*\s*', '', name)

    # Remove "In re:" prefix
    for prefix in ("In re:", "In re", "In the Matter of:", "In the Matter of"):
        if name.lower().startswith(prefix.lower()):
            name = name[len(prefix):].strip()

    # Remove trailing case info
    for suffix in (", Debtor", ", Debtors", " - Debtor", " et al.", " et al"):
        if name.lower().endswith(suffix.lower()):
            name = name[:-len(suffix)].strip()

    name = name.strip(" ,;:-")
    return name


def _extract_chapter(title: str, description: str) -> str:
    """Extract bankruptcy chapter from RSS item."""
    text = f"{title} {description}".lower()
    if "chapter 11" in text:
        return "11"
    if "chapter 7" in text:
        return "7"
    if "chapter 13" in text:
        return "13"
    if "chapter 12" in text:
        return "12"
    return ""


def _extract_docket_number(title: str) -> str:
    """Extract docket number from RSS title."""
    match = re.match(r'^([\d:]+[-\w]+)', title)
    return match.group(1) if match else ""


def collect_court_rss(lane: str, limit: int | None = None, filters=None) -> list[dict]:
    """Collect bankruptcy signals from court RSS feeds.

    Only fires for the bankruptcy lane.
    Returns raw signal dicts ready for pipeline normalization.
    """
    from app.models import SearchFilters
    if filters is None:
        filters = SearchFilters()

    if lane != "bankruptcy":
        return []

    target_chapters = set(filters.chapters)
    logger.info("Court RSS: scanning %d tracked courts (chapters %s)", len(_TRACKED_COURTS), ",".join(sorted(target_chapters)))

    results: list[dict] = []
    seen_titles: set[str] = set()

    for court_id, state_code, court_label in _TRACKED_COURTS:
        url = _build_feed_url(court_id)
        xml_text = _fetch_feed(url)

        if not xml_text:
            continue

        items = _parse_rss(xml_text)
        court_hits = 0

        for item in items:
            title = item["title"]
            description = item["description"]

            if not _is_business_bankruptcy(title, description):
                continue

            # Dedupe within this batch
            if title in seen_titles:
                continue
            seen_titles.add(title)

            company_name = _clean_case_name(title)
            if not company_name:
                continue

            chapter = _extract_chapter(title, description)

            if chapter not in target_chapters:
                continue

            docket = _extract_docket_number(title)

            portfolio_type = f"bankruptcy_ch{chapter}"
            distress = f"Chapter {chapter} bankruptcy filing"

            results.append({
                "company_name": company_name,
                "state": state_code,
                "portfolio_type": portfolio_type,
                "bankruptcy_chapter": chapter,
                "reason_qualified": f"{distress} — {court_label}",
                "source_url": item.get("link", ""),
                "notes": f"Docket {docket}. Court RSS feed: {court_id}." if docket else f"Court RSS: {court_id}",
                "distress_signal": distress,
                "private_company_confirmed": True,
            })
            court_hits += 1

            if limit and len(results) >= limit:
                logger.info("Court RSS: reached limit of %d results", limit)
                return results

        if court_hits:
            logger.debug("Court RSS: %d signals from %s", court_hits, court_id)

        time.sleep(POLITE_DELAY)

    if results:
        logger.info("Court RSS: found %d business bankruptcy signals total", len(results))
    else:
        logger.info("Court RSS: no new business bankruptcy signals found")

    return results
