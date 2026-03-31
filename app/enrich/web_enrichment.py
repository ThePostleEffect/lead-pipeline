"""Web enrichment orchestrator — find websites and phones for leads.

Thin orchestrator that delegates to focused modules:
  - web_search: Brave Search API + domain guessing
  - domain_classification: URL trust classification
  - phone_extraction: phone scraping from websites

Non-destructive: won't overwrite existing values.
Only "official" domains populate the canonical website field.
"""

from __future__ import annotations

import logging
import time

from app.enrich.phone_extraction import fetch_phone_from_site
from app.enrich.web_search import (
    POLITE_DELAY,
    find_website_via_guessing,
    find_website_via_search,
    get_brave_key,
)
from app.models import Lead
from app.utils.urls import normalize_url

logger = logging.getLogger(__name__)


def enrich_lead_from_web(lead: Lead) -> Lead:
    """Try to find website and phone for a single lead via web lookup.

    Strategy:
    1. Brave Search API (if BRAVE_API_KEY set) — best accuracy
    2. Domain guessing fallback — no API needed, lower hit rate
    3. Phone extraction from official website only

    Non-destructive: won't overwrite existing values.
    """
    needs_website = not lead.website
    needs_phone = not lead.business_phone

    if not needs_website and not needs_phone:
        return lead

    supporting_refs: list[str] = []

    # Step 1: Find website if missing
    if needs_website:
        official_url, refs = find_website_via_search(lead.company_name, lead.state)
        supporting_refs.extend(refs)

        if official_url:
            lead.website = normalize_url(official_url)
            logger.debug("Search enriched website for %s: %s", lead.company_name, lead.website)
        else:
            guessed = find_website_via_guessing(lead.company_name)
            if guessed:
                lead.website = normalize_url(guessed)
                logger.debug("Guess enriched website for %s: %s", lead.company_name, lead.website)

    # Step 2: Find phone if missing (only from official website)
    if not lead.business_phone and lead.website:
        phone = fetch_phone_from_site(lead.website)
        if phone:
            lead.business_phone = phone
            logger.debug("Enriched phone for %s: %s", lead.company_name, phone)

    # Step 3: Log supporting references in notes
    if supporting_refs:
        ref_note = "Supporting refs: " + "; ".join(supporting_refs[:3])
        if lead.notes:
            lead.notes = f"{lead.notes} | {ref_note}"
        else:
            lead.notes = ref_note

    return lead


def enrich_leads_from_web(leads: list[Lead]) -> list[Lead]:
    """Batch web enrichment for leads missing website or phone.

    Only processes leads that need enrichment. Rate-limited to be polite.
    """
    needs_enrichment = [ld for ld in leads if not ld.website or not ld.business_phone]

    if not needs_enrichment:
        logger.info("Web enrichment: all %d leads already have website and phone", len(leads))
        return leads

    has_brave = bool(get_brave_key())
    method = "Brave Search + domain guess fallback" if has_brave else "domain guessing only"
    logger.info(
        "Web enrichment: %d of %d leads need lookup (%s)",
        len(needs_enrichment), len(leads), method,
    )

    enriched_count = 0
    for i, lead in enumerate(needs_enrichment):
        had_website = bool(lead.website)
        had_phone = bool(lead.business_phone)

        enrich_lead_from_web(lead)

        found_something = (not had_website and bool(lead.website)) or \
                          (not had_phone and bool(lead.business_phone))
        if found_something:
            enriched_count += 1

        if (i + 1) % 10 == 0:
            logger.info("Web enrichment progress: %d/%d processed, %d enriched",
                        i + 1, len(needs_enrichment), enriched_count)

        if has_brave:
            time.sleep(POLITE_DELAY)

    logger.info(
        "Web enrichment complete: %d of %d leads enriched with new data",
        enriched_count, len(needs_enrichment),
    )

    return leads
