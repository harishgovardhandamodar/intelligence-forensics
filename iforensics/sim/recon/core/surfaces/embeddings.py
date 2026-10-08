"""Embeddings surface (engine-backed P14 surface).

Policy: deterministic 384-d hash vector per prompt, no text ever. Text
accuracy is ALWAYS 0 — the only contribution is linkage: near-duplicate
prompts collapse into families so fragments found in text-bearing stores
can be lined up. Pure vector-to-text inversion is never claimed.
"""
from __future__ import annotations

from .base import EngineSurface


class EmbeddingsSurface(EngineSurface):
    id = "embeddings"
    title = "Query vectors"

    def text_accuracy(self) -> float:
        return 0.0


SURFACE = EmbeddingsSurface()
POLICY = {"dim": 384, "text_accuracy": 0.0,
          "contributes": "linkage (near-duplicate families)"}
