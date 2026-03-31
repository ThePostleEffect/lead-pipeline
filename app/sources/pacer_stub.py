"""PACER adapter — interface stub for future implementation.

PACER scraping is NOT implemented. This module defines the interface
so that a real PACER adapter can be dropped in later.
"""

from __future__ import annotations

import logging

from app.models import Lead, SourceLog, SourceType
from app.sources.base import BaseSource

logger = logging.getLogger(__name__)


class PacerSource(BaseSource):
    """Stub interface for PACER-based lead collection.

    When implemented, this adapter will:
    - authenticate with PACER
    - search bankruptcy filings
    - extract company & contact info
    - return normalized Lead objects
    """

    name = "pacer"
    source_type = "pacer"

    def collect(self, lane: str, limit: int | None = None) -> tuple[list[Lead], SourceLog]:
        logger.info("PacerSource is a stub — PACER integration not yet implemented")
        return [], SourceLog(
            source_name=self.name,
            source_type=SourceType.PACER,
            notes="Stub — PACER integration pending",
        )
