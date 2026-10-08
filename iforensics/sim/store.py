"""Embedding stores (P8.1): one interface, two backends.

`NumpyStore` is the default: in-memory list + exact cosine search with
metadata filtering. No dependencies, hermetic tests, survives Milvus being
down. `MilvusStore` wraps pymilvus when installed *and* reachable; otherwise
`connect()` falls back to `NumpyStore` and says so in the returned note —
the same degradation rule the tap uses for fox.
"""
from __future__ import annotations

import os
import threading

from .embeddings import cosine


class NumpyStore:
    """In-memory vector store with metadata filtering."""

    def __init__(self, dim: int = 384):
        self.dim = dim
        self._lock = threading.Lock()
        self._items: list[dict] = []
        self._seq = 0

    def add(self, texts: list[str], vectors: list[list[float]],
            metadatas: list[dict]) -> list[int]:
        ids = []
        with self._lock:
            for text, vec, meta in zip(texts, vectors, metadatas):
                if len(vec) != self.dim:
                    raise ValueError(
                        f"dim mismatch: store={self.dim} vector={len(vec)}")
                self._seq += 1
                self._items.append({"id": self._seq, "text": text,
                                    "vector": list(vec), "metadata": dict(meta)})
                ids.append(self._seq)
        return ids

    def _match(self, meta: dict, filtr: dict | None) -> bool:
        return not filtr or all(meta.get(k) == v for k, v in filtr.items())

    def search(self, vector: list[float], top_k: int = 10,
               filtr: dict | None = None) -> list[dict]:
        with self._lock:
            scored = [(cosine(vector, it["vector"]), it)
                      for it in self._items if self._match(it["metadata"], filtr)]
        scored.sort(key=lambda p: -p[0])
        return [{"id": it["id"], "text": it["text"], "score": round(s, 4),
                 "metadata": dict(it["metadata"])} for s, it in scored[:top_k]]

    def get_all(self, filtr: dict | None = None) -> list[dict]:
        with self._lock:
            return [{"id": it["id"], "text": it["text"],
                     "metadata": dict(it["metadata"])}
                    for it in self._items if self._match(it["metadata"], filtr)]

    def texts_vectors(self, filtr: dict | None = None) -> tuple[list, list]:
        """Parallel (texts, vectors) for attack math, filtered alike."""
        with self._lock:
            rows = [(it["text"], list(it["vector"])) for it in self._items
                    if self._match(it["metadata"], filtr)]
        return [r[0] for r in rows], [r[1] for r in rows]

    def delete(self, filtr: dict | None = None) -> int:
        """Drop rows matching `filtr` (none == every row). Returns the count."""
        with self._lock:
            if not filtr:
                n = len(self._items)
                self._items.clear()
                return n
            kept = [it for it in self._items
                    if not self._match(it["metadata"], filtr)]
            n = len(self._items) - len(kept)
            self._items = kept
            return n

    def clear(self) -> int:
        with self._lock:
            n = len(self._items)
            self._items.clear()
            return n

    def __len__(self) -> int:
        with self._lock:
            return len(self._items)


class MilvusStore:
    """pymilvus wrapper (spec schema: id/vector/text/metadata/timestamp)."""

    @staticmethod
    def _expr(filtr: dict | None) -> str:
        if not filtr:
            return "id >= 0"
        parts = [f'metadata["{k}"] == "{v}"' if isinstance(v, str)
                 else f'metadata["{k}"] == {v}' for k, v in filtr.items()]
        return " && ".join(["id >= 0"] + parts)

    def __init__(self, url: str, collection: str, dim: int):
        try:
            from pymilvus import (Collection, CollectionSchema, DataType,
                                  FieldSchema, connections, utility)
        except ImportError as e:
            raise RuntimeError("pymilvus not installed") from e
        host, _, port = url.rpartition(":")
        connections.connect("iforensics-sim", host=host or "localhost",
                            port=port or "19530")
        fields = [
            FieldSchema(name="id", dtype=DataType.INT64, is_primary=True,
                        auto_id=True),
            FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
            FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
            FieldSchema(name="metadata", dtype=DataType.JSON),
            FieldSchema(name="timestamp", dtype=DataType.INT64),
        ]
        self._collection = Collection(name=collection,
                                      schema=CollectionSchema(fields=fields))
        if not utility.has_collection(collection):
            self._collection.create_index(
                "embedding", {"index_type": "IVF_FLAT", "metric_type": "IP",
                              "params": {"nlist": 128}})
        self._collection.load()
        self.dim = dim

    def add(self, texts, vectors, metadatas) -> list[int]:
        import time
        now = int(time.time())
        res = self._collection.insert([
            [list(map(float, v)) for v in vectors], list(texts),
            [dict(m) for m in metadatas], [now] * len(texts)])
        self._collection.flush()
        return list(res.primary_keys)

    def search(self, vector, top_k=10, filtr=None) -> list[dict]:
        expr = None if not filtr else self._expr(filtr)
        hits = self._collection.search(
            [list(map(float, vector))], "embedding",
            {"metric_type": "IP", "params": {"nprobe": 16}}, limit=top_k,
            expr=expr, output_fields=["text", "metadata"])[0]
        return [{"id": h.id, "text": h.entity.get("text"),
                 "score": round(float(h.score), 4),
                 "metadata": dict(h.entity.get("metadata") or {})} for h in hits]

    def get_all(self, filtr=None) -> list[dict]:
        rows = self._collection.query(self._expr(filtr),
                                      output_fields=["text", "metadata"],
                                      limit=16384)
        return [{"id": r["id"], "text": r["text"],
                 "metadata": dict(r.get("metadata") or {})} for r in rows]

    def delete(self, filtr=None) -> int:
        n = len(self.get_all(filtr))
        self._collection.delete(self._expr(filtr))
        return n

    def clear(self) -> int:
        n = len(self.get_all())
        self._collection.delete("id >= 0")
        return n

    def __len__(self) -> int:
        return len(self.get_all())


def connect(dim: int = 384, collection: str = "llm_embeddings") -> tuple:
    """Milvus when $MILVUS_URL is set and reachable, else NumpyStore.

    Returns (store, note) where note names the backend in use.
    """
    url = os.environ.get("MILVUS_URL", "")
    if url:
        try:
            return MilvusStore(url, collection, dim), f"milvus:{url}"
        except Exception as e:  # noqa: BLE001 — fall back, never crash
            return NumpyStore(dim), f"numpy (milvus unreachable: {e})"
    return NumpyStore(dim), "numpy (no MILVUS_URL)"
