"""RAG index chunks (staged). 1/8 turns embedded whole, 512-char head."""
from __future__ import annotations
from .staged import StagedSurface
class RagIndexSurface(StagedSurface):
    id = "rag_index"; title = "RAG index"
    rate_num = 1; rate_den = 8; head_chars = 512
SURFACE = RagIndexSurface()
