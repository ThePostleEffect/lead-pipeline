"""US state validation and normalization."""

from __future__ import annotations

VALID_STATES: set[str] = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
    "DC",
}


def normalize_state(state: str) -> str:
    """Return the two-letter uppercase abbreviation or the original string."""
    abbr = state.strip().upper()
    if abbr in VALID_STATES:
        return abbr
    return state.strip()


def is_valid_state(state: str) -> bool:
    return state.strip().upper() in VALID_STATES
