"""Rate-limit / quota counters (staged). Counter keys only — never text."""
from __future__ import annotations
from .staged import StagedSurface
class RateLimitQuotaSurface(StagedSurface):
    id = "rate_limit_quota"; title = "Rate-limit counters"
    rate_num = 0; rate_den = 1; head_chars = 48
SURFACE = RateLimitQuotaSurface()
