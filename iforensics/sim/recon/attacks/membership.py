"""Membership attack: does a candidate secret appear in the residual pool?

Pure presence test over the user's retained texts — substring match per
candidate. No scoring model, no confidence inflation: present or not.
"""
from __future__ import annotations

from ... import reconstruction as _eng


def membership(user_id: str, candidates: list[str]) -> dict:
    """Presence of each candidate in the user's pooled residual texts."""
    recs = _eng.STATE.records_for(user_id)
    pool = " ".join(r["text"] for r in recs if r["text"])
    hits = {c: (c in pool) for c in (candidates or [])}
    return {"strategy": "membership", "user_id": user_id,
            "n_texts": sum(1 for r in recs if r["text"]),
            "hits": hits,
            "n_hits": sum(1 for v in hits.values() if v)}
