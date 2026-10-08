"""Logging surface (engine-backed P14 surface).

Policy: 180-char prompt head on every turn, full prompt on the 15%
safety-sampled turns, plus the completion. Retention lives in
`reconstruction._residuals` — this module is the policy card + reader.
"""
from __future__ import annotations

from .base import EngineSurface


class LoggingSurface(EngineSurface):
    id = "logging"
    title = "Observability logs"


SURFACE = LoggingSurface()
POLICY = {"head_chars": 180, "full_fraction": "logging_flagged@0.15",
          "also": ["completion verbatim"]}
