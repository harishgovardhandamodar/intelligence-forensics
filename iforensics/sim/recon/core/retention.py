"""Retention constants — re-exported from the engine, never copied.

`RATE`, `HEAD_CHARS`, `TRACE_CHARS`, `STORE_IDS`, `SURFACES` are the live
objects from `iforensics/sim/reconstruction.py`: one source of truth, so a
rate change in the engine is automatically the rate the framework reports.
`STAGED_RATES` covers surfaces not yet wired into the engine — deterministic
fractions of turn index with retention-window comments.
"""
from __future__ import annotations

from ...reconstruction import (  # noqa: F401  (re-export = the contract)
    HEAD_CHARS,
    RATE,
    STORE_IDS,
    SURFACES,
    TRACE_CHARS,
)

FRAG_CHARS = 90     # employee-pasted window around the secret (engine value)
PREFIX_MIN = 24     # cache-key prefix floor (engine value)


def surface_card(surface_id: str) -> dict:
    """Policy card for one engine surface: rate keys, truncation, role."""
    for s in SURFACES:
        if s["id"] == surface_id:
            return {"id": s["id"], "title": s.get("title", ""),
                    "role": s.get("role", ""), "retains": s.get("retains", ""),
                    "rate_keys": [k for k in RATE if k.startswith(
                        {"logging": "logging", "billing": "billing",
                         "training": "training",
                         "infrastructure": "infra"}.get(surface_id, "\0"))],
                    "truncation": {"logging": HEAD_CHARS,
                                   "infrastructure": TRACE_CHARS}.get(
                                       surface_id)}
    raise ValueError(f"unknown engine surface: {surface_id!r}")


# Staged surfaces: policy-complete here, engine rollout tracked separately.
# Each entry is (deterministic fraction of turns kept whole, head chars kept
# always, retention window note). Fractions are evaluated against the turn
# index (turn % denom < num), so they are bit-identical across processes.
STAGED_RATES = {
    "api_gateway":      {"full": (1, 20), "head": 200,
                         "window": "access-log sampling, 7d"},
    "tool_use":         {"full": (1, 12), "head": 160,
                         "window": "tool-call audit trail, 30d"},
    "session_correlation": {"full": (1, 25), "head": 64,
                            "window": "session-id join keys, 90d"},
    "backup_snapshot":  {"full": (1, 50), "head": 0,
                         "window": "nightly snapshots, 35d"},
    "rate_limit_quota": {"full": (0, 1), "head": 48,
                         "window": "counter keys only, 24h"},
    "apm_error":        {"full": (1, 15), "head": 220,
                         "window": "error traces with prompt echo, 14d"},
    "waf_dlp":          {"full": (1, 30), "head": 120,
                         "window": "matched-rule excerpts, 90d"},
    "product_analytics": {"full": (0, 1), "head": 80,
                          "window": "event properties, 13mo"},
    "feature_store":    {"full": (1, 40), "head": 0,
                         "window": "training features incl. raw text, 400d"},
    "rag_index":        {"full": (1, 8), "head": 512,
                         "window": "indexed chunks embed full turns, 400d"},
    "gpu_debug":        {"full": (1, 100), "head": 96,
                         "window": "NCCL / crash dumps, 3d"},
}
