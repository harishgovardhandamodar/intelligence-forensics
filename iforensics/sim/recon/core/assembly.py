"""Assembly: position-wise merge of secret-shaped spans (engine-backed).

Backed by the engine's structure attack (`score_texts`); this module names
the contract — recovered value + coverage fraction + confidence — and adds
the honesty gate: assembly without ground truth returns candidates only,
never a scored claim.
"""
from __future__ import annotations

from ... import reconstruction as _eng


def assemble(texts: list[str], truth: dict | None = None) -> dict:
    """Merge secret-shaped spans across a text pool.

    With truth: scored report (accuracy, recovered, fields). Without truth:
    unscored candidates straight from the structure attack — the insider
    sees shapes, not confirmation.
    """
    from ... import attacks
    if truth:
        rep = _eng.score_texts(list(texts), dict(truth))
        cands = rep.get("candidates", [])
    else:
        struct = attacks.structure_attack(list(texts))
        cands = struct.get("secrets", [])
        rep = {"fields": {}, "n_fields": 0, "recovered": 0,
               "mean_accuracy": 0.0}
    cov = ([c.get("coverage", 0.0) for c in cands] or [0.0])
    return {"recovered": rep.get("recovered", 0),
            "n_fields": rep.get("n_fields", 0),
            "mean_accuracy": rep.get("mean_accuracy", 0.0),
            "coverage": sum(cov) / len(cov),
            "confidence": rep.get("mean_accuracy", 0.0),
            "fields": rep.get("fields", {}),
            "candidates": cands,
            "scored": bool(truth)}
