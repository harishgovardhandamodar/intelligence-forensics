"""Linkage: near-duplicate families (engine-backed).

Backed by the engine's `_linkage` over the user's embedding vectors.
Vectors never yield text (accuracy stays 0); they yield family structure —
purity, coverage, family count — which is what lets an insider line up
fragments recovered from text-bearing stores.
"""
from __future__ import annotations

from ... import reconstruction as _eng


def families(user_id: str) -> dict:
    """Embedding family structure for one engine user (text accuracy: 0)."""
    recs = _eng.STATE.records_for(user_id)
    rep = _eng._linkage(recs)
    return {"text_accuracy": 0.0,
            "n_vectors": rep.get("n_vectors", 0),
            "n_families": rep.get("n_families", 0),
            "linked": rep.get("linked", 0),
            "linked_ratio": rep.get("linked_ratio", 0.0),
            "mean_cohesion": rep.get("mean_cohesion", 0.0)}
