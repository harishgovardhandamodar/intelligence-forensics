"""Metrics: solo / cumulative / curves over `build_report` (engine-backed).

`solo()` scores each store alone. `cumulative()` scores growing prefixes —
monotone non-decreasing by construction (the text pool only ever grows).
`curves()` returns accuracy vs number of turns. Every number carries the
engine's honesty fields (recovered counts, caveats live in the report).
"""
from __future__ import annotations

from ... import reconstruction as _eng


def report(user_id: str) -> dict:
    """Full engine report for one user (requires registered truth)."""
    return _eng.build_report(_eng.STATE, user_id)


def solo(user_id: str) -> dict:
    """Per-surface accuracy, one store at a time."""
    rep = report(user_id)
    return {s["id"]: {"accuracy": s["accuracy"],
                       "recovered_fields": s["recovered_fields"],
                       "records": s["records"],
                       "text_records": s["text_records"]}
            for s in rep.get("surfaces", [])}


def cumulative(user_id: str) -> list[dict]:
    """Growing-prefix accuracies (monotone by construction)."""
    return list(report(user_id).get("cumulative", []))


def curves(user_id: str) -> dict:
    """Accuracy vs number of requests (repetition curves + amplification)."""
    rep = report(user_id)
    return {"curves": rep.get("curves", {}),
            "amplification": rep.get("amplification", {}),
            "mean_accuracy": rep.get("mean_accuracy", 0.0),
            "recovered": rep.get("recovered", 0),
            "n_fields": rep.get("n_fields", 0)}


def check_monotone(values: list[float]) -> bool:
    """The framework's core invariant: accuracy never steps down."""
    return all(b + 1e-12 >= a for a, b in zip(values, values[1:]))
