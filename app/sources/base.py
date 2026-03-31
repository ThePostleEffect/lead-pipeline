"""Abstract base class for all lead source collectors."""

from __future__ import annotations

from abc import ABC, abstractmethod

from app.models import Lead, SearchFilters, SourceLog


class BaseSource(ABC):
    """Every source collector must implement collect()."""

    name: str = "base"
    source_type: str = "manual"

    @abstractmethod
    def collect(self, lane: str, limit: int | None = None, filters: SearchFilters | None = None) -> tuple[list[Lead], SourceLog]:
        """Collect leads for the given lane.

        Returns:
            (leads, source_log)
        """
        ...
