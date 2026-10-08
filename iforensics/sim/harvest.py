"""Vector collection of residual records: harvest now, consume/attack later.

The eight residual surfaces keep their text whether or not anyone scores it,
so *collection* is decoupled from *reconstruction*:

  harvest — write-through on ingest: embed every text-bearing residual and
            append it to a named vector collection. Immediate, cheap, and it
            needs no ground truth — the analyst may not know yet which fields
            to score for.
  consume — later, on demand: read the collection back and run the attack
            against whatever ground truth has been registered by then.

The split is the whole point forensically. The collection is captured while
the provider still holds the records (evidence of retention, with provenance
per row); the attack is a separate, repeatable act that can be re-run with
different truth, different surfaces, or a tighter assembly strategy without
re-collecting anything.

Backend follows `store.connect()` — Milvus collection when $MILVUS_URL is
set and reachable, in-process NumpyStore otherwise, with the backend named
in every response so nobody mistakes a fallback for the real thing.
"""
from __future__ import annotations

import threading

from .embeddings import HashEmbedder
from .store import connect

STRATEGY = "harvest-now-consume-later"
STRATEGY_LABEL = "harvest now · consume / attack later"
DEFAULT_COLLECTION = "recon_residuals"
DIM = 384


class ResidualCollection:
    """Named vector collection with a two-phase (harvest → consume) API."""

    def __init__(self, name: str = DEFAULT_COLLECTION, dim: int = DIM):
        self.name = name
        self.dim = dim
        self.strategy = STRATEGY
        self.strategy_label = STRATEGY_LABEL
        self._lock = threading.Lock()
        # namespaced salt: this collection's vectors never collide with the
        # sim's own `iforensics-sim-v1` store even when both are in-process
        self.embedder = HashEmbedder(dim=dim, salt="iforensics-recon-v1")
        self.store, self.backend = connect(dim, name)
        self.harvested = 0
        self.consumed = 0
        self.last_user = ""
        self.by_user: dict[str, int] = {}
        self.last_attack: dict | None = None

    # -- harvest ----------------------------------------------------------- #

    def harvest(self, records: list[dict], user_id: str = "",
                run_id: str = "") -> int:
        """Write-through: embed and append every text-bearing residual."""
        rows = [r for r in records if (r.get("text") or "").strip()]
        if not rows:
            return 0
        texts = [r["text"] for r in rows]
        vectors = self.embedder.embed(texts)
        metas = [{"user_id": user_id or r.get("user_id") or "anonymous",
                  "run_id": run_id or r.get("run_id") or "",
                  "surface": r.get("surface") or "",
                  "kind": r.get("kind") or "",
                  "field": r.get("field") or "",
                  "turn": int(r.get("turn", -1)),
                  "record_id": r.get("id", -1)} for r in rows]
        ids = self.store.add(texts, vectors, metas)
        with self._lock:
            self.harvested += len(ids)
            for m in metas:
                self.by_user[m["user_id"]] = self.by_user.get(m["user_id"], 0) + 1
                self.last_user = m["user_id"]
        return len(ids)

    # -- consume ----------------------------------------------------------- #

    def rows(self, user_id: str = "") -> list[dict]:
        return self.store.get_all({"user_id": user_id} if user_id else None)

    def consume(self, user_id: str, truth: dict | None = None,
                attack: bool = True) -> dict:
        """Read the collection back; optionally score it against `truth`."""
        rows = self.rows(user_id)
        texts = [r.get("text") or "" for r in rows]
        texts = [t for t in texts if t]
        with self._lock:
            self.consumed += 1
            last_user = user_id
        out: dict = {"collection": self.name, "backend": self.backend,
                     "strategy": self.strategy,
                     "strategy_label": self.strategy_label,
                     "user_id": user_id, "records": len(rows),
                     "texts": len(texts), "attack": None,
                     "accuracy": None, "recovered": None, "n_fields": None}
        if not attack:
            out["note"] = "harvested rows returned without scoring"
            return out
        from .reconstruction import score_texts  # lazy: avoids an import cycle
        rep = score_texts(texts, truth or {})
        out["attack"] = rep
        out["accuracy"] = rep["mean_accuracy"]
        out["recovered"] = rep["recovered"]
        out["n_fields"] = rep["n_fields"]
        with self._lock:
            self.last_attack = {"user_id": last_user,
                                "accuracy": rep["mean_accuracy"],
                                "recovered": rep["recovered"],
                                "n_fields": rep["n_fields"],
                                "records": len(rows)}
        return out

    # -- bookkeeping ------------------------------------------------------- #

    def purge_user(self, user_id: str) -> int:
        """Drop one user's rows (a re-run of the same session must not
        double-harvest on top of last time's)."""
        n = self.store.delete({"user_id": user_id})
        with self._lock:
            self.by_user.pop(user_id, None)
            self.harvested = max(0, self.harvested - n)
            if self.last_user == user_id:
                self.last_user = next(iter(self.by_user), "")
        return n

    def clear(self) -> int:
        n = self.store.clear()
        with self._lock:
            self.harvested = 0
            self.by_user.clear()
            self.last_user = ""
            self.last_attack = None
        return n

    def stats(self) -> dict:
        with self._lock:
            return {"collection": self.name, "backend": self.backend,
                    "strategy": self.strategy,
                    "strategy_label": self.strategy_label,
                    "dim": self.dim, "harvested": self.harvested,
                    "consumed": self.consumed, "resident": len(self.store),
                    "users": len(self.by_user),
                    "by_user": dict(sorted(self.by_user.items())),
                    "last_user": self.last_user,
                    "last_attack": dict(self.last_attack) if self.last_attack
                    else None}
