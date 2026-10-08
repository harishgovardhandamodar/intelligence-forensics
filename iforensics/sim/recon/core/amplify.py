"""Amplification: pooled vs single-turn accuracy (engine-backed, analysis only).

Amplification is an analysis layer, never a store: it re-reads the same
residuals and compares judging each request alone against pooling every
request. Backed by the engine's report `amplification` block.
"""
from __future__ import annotations

from ... import reconstruction as _eng


def amplify(user_id: str) -> dict:
    """Amplification delta for one engine user (requires registered truth)."""
    rep = _eng.build_report(_eng.STATE, user_id)
    amp = rep.get("amplification", {})
    return {"single_query_accuracy": amp.get("single_query_accuracy", 0.0),
            "single_query_best": amp.get("single_query_best", 0.0),
            "pooled_accuracy": amp.get("pooled_accuracy", 0.0),
            "turns_pooled": amp.get("turns_pooled", 0),
            "delta": amp.get("delta", 0.0),
            "verdict": amp.get("verdict", "")}
