"""Progressive attack: position-wise assembly over growing turn sets.

Reads the engine report's repetition curves — accuracy as turns accumulate.
Delegates entirely to `core.metrics.curves`; no independent scoring here.
"""
from __future__ import annotations

from ..core import metrics as _metrics


def progressive(user_id: str) -> dict:
    """Per-turn accuracy growth + pooled endpoint for one engine user."""
    c = _metrics.curves(user_id)
    return {"strategy": "progressive",
            "curves": c["curves"],
            "pooled_accuracy": c["amplification"].get("pooled_accuracy", 0.0),
            "mean_accuracy": c["mean_accuracy"],
            "recovered": c["recovered"], "n_fields": c["n_fields"]}
