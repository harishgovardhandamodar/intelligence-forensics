"""WAF / DLP matched-rule excerpts (staged). 1/30 whole, 120-char head."""
from __future__ import annotations
from .staged import StagedSurface
class WafDlpSurface(StagedSurface):
    id = "waf_dlp"; title = "WAF / DLP excerpts"
    rate_num = 1; rate_den = 30; head_chars = 120
SURFACE = WafDlpSurface()
