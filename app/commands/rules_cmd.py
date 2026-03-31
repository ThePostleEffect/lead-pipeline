"""rules command — print current lane/state/quality/discard rules."""

from __future__ import annotations

import json

from app.config import load_rules


def run_rules() -> dict:
    """Load and print the current rules configuration."""
    rules = load_rules()

    output = {
        "lanes": {},
        "discard_rules": rules.get("discard_rules", []),
        "quality_tiers": rules.get("quality", {}),
        "scoring_weights": rules.get("scoring", {}).get("weights", {}),
        "preferred_employee_range": rules.get("scoring", {}).get("preferred_employee_range", {}),
    }

    for lane_name, lane_cfg in rules.get("lanes", {}).items():
        output["lanes"][lane_name] = {
            "description": lane_cfg.get("description", ""),
            "excluded_states": lane_cfg.get("excluded_states", []),
        }

    print(json.dumps(output, indent=2))
    return output
