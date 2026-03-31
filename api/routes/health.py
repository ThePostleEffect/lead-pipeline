"""Source health endpoint — reports which data sources and enrichment services are configured."""

from __future__ import annotations

import os

from fastapi import APIRouter

router = APIRouter()


def _check_env(var: str) -> bool:
    """Return True if an environment variable is set and non-empty."""
    return bool(os.environ.get(var, "").strip())


@router.get("/sources")
def get_source_health() -> dict:
    """Return configuration and availability status for each data source and enrichment service."""
    courtlistener_key = _check_env("COURTLISTENER_API_KEY")
    brave_key = _check_env("BRAVE_API_KEY")
    opencorporates_key = _check_env("OPENCORPORATES_API_KEY")
    pacer_user = _check_env("PACER_USERNAME")
    pacer_pass = _check_env("PACER_PASSWORD")

    sources = [
        {
            "name": "CourtListener",
            "type": "source",
            "description": "Federal bankruptcy court filings via CourtListener API",
            "configured": courtlistener_key,
            "env_vars": ["COURTLISTENER_API_KEY"],
            "lanes": ["bankruptcy"],
            "status": "ready" if courtlistener_key else "missing_key",
        },
        {
            "name": "Court RSS",
            "type": "source",
            "description": "PACER RSS feeds from major bankruptcy courts",
            "configured": True,
            "env_vars": [],
            "lanes": ["bankruptcy"],
            "status": "ready",
        },
        {
            "name": "FDIC Failed Banks",
            "type": "source",
            "description": "Failed bank data — liquidated loan portfolios",
            "configured": True,
            "env_vars": [],
            "lanes": ["charged_off"],
            "status": "ready",
        },
        {
            "name": "CFPB Complaints",
            "type": "source",
            "description": "Consumer complaints — distressed lender/servicer signals",
            "configured": True,
            "env_vars": [],
            "lanes": ["charged_off"],
            "status": "ready",
        },
        {
            "name": "Brave Search",
            "type": "enrichment",
            "description": "Web search for company websites and info",
            "configured": brave_key,
            "env_vars": ["BRAVE_API_KEY"],
            "lanes": ["all"],
            "status": "ready" if brave_key else "fallback",
            "fallback_note": "Using domain guessing (less accurate)" if not brave_key else None,
        },
        {
            "name": "OpenCorporates",
            "type": "enrichment",
            "description": "Company entity verification and legal name lookup",
            "configured": opencorporates_key,
            "env_vars": ["OPENCORPORATES_API_KEY"],
            "lanes": ["all"],
            "status": "ready" if opencorporates_key else "disabled",
        },
        {
            "name": "SEC EDGAR",
            "type": "enrichment",
            "description": "Public company detection (auto-discard)",
            "configured": True,
            "env_vars": [],
            "lanes": ["all"],
            "status": "ready",
        },
        {
            "name": "PACER",
            "type": "enrichment",
            "description": "Bankruptcy case verification and status lookup",
            "configured": pacer_user and pacer_pass,
            "env_vars": ["PACER_USERNAME", "PACER_PASSWORD"],
            "lanes": ["bankruptcy"],
            "status": "ready" if (pacer_user and pacer_pass) else "disabled",
        },
    ]

    ready_count = sum(1 for s in sources if s["status"] == "ready")
    total_count = len(sources)

    return {
        "sources": sources,
        "summary": {
            "ready": ready_count,
            "total": total_count,
            "all_configured": ready_count == total_count,
        },
    }
