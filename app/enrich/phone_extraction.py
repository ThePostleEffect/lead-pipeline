"""Phone extraction — scrape phone numbers from company websites.

Checks homepage first, then /contact and /about pages.
Validates US phone number format (area code, exchange rules).
Only extracts from official company websites — never from directories.
"""

from __future__ import annotations

import logging
import re
import time
from urllib.parse import urljoin

import requests

from app.utils.phones import normalize_phone

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10
POLITE_DELAY = 0.3
USER_AGENT = "LeadPipeline/1.0 (business-development research tool)"

# US phone number pattern (various formats)
_PHONE_PATTERN = re.compile(
    r'(?<!\d)'                    # not preceded by digit
    r'[\(]?(\d{3})[\)]?'         # area code
    r'[-.\s]?'                    # separator
    r'(\d{3})'                    # exchange
    r'[-.\s]?'                    # separator
    r'(\d{4})'                    # subscriber
    r'(?!\d)',                     # not followed by digit
)

# Fake/placeholder phone patterns to skip
_FAKE_PHONES = {"000-000-0000", "111-111-1111", "123-456-7890", "555-555-5555",
                "999-999-9999", "800-000-0000"}


def extract_phones_from_html(html: str) -> list[str]:
    """Extract valid US phone numbers from HTML content."""
    matches = _PHONE_PATTERN.findall(html)
    phones: list[str] = []
    seen: set[str] = set()

    for area, exchange, subscriber in matches:
        raw = f"{area}-{exchange}-{subscriber}"
        normalized = normalize_phone(raw)
        if normalized and normalized not in seen and normalized not in _FAKE_PHONES:
            # US area code: first digit 2-9, not N11 pattern
            if area[0] not in ("0", "1") and not (area[1] == "1" and area[2] == "1"):
                # Exchange: first digit 2-9
                if exchange[0] not in ("0", "1"):
                    seen.add(normalized)
                    phones.append(normalized)

    return phones


def fetch_phone_from_site(base_url: str) -> str | None:
    """Fetch a website and try to find a phone number.

    Checks homepage first, then /contact and /about pages.
    """
    headers = {"User-Agent": USER_AGENT}
    pages_to_try = [
        base_url,
        urljoin(base_url, "/contact"),
        urljoin(base_url, "/contact-us"),
        urljoin(base_url, "/about"),
        urljoin(base_url, "/about-us"),
    ]

    for page_url in pages_to_try:
        try:
            resp = requests.get(
                page_url, timeout=REQUEST_TIMEOUT,
                headers=headers, allow_redirects=True,
            )
            if resp.status_code >= 400:
                continue

            phones = extract_phones_from_html(resp.text)
            if phones:
                logger.debug("Found phone %s on %s", phones[0], page_url)
                return phones[0]
        except requests.RequestException:
            continue
        time.sleep(POLITE_DELAY)

    return None
