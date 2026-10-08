"""Infrastructure surface (engine-backed P14 surface).

Policy: 120-char trace payload on every turn; full prompt on the 16%
over-TTL queue turns and the 7% object-store snapshot turns.
"""
from __future__ import annotations

from .base import EngineSurface


class InfrastructureSurface(EngineSurface):
    id = "infrastructure"
    title = "Traces / queues / snapshots"


SURFACE = InfrastructureSurface()
POLICY = {"trace_chars": 120,
          "full_fractions": ["infra_queue@0.16", "infra_snapshot@0.07"]}
