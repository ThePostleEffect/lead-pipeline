"""Email enrichment — scrape company websites for email addresses.

Strategy (in priority order):
  1. Scrape the company's website for mailto: links and email patterns
  2. Try common contact page paths (/contact, /about, /team) if homepage is empty
  3. Fall back to guessing info@domain.com from the website domain

No API key required. Uses only the website field already enriched in step 2b.
Adds a polite 1.5s delay between requests.
"""

from __future__ import annotations

import logging
import re
import time
from urllib.parse import urljoin, urlparse

import requests

from app.models import Lead

logger = logging.getLogger(__name__)

POLITE_DELAY = 1.5
REQUEST_TIMEOUT = 10

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; LeadPipeline/1.0; +https://github.com/ThePostleEffect/lead-pipeline)"
    ),
    "Accept": "text/html,application/xhtml+xml",
}

# Regex: match anything that looks like an email address
_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

# Email prefixes we skip — too generic to be useful as a lead contact
_SKIP_PREFIXES = {
    "noreply", "no-reply", "donotreply", "do-not-reply",
    "support", "help", "admin", "webmaster", "postmaster",
    "abuse", "spam", "unsubscribe", "privacy", "legal",
    "newsletter", "news", "marketing", "sales@sales",
    "notifications", "bounce", "mailer-daemon",
}

# Contact-style paths to try if homepage yields nothing
_CONTACT_PATHS = ["/contact", "/contact-us", "/about", "/about-us", "/team", "/staff"]


def _is_useful_email(email: str, domain: str) -> bool:
    """Filter out generic/system emails that aren't useful leads."""
    email_lower = email.lower()
    prefix = email_lower.split("@")[0]
    email_domain = email_lower.split("@")[1] if "@" in email_lower else ""

    # Must be on the company's own domain (or a close variant)
    if domain and not email_domain.endswith(domain.lstrip("www.")):
        return False

    if prefix in _SKIP_PREFIXES:
        return False

    return True


def _extract_emails_from_html(html: str, domain: str) -> list[str]:
    """Pull email addresses from raw HTML, filtering out junk."""
    found = _EMAIL_RE.findall(html)
    seen: set[str] = set()
    result: list[str] = []
    for email in found:
        email_lower = email.lower()
        if email_lower not in seen and _is_useful_email(email_lower, domain):
            seen.add(email_lower)
            result.append(email_lower)
    return result


def _fetch_html(url: str) -> str:
    """Fetch a page's HTML. Returns empty string on any error."""
    try:
        resp = requests.get(url, headers=_HEADERS, timeout=REQUEST_TIMEOUT, allow_redirects=True)
        if resp.status_code == 200:
            return resp.text
    except requests.RequestException:
        pass
    return ""


def find_emails_on_website(url: str) -> list[str]:
    """Scrape a company website for real email addresses.

    Tries the homepage first, then common contact page paths.
    Returns a list of email strings (best candidates first), or empty list.
    """
    if not url:
        return []

    parsed = urlparse(url if url.startswith("http") else f"https://{url}")
    domain = parsed.netloc.lstrip("www.")

    # Try homepage
    html = _fetch_html(url)
    emails = _extract_emails_from_html(html, domain)

    # If homepage had nothing, try contact/about paths
    if not emails:
        base = f"{parsed.scheme}://{parsed.netloc}"
        for path in _CONTACT_PATHS:
            page_html = _fetch_html(urljoin(base, path))
            emails = _extract_emails_from_html(page_html, domain)
            if emails:
                break

    return emails


def _guess_info_email(url: str) -> str:
    """Fallback: construct info@domain.com from the website URL."""
    if not url:
        return ""
    try:
        parsed = urlparse(url if url.startswith("http") else f"https://{url}")
        domain = parsed.netloc.lstrip("www.")
        if domain and "." in domain:
            return f"info@{domain}"
    except Exception:
        pass
    return ""


def enrich_leads_with_emails(leads: list[Lead]) -> list[Lead]:
    """Batch email enrichment — scrape websites then fall back to info@ guess.

    Only processes leads that have a website but no email yet.
    Adds polite delay between requests.
    """
    needs_email = [ld for ld in leads if ld.website and not ld.email]

    if not needs_email:
        logger.info("Email enrichment: no leads need email lookup")
        return leads

    logger.info("Email enrichment: processing %d leads", len(needs_email))

    found_count = 0
    for lead in needs_email:
        logger.info("Email enrichment: processing %s → %s", lead.company_name, lead.website)

        emails = find_emails_on_website(lead.website)

        if emails:
            lead.email = emails[0]  # Best candidate first
            logger.debug("  Found real email: %s", lead.email)
            found_count += 1
        else:
            guessed = _guess_info_email(lead.website)
            if guessed:
                lead.email = guessed
                logger.debug("  Guessed fallback: %s", lead.email)
                found_count += 1
            else:
                logger.debug("  No email found for %s", lead.company_name)

        time.sleep(POLITE_DELAY)

    logger.info(
        "Email enrichment complete: %d/%d leads now have email",
        found_count, len(needs_email),
    )
    return leads
