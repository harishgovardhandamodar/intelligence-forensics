"""Leakage estimation (no ground truth required).

The report scores accuracy *against* registered truth — but a defender
watching a live log has no truth to compare against. `estimate_exposure`
answers the prior question from structure alone: given these texts, how
much secret material is recoverable in principle?

Per shape-group: `coverage` (fraction of slots filled by ≥1 fragment) is
the completeness estimate; `confidence` scales with independent
occurrences (one sighting could be a typo, three is a pattern). The user
exposure score is the max coverage — the worst secret present.
"""
from __future__ import annotations

from .attacks import structure_attack


def estimate_exposure(texts: list[str]) -> dict:
    """Exposure estimate without ground truth."""
    struct = structure_attack(texts or [])
    groups = []
    for s in struct["secrets"]:
        occ = s["occurrences"]
        confidence = round(min(1.0, occ / 3), 3)
        groups.append({"shape": s["shape"], "occurrences": occ,
                       "coverage": s["coverage"], "confidence": confidence,
                       "expected": s["coverage"]})
    exposure = max((g["coverage"] for g in groups), default=0.0)
    return {"groups": groups[:10], "n_groups": struct["n_groups"],
            "exposure": exposure}
