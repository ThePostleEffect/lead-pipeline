"""Phone number normalization utilities."""

from __future__ import annotations

import re


def normalize_phone(phone: str) -> str:
    """Strip a US phone number to digits and format as XXX-XXX-XXXX."""
    digits = re.sub(r"\D", "", phone)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"{digits[:3]}-{digits[3:6]}-{digits[6:]}"
    return phone.strip()  # Return as-is if non-standard
