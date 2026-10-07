"""Shared simulation state (server side): store + truth registry.

Module-global SimState mirrors the LiveTap pattern: one lock-guarded holder
per process, resettable for tests. Ground truth lives here because the
client registers each user's secrets at scenario start (`/api/sim/begin`) —
the server can then score attacks without ever seeing real credentials
(all values are synthetic by construction).
"""
from __future__ import annotations

import threading

from .embeddings import HashEmbedder
from .gateway import MockGateway
from .store import NumpyStore


class SimState:
    """Embedder, vector store, gateway, and per-user ground truth."""

    def __init__(self, dim: int = 384):
        self.lock = threading.Lock()
        self.reset(dim=dim)
        self.backend_note = "numpy"

    def reset(self, dim: int = 384) -> dict:
        with self.lock:
            self.embedder = HashEmbedder(dim=dim)
            self.store = NumpyStore(dim=dim)
            self.gateway = MockGateway(self.store, self.embedder)
            self.truth: dict[str, dict] = {}
            self.backend_note = "numpy"
        return {"ok": True, "dim": dim}

    def use_milvus(self, url: str, collection: str = "llm_embeddings") -> dict:
        """Swap the backend when Milvus is reachable (compose `milvus` profile)."""
        from .store import connect
        with self.lock:
            store, note = connect(self.store.dim, collection)
            if note.startswith("milvus:"):
                self.store = store
                self.gateway = MockGateway(self.store, self.embedder)
                self.backend_note = note
                return {"ok": True, "backend": note}
            return {"ok": False, "backend": note}

    def register_truth(self, user_id: str, fields: dict) -> None:
        with self.lock:
            self.truth[user_id] = dict(fields)

    def get_truth(self, user_id: str) -> dict:
        with self.lock:
            return dict(self.truth.get(user_id, {}))

    def truth_users(self) -> list[str]:
        with self.lock:
            return sorted(self.truth)


STATE = SimState()
