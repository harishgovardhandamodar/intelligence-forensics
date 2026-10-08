"""Near-duplicate attack: linkage families + assembly.

Joins `core.linkage.families` (which turns collapse together) with
`core.assembly.assemble` over the pooled text (what the joined turns give
up). The linkage half never yields text — accuracy 0 there by construction.
"""
from __future__ import annotations

from ... import reconstruction as _eng
from ..core import assembly as _assembly
from ..core import linkage as _linkage


def near_dup(user_id: str) -> dict:
    """Family structure + pooled assembly for one engine user."""
    recs = _eng.STATE.records_for(user_id)
    texts = [r["text"] for r in recs if r["text"]]
    truth = _eng.STATE.get_truth(user_id)
    fam = _linkage.families(user_id)
    asm = _assembly.assemble(texts, truth or None)
    return {"strategy": "near-dup", "families": fam["n_families"],
            "linked_ratio": fam["linked_ratio"],
            "mean_cohesion": fam["mean_cohesion"],
            "mean_accuracy": asm["mean_accuracy"],
            "recovered": asm["recovered"], "n_fields": asm["n_fields"]}
