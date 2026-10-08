"""Human-ops surface (engine-backed P14 surface).

Policy: on turns carrying a masked secret, the 12% support-view turns keep
a 90-char window around the secret and the 5% paste turns keep the raw
value. No mask in the prompt → nothing retained: the strongest surface,
and the easiest to switch off.
"""
from __future__ import annotations

from .base import EngineSurface


class HumanOpsSurface(EngineSurface):
    id = "human_ops"
    title = "Support tooling"


SURFACE = HumanOpsSurface()
POLICY = {"window_chars": 90,
          "full_fractions": ["ops_view@0.12", "ops_paste@0.05"],
          "requires": "masked secret present in the prompt"}
