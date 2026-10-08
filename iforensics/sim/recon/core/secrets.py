"""Synthetic secrets: generators + reserved-range validators + TruthRegistry.

Backed by `iforensics/sim/sensitive.py` (the only generator). Validators
enforce the reserved/test ranges so a bug that emits a real-looking value
fails loudly instead of leaking into a report.
"""
from __future__ import annotations

import re

from ... import sensitive as _sens

# shape -> regex the value MUST match (reserved ranges only; the SSN
# generator emits the 9xx area, all of which SSA never issues)
RESERVED_PATTERNS = {
    "ssn": re.compile(r"^9\d{2}-\d{2}-\d{4}$"),
    "credit_card": re.compile(r"^4242( \d{4}){3}$"),
    "email": re.compile(r"^[^@\s]+@example\.com$"),
    "phone": re.compile(r"^555-\d{3}-\d{4}$"),
    "api_key": re.compile(r"^sk-test-[A-Za-z0-9]+$"),
    "deploy_token": re.compile(r"^(ghp_test_|sk-test-)[A-Za-z0-9_]+$"),
}

SHAPES = sorted(_sens.FIELD_GENERATORS)


def generate(field: str, seed: int | None = None) -> dict:
    """One synthetic value + sensitivity (delegates to sensitive.generate)."""
    return _sens.generate(field, seed)


def is_reserved(field: str, value: str) -> bool:
    """True when `value` is inside the reserved range for `field`.

    Fields without a strict pattern (names, companies, readings) are
    checked structurally: no 9-digit runs that could read as an SSN, no
    16-digit runs that could read as a PAN.
    """
    pat = RESERVED_PATTERNS.get(field)
    if pat is not None:
        return bool(pat.match(value or ""))
    v = value or ""
    if re.search(r"\b(?!9\d{2})\d{3}-\d{2}-\d{4}\b", v):
        return False
    if re.search(r"\b(?<!4242 )\d{16}\b", v.replace(" ", "")):
        return False
    return True


def check_reserved(mapping: dict) -> list[str]:
    """Fields in `mapping` whose values fall OUTSIDE the reserved ranges."""
    return [f for f, v in (mapping or {}).items()
            if not is_reserved(f, str(v))]


class TruthRegistry:
    """Ground truth for one run. The insider view never receives this."""

    def __init__(self) -> None:
        self._truth: dict[str, dict] = {}

    def register(self, user_id: str, fields: dict) -> None:
        bad = check_reserved(fields)
        if bad:
            raise ValueError(f"non-reserved synthetic values for: {bad}")
        self._truth[user_id] = dict(fields)

    def get(self, user_id: str) -> dict:
        return dict(self._truth.get(user_id, {}))

    def users(self) -> list[str]:
        return sorted(self._truth)
