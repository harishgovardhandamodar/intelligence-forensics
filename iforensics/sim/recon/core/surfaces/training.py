"""Training surface (engine-backed P14 surface).

Policy: full prompt on the 14% eval/red-team-sampled turns and the 8%
pre-deletion staging turns. Long-window stores (30d eval, staging) — the
reason "stateless" products still train on your prompts.
"""
from __future__ import annotations

from .base import EngineSurface


class TrainingSurface(EngineSurface):
    id = "training"
    title = "Eval / staging"


SURFACE = TrainingSurface()
POLICY = {"full_fractions": ["training_eval@0.14", "training_staging@0.08"],
          "windows": ["eval 30d", "staging pre-deletion"]}
