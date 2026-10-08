"""APM / error traces with prompt echo (staged). 1/15 whole, 220-char head."""
from __future__ import annotations
from .staged import StagedSurface
class ApmErrorSurface(StagedSurface):
    id = "apm_error"; title = "APM error traces"
    rate_num = 1; rate_den = 15; head_chars = 220
SURFACE = ApmErrorSurface()
