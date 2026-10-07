"""Embedding backends (P8.1): same interface, two fidelities.

`HashEmbedder` (default): deterministic char-n-gram hashing into a fixed
vector, L2-normalized. No dependencies, seeded salt, stable across runs —
near-duplicates score higher than unrelated texts, which is all the attack
math needs. `SentenceTransformerBackend`: optional `sentence_transformers`
model when installed (heavy: torch); identical API for honest comparisons.
"""
from __future__ import annotations

import hashlib
import math
import re

_WORD = re.compile(r"[a-z0-9]+")


def _ngrams(text: str, n: int = 4):
    toks = _WORD.findall(text.lower())
    grams = []
    for tok in toks:
        padded = f"^{tok}$"
        grams.extend(padded[i:i + n] for i in range(max(1, len(padded) - n + 1)))
    return grams or ["^$"]


class HashEmbedder:
    """Deterministic sparse-hash embedding. `salt` namespaces stores."""

    def __init__(self, dim: int = 384, salt: str = "iforensics-sim-v1"):
        self.dim = dim
        self.salt = salt

    def embed(self, texts: list[str]) -> list[list[float]]:
        out = []
        for text in texts:
            vec = [0.0] * self.dim
            for g in _ngrams(text or ""):
                h = int(hashlib.sha256((self.salt + g).encode()).hexdigest(), 16)
                vec[h % self.dim] += 1.0
            norm = math.sqrt(sum(v * v for v in vec)) or 1.0
            out.append([v / norm for v in vec])
        return out

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


class SentenceTransformerBackend:
    """Optional real model (`pip install sentence-transformers`)."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise RuntimeError(
                "sentence-transformers not installed; use HashEmbedder") from e
        self._model = SentenceTransformer(model_name)
        self.dim = self._model.get_sentence_embedding_dimension()

    def embed(self, texts: list[str]) -> list[list[float]]:
        vecs = self._model.encode(list(texts), normalize_embeddings=True)
        return [list(map(float, v)) for v in vecs]

    def embed_one(self, text: str) -> list[float]:
        return self.embed([text])[0]


def cosine(a: list[float], b: list[float]) -> float:
    """Cosine similarity (inputs are L2-normalized by both backends)."""
    if len(a) != len(b) or not a:
        return 0.0
    return sum(x * y for x, y in zip(a, b))
