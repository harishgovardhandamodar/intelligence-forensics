"""Accuracy analysis (P8.1): score reconstruction against ground truth.

The client registers each user's true secrets at scenario start; the server
compares assembled fragments position-wise. Metrics are character-level
(exact matches / secret length) and field-level (full-value recovery), plus
a progression curve: accuracy using only the first k queries, which is the
chart that shows leakage growing with repetition.
"""
from __future__ import annotations


def char_accuracy(assembled: str, truth: str) -> dict:
    """Position-wise comparison over the secret's alphanumeric slots."""
    if not truth:
        return {"accuracy": 0.0, "matched": 0, "total": 0, "recovered": False}
    total = sum(1 for c in truth if c.isalnum())
    matched = sum(1 for a, t in zip(assembled, truth)
                  if t.isalnum() and a == t)
    acc = round(matched / max(1, total), 3)
    return {"accuracy": acc, "matched": matched, "total": total,
            "recovered": acc >= 1.0}


def window_accuracy(assembled: str, truth: str) -> dict:
    """Best positional score of truth against any same-length window.

    Cluster assemblies are full sentences ("Ref: 123-45-6789 ..."), not bare
    secrets — slide the truth across and score the best fit, which is what
    "the value appears in the text" means forensically.
    """
    if not truth or not assembled or len(assembled) < len(truth):
        return char_accuracy(assembled, truth)
    best = {"accuracy": 0.0, "matched": 0, "total": 0, "recovered": False}
    for i in range(len(assembled) - len(truth) + 1):
        r = char_accuracy(assembled[i:i + len(truth)], truth)
        if r["accuracy"] > best["accuracy"]:
            best = r
    return best


def field_report(truth_fields: dict, assembled_by_field: dict,
                 scorer=None) -> dict:
    """Per-field accuracy + totals across one user's secrets."""
    scorer = scorer or char_accuracy
    fields = {}
    for field, truth in truth_fields.items():
        r = scorer(assembled_by_field.get(field, ""), truth)
        fields[field] = r
    n = len(fields)
    recovered = sum(1 for r in fields.values() if r["recovered"])
    mean_acc = round(sum(r["accuracy"] for r in fields.values()) / max(1, n), 3)
    return {"fields": fields, "n_fields": n, "recovered": recovered,
            "mean_accuracy": mean_acc}


def progression_curve(truth: str, masks_in_order: list[str],
                      assemble, scorer=None) -> list[dict]:
    """Accuracy after each prefix of the reveal schedule (for the chart)."""
    scorer = scorer or char_accuracy
    curve = []
    for k in range(1, len(masks_in_order) + 1):
        asm = assemble(masks_in_order[:k])
        r = scorer(asm["assembled"], truth)
        curve.append({"queries": k, "accuracy": r["accuracy"],
                      "recovered": r["recovered"]})
    return curve
