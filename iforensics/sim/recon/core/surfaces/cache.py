"""Cache surface (engine-backed P14 surface).

Policy: exact-match hits keep the whole prompt; shared prefixes >= 24
chars keep the shared prefix; the newest KV snapshot lingers (only the
newest turn keeps one — re-ingest evicts the older snapshot).
"""
from __future__ import annotations

from .base import EngineSurface


class CacheSurface(EngineSurface):
    id = "cache"
    title = "Prompt / KV caches"


SURFACE = CacheSurface()
POLICY = {"exact_hit": "full prompt", "prefix_min": 24,
          "kv_linger": "newest turn only"}
