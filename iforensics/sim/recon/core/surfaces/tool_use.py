"""Tool-use audit trail (staged). 1/12 calls whole, 160-char head."""
from __future__ import annotations
from .staged import StagedSurface
class ToolUseSurface(StagedSurface):
    id = "tool_use"; title = "Tool-use audit"
    rate_num = 1; rate_den = 12; head_chars = 160
SURFACE = ToolUseSurface()
