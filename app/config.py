"""Configuration loader — reads config/rules.yaml and provides defaults."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_DEFAULT_RULES_PATH = _PROJECT_ROOT / "config" / "rules.yaml"


def load_rules(path: Path | None = None) -> dict[str, Any]:
    """Load the rules YAML file and return as a dict."""
    path = path or _DEFAULT_RULES_PATH
    if not path.exists():
        raise FileNotFoundError(f"Rules file not found: {path}")
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def get_excluded_states(rules: dict[str, Any], lane: str) -> set[str]:
    """Return the set of excluded state abbreviations for a given lane."""
    lane_cfg = rules.get("lanes", {}).get(lane, {})
    return set(lane_cfg.get("excluded_states", []))


def get_scoring_weights(rules: dict[str, Any]) -> dict[str, int]:
    """Return the scoring weight map."""
    return rules.get("scoring", {}).get("weights", {})


def get_preferred_employee_range(rules: dict[str, Any]) -> tuple[int, int]:
    """Return (min, max) preferred employee count."""
    rng = rules.get("scoring", {}).get("preferred_employee_range", {})
    return rng.get("min", 10), rng.get("max", 50)


# Convenience: project paths
DATA_INPUT = _PROJECT_ROOT / "data" / "input"
DATA_OUTPUT = _PROJECT_ROOT / "data" / "output"
