"""Rules endpoint — returns current pipeline rules configuration."""

from __future__ import annotations

from fastapi import APIRouter

from app.commands.rules_cmd import run_rules

router = APIRouter()


@router.get("")
def get_rules() -> dict:
    """Return the current lane/state/quality/scoring rules."""
    return run_rules()
