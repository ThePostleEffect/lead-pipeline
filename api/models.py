"""API request/response Pydantic schemas.

These wrap the pipeline's data models for HTTP transport.
They do NOT duplicate pipeline logic — they define the API contract.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------

class CollectRequest(BaseModel):
    lane: Literal["charged_off", "bankruptcy", "performing", "capital_seeking"]
    limit: int | None = None
    min_quality: Literal["best_case", "mid_level"] | None = None
    source_type: Literal["json", "csv", "web", "auto"] | None = None
    save_discards: bool = True
    export_xlsx: bool = False
    # Search filters
    chapters: str | None = None  # Comma-separated: "13,7"
    lookback_days: int | None = None
    include_individuals: bool | None = None
    company_types: str | None = None  # Comma-separated: "credit_extenders,auto_dealers"


class ExportRequest(BaseModel):
    run_id: str


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------

class RunResponse(BaseModel):
    run_id: str
    lane: str
    status: Literal["pending", "running", "completed", "failed"]
    created_at: str
    completed_at: str | None = None
    raw_signal_count: int | None = None
    kept_count: int | None = None
    discard_count: int | None = None
    output_json_path: str | None = None
    discard_json_path: str | None = None
    xlsx_path: str | None = None
    error: str | None = None


class RunListItem(BaseModel):
    run_id: str
    lane: str
    status: Literal["pending", "running", "completed", "failed"]
    created_at: str
    completed_at: str | None = None
    kept_count: int | None = None
    discard_count: int | None = None
