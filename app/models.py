"""Data models for the lead pipeline."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any, Optional
from uuid import uuid4

from pydantic import BaseModel, Field


class LeadLane(str, Enum):
    CHARGED_OFF = "charged_off"
    BANKRUPTCY = "bankruptcy"
    PERFORMING = "performing"
    CAPITAL_SEEKING = "capital_seeking"


class QualityTier(str, Enum):
    BEST_CASE = "best_case"
    MID_LEVEL = "mid_level"
    WEAK = "weak"


class SourceType(str, Enum):
    MANUAL = "manual"
    PUBLIC_WEB = "public_web"
    PACER = "pacer"
    API = "api"


class LeadStatus(str, Enum):
    NEW = "new"
    REVIEWED = "reviewed"
    CONTACTED = "contacted"
    QUALIFIED = "qualified"
    DISQUALIFIED = "disqualified"
    DISCARDED = "discarded"


def _generate_lead_id() -> str:
    return f"LEAD-{uuid4().hex[:10].upper()}"


class Lead(BaseModel):
    """Core lead data model. Every kept lead must have these fields populated."""

    lead_id: str = Field(default_factory=_generate_lead_id)
    collected_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    company_name: str
    lead_lane: LeadLane
    portfolio_type: str = ""
    private_company_confirmed: bool = False
    public_company_confirmed: bool = False
    trustee_related: bool = False
    state: str = ""
    city: str = ""
    website: str = ""
    business_phone: str = ""
    reason_qualified: str = ""
    quality_tier: QualityTier = QualityTier.WEAK
    confidence_score: float = 0.0
    source_type: SourceType = SourceType.MANUAL
    source_url: str = ""
    notes: str = ""
    status: LeadStatus = LeadStatus.NEW

    # Preferred optional fields
    named_contact: Optional[str] = None
    contact_title: Optional[str] = None
    employee_estimate: Optional[int] = None
    distress_signal: Optional[str] = None
    financing_signal: Optional[str] = None
    bankruptcy_chapter: Optional[str] = None

    # Scoring explainability
    score_breakdown: list[dict[str, Any]] = Field(default_factory=list)
    score_reasons: list[str] = Field(default_factory=list)


class SearchFilters(BaseModel):
    """Per-run search preferences — controls what sources pull and what gets kept."""

    chapters: list[str] = Field(default_factory=lambda: ["13", "7"])
    lookback_days: int = 30
    include_individuals: bool = True  # Ch.13 individual filers with business signals
    # Industry focus filter — e.g. ["credit_extenders"]. Empty = no filter.
    company_types: list[str] = Field(default_factory=list)

    class Config:
        frozen = False


class SourceLog(BaseModel):
    """Tracks what each source produced."""

    source_name: str
    source_type: SourceType
    source_url: str = ""
    collected_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    leads_found: int = 0
    leads_kept: int = 0
    notes: str = ""


class DiscardRecord(BaseModel):
    """Records why a lead was discarded — carries full lead data for display."""

    # Discard metadata
    reason: str
    rule: str

    # Full lead fields (mirrors Lead — populated so discards can be displayed like kept leads)
    lead_id: str
    company_name: str
    lead_lane: str = ""
    portfolio_type: str = ""
    state: str = ""
    city: str = ""
    quality_tier: str = ""
    confidence_score: float = 0.0
    website: str = ""
    business_phone: str = ""
    reason_qualified: str = ""
    notes: str = ""
    source_type: str = ""
    source_url: str = ""
    named_contact: Optional[str] = None
    contact_title: Optional[str] = None
    employee_estimate: Optional[int] = None
    distress_signal: Optional[str] = None
    financing_signal: Optional[str] = None
    bankruptcy_chapter: Optional[str] = None
    private_company_confirmed: bool = False
    public_company_confirmed: bool = False
    trustee_related: bool = False
    collected_at: str = ""
