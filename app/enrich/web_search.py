"""Web search and domain guessing — find company websites.

Two strategies:
1. Brave Search API (primary) — set BRAVE_API_KEY env var
2. Domain guessing (fallback) — construct likely .com domains and verify

Only returns URLs classified as "official" by domain_classification.
Non-official results are returned separately as supporting references.
"""

from __future__ import annotations

import logging
import os
import re
import time

import requests

from app.enrich.domain_classification import (
    DomainClass,
    classify_domain,
    extract_base_domain,
    is_official_domain,
)

logger = logging.getLogger(__name__)

REQUEST_TIMEOUT = 10
POLITE_DELAY = 0.3
MAX_DOMAIN_GUESSES = 6
USER_AGENT = "LeadPipeline/1.0 (business-development research tool)"

# Common entity suffixes to strip when guessing domains
_ENTITY_SUFFIXES = [
    " LLC", " L.L.C.", " Inc.", " Inc", " Corp.", " Corp",
    " Corporation", " Company", " Co.", " Co",
    " LP", " L.P.", " LLP", " L.L.P.",
    " Partners", " Holdings", " Enterprises", " Group",
    " Services", " Solutions", " Associates", " Advisors",
    " International", " Global", " National",
]

_FILLER_WORDS = {"the", "of", "and", "&", "a", "an", "for", "in", "at", "by"}


# ── Name helpers ──────────────────────────────────────────────────────

def strip_entity_suffix(name: str) -> str:
    """Remove common business entity suffixes from a company name."""
    result = name.strip()
    for suffix in sorted(_ENTITY_SUFFIXES, key=len, reverse=True):
        if result.lower().endswith(suffix.lower()):
            result = result[:-len(suffix)].strip(" ,.")
            break
    return result


def name_to_words(name: str) -> list[str]:
    """Split a cleaned company name into meaningful words."""
    cleaned = re.sub(r"[^\w\s-]", "", name)
    words = cleaned.lower().split()
    return [w for w in words if w not in _FILLER_WORDS and len(w) > 1]


# ── Brave Search API ──────────────────────────────────────────────────

def get_brave_key() -> str | None:
    return os.environ.get("BRAVE_API_KEY")


def brave_search(query: str, count: int = 5) -> list[dict]:
    """Search Brave and return web results."""
    key = get_brave_key()
    if not key:
        return []

    try:
        resp = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": key,
            },
            params={"q": query, "count": count},
            timeout=REQUEST_TIMEOUT,
        )
        if resp.status_code == 429:
            logger.warning("Brave Search: rate limited")
            return []
        if resp.status_code != 200:
            logger.warning("Brave Search: HTTP %d", resp.status_code)
            return []

        data = resp.json()
        return data.get("web", {}).get("results", [])

    except requests.RequestException as exc:
        logger.warning("Brave Search request failed: %s", exc)
        return []


def find_website_via_search(company_name: str, state: str) -> tuple[str | None, list[str]]:
    """Use Brave Search to find a company's official website.

    Returns:
        (official_url or None, list of supporting reference URLs)
    """
    query = f"{company_name} {state} official website".strip()
    results = brave_search(query, count=8)

    words = name_to_words(strip_entity_suffix(company_name))
    official_url: str | None = None
    supporting_urls: list[str] = []

    for result in results:
        url = result.get("url", "")
        if not url:
            continue

        classification = classify_domain(url)

        if classification == DomainClass.SKIP:
            continue

        if classification != DomainClass.OFFICIAL:
            supporting_urls.append(url)
            logger.debug("Search found %s reference: %s (%s)", classification, url, company_name)
            continue

        if official_url:
            continue

        title = result.get("title", "").lower()
        desc = result.get("description", "").lower()

        if words and any(w in title or w in desc for w in words[:3]):
            official_url = url
            logger.debug("Search found official site: %s for '%s'", url, company_name)
        elif not official_url:
            official_url = url
            logger.debug("Search found official site (weak match): %s for '%s'", url, company_name)

    return official_url, supporting_urls


# ── Domain guessing (fallback) ────────────────────────────────────────

def guess_domains(company_name: str) -> list[str]:
    """Generate likely domain guesses from a company name."""
    stripped = strip_entity_suffix(company_name)
    words = name_to_words(stripped)

    if not words:
        return []

    candidates: list[str] = []
    seen: set[str] = set()

    def _add(domain: str) -> None:
        if domain not in seen and len(domain) > 5:
            seen.add(domain)
            candidates.append(domain)

    _add("".join(words) + ".com")
    if len(words) >= 2:
        _add(words[0] + words[1] + ".com")
    if len(words) >= 3:
        _add(words[0] + words[1] + words[2] + ".com")
    if len(words[0]) >= 5:
        _add(words[0] + ".com")
    if len(words) >= 3:
        _add(words[0] + words[-1] + ".com")
    if len(words) >= 2:
        _add("-".join(words[:3]) + ".com")

    return candidates[:MAX_DOMAIN_GUESSES]


def verify_domain(domain: str) -> str | None:
    """Check if a domain resolves and hasn't redirected to unrelated site."""
    for scheme in ("https", "http"):
        url = f"{scheme}://{domain}"
        try:
            resp = requests.head(
                url, timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
                headers={"User-Agent": USER_AGENT},
            )
            if resp.status_code >= 400:
                continue

            final_url = str(resp.url)
            final_base = extract_base_domain(final_url)
            original_base = domain.lower().replace("www.", "")
            if final_base != original_base:
                logger.debug("Skipping %s — redirected to %s", domain, final_base)
                continue

            if not is_official_domain(final_url):
                logger.debug("Skipping %s — classified as %s", domain, classify_domain(final_url))
                continue

            return final_url
        except requests.RequestException:
            continue

    return None


def find_website_via_guessing(company_name: str) -> str | None:
    """Fallback: guess domains and verify. Only returns official domains."""
    guesses = guess_domains(company_name)
    for domain in guesses:
        verified = verify_domain(domain)
        if verified:
            logger.debug("Domain guess found %s for '%s'", verified, company_name)
            return verified
        time.sleep(POLITE_DELAY)
    return None
