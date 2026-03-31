"""Domain classification — categorize URLs by trust level.

Every URL found during enrichment is classified before use.
Only "official" domains populate the canonical website field.
Non-official URLs are logged as supporting references for provenance.

Categories:
  official    — company's own domain (default if not matched elsewhere)
  directory   — business directories, listing sites
  government  — .gov, .mil, court/SEC/SOS sites
  social      — social media platforms
  marketplace — e-commerce platforms
  news        — news/media outlets
  skip        — search engines, generic junk
"""

from __future__ import annotations

from urllib.parse import urlparse


class DomainClass:
    OFFICIAL = "official"
    DIRECTORY = "directory"
    GOVERNMENT = "government"
    SOCIAL = "social"
    MARKETPLACE = "marketplace"
    NEWS = "news"
    SKIP = "skip"


# ── Domain lists ──────────────────────────────────────────────────────

# Government domains — never a company's own site
GOVERNMENT_DOMAINS = {
    "sec.gov", "uscourts.gov", "courtlistener.com", "pacer.gov",
    "fmcsa.dot.gov", "dot.gov", "irs.gov", "sba.gov", "ftc.gov",
    "cms.gov", "hhs.gov", "ed.gov", "state.gov",
    "sunbiz.org",  # Florida SOS (acts as gov registry)
    "opengovus.com",  # government data aggregator
    "openpaymentsdata.cms.gov",
    "adviserinfo.sec.gov",
    "ecorp.sos.ga.gov",
}

GOVERNMENT_SUFFIXES = (".gov", ".mil")

# Directory and listing sites — useful for reference, not canonical
DIRECTORY_DOMAINS = {
    # Business directories
    "bbb.org", "dnb.com", "zoominfo.com", "crunchbase.com",
    "opencorporates.com", "bizapedia.com", "buzzfile.com",
    "manta.com", "dandb.com", "hoovers.com", "owler.com",
    "pitchbook.com", "privco.com", "incfact.com",
    # City/data directories
    "city-data.com", "chamberofcommerce.com",
    # Real estate listing/marketplace sites
    "har.com", "realtor.com", "zillow.com", "redfin.com",
    "loopnet.com", "crexi.com", "costar.com",
    # Job boards
    "glassdoor.com", "indeed.com", "ziprecruiter.com",
    # Review sites
    "yelp.com", "trustpilot.com", "sitejabber.com",
    # Legal directories
    "avvo.com", "justia.com", "findlaw.com",
    # Florida/state business registries
    "flbusinessgo.com", "bizfilings.com",
    # Bankruptcy/court data listing sites
    "bkdata.com", "bankruptcydata.com", "pacermonitor.com",
    # Domain marketplace / parking
    "sawsells.com", "afternic.com", "sedo.com", "godaddy.com",
    "hugedomains.com", "dan.com",
}

# Social media and content platforms
SOCIAL_DOMAINS = {
    "linkedin.com", "facebook.com", "twitter.com", "x.com",
    "instagram.com", "youtube.com", "tiktok.com", "reddit.com",
    "medium.com", "substack.com",
}

# News/media — useful context but not company sites
NEWS_DOMAINS = {
    "bloomberg.com", "reuters.com", "wsj.com", "nytimes.com",
    "cnbc.com", "forbes.com", "businessinsider.com",
    "prnewswire.com", "businesswire.com", "globenewswire.com",
}

# Search engines and generic junk — always skip
SKIP_DOMAINS = {
    "google.com", "bing.com", "yahoo.com", "duckduckgo.com",
    "amazon.com", "ebay.com", "walmart.com",
    "wikipedia.org", "wikimedia.org",
}

# Marketplace/investor portals that look official but are platforms
MARKETPLACE_DOMAINS = {
    "shopify.com", "wix.com", "squarespace.com",
    "etsy.com", "gofundme.com",
}


# ── Classification logic ──────────────────────────────────────────────

def extract_base_domain(url: str) -> str:
    """Extract the base domain from a URL, stripping www. prefix."""
    netloc = urlparse(url).netloc.lower()
    if netloc.startswith("www."):
        netloc = netloc[4:]
    return netloc


def classify_domain(url: str) -> str:
    """Classify a URL's domain into a trust category.

    Returns one of: official, directory, government, social,
    marketplace, news, skip.
    """
    domain = extract_base_domain(url)
    if not domain:
        return DomainClass.SKIP

    # Check exact matches first
    if domain in SKIP_DOMAINS:
        return DomainClass.SKIP
    if domain in GOVERNMENT_DOMAINS:
        return DomainClass.GOVERNMENT
    if domain in DIRECTORY_DOMAINS:
        return DomainClass.DIRECTORY
    if domain in SOCIAL_DOMAINS:
        return DomainClass.SOCIAL
    if domain in NEWS_DOMAINS:
        return DomainClass.NEWS
    if domain in MARKETPLACE_DOMAINS:
        return DomainClass.MARKETPLACE

    # Check suffix patterns (.gov, .mil)
    for suffix in GOVERNMENT_SUFFIXES:
        if domain.endswith(suffix):
            return DomainClass.GOVERNMENT

    # Check if it's a subdomain of a known non-official domain
    parts = domain.split(".")
    if len(parts) >= 3:
        parent = ".".join(parts[-2:])
        if parent in GOVERNMENT_DOMAINS:
            return DomainClass.GOVERNMENT
        if parent in DIRECTORY_DOMAINS:
            return DomainClass.DIRECTORY
        if parent in SOCIAL_DOMAINS:
            return DomainClass.SOCIAL
        if parent in NEWS_DOMAINS:
            return DomainClass.NEWS

    # Default: assume official (company's own domain)
    return DomainClass.OFFICIAL


def is_official_domain(url: str) -> bool:
    """Check if a URL is classified as an official company domain."""
    return classify_domain(url) == DomainClass.OFFICIAL
