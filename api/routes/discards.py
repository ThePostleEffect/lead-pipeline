"""Global discards vault endpoint — rolling 100 most recent discards across all runs."""

from __future__ import annotations

from fastapi import APIRouter

from api.run_store import get_global_discards

router = APIRouter()


@router.get("")
def list_global_discards() -> list[dict]:
    """Return the rolling vault of up to 100 most recent discards across all runs."""
    return get_global_discards()
