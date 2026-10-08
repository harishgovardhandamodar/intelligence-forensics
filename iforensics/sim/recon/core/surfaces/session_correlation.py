"""Session-correlation join keys (staged). 1/25 whole, 64-char keys."""
from __future__ import annotations
from .staged import StagedSurface
class SessionCorrelationSurface(StagedSurface):
    id = "session_correlation"; title = "Session correlation"
    rate_num = 1; rate_den = 25; head_chars = 64
SURFACE = SessionCorrelationSurface()
