"""Staged surfaces: policy-complete here, engine rollout tracked separately.

A staged surface keeps a deterministic fraction of turns whole
(`turn.index % denom < num` — bit-identical across processes) plus a head
prefix on every turn, in its own in-memory store. `read()` is exactly what
an insider holding this surface would see. Nothing here touches the engine;
wiring a staged surface into `SURFACES` is a tracked rollout, never a
half-measure.
"""
from __future__ import annotations

from .base import Residual, SurfacePolicy, Turn


class StagedSurface(SurfacePolicy):
    staged = True
    rate_num = 0
    rate_den = 1
    head_chars = 0

    def __init__(self) -> None:
        self._store: list[Residual] = []

    def _keep_full(self, turn: Turn) -> bool:
        if self.rate_den <= 0 or self.rate_num <= 0:
            return False
        return (turn.index % self.rate_den) < self.rate_num

    def retain(self, turn: Turn) -> list[Residual]:
        out: list[Residual] = []
        if self._keep_full(turn):
            out.append(Residual(surface=self.id, turn_id=turn.index,
                                kind="full", text=turn.prompt,
                                linkage_key=f"{self.id}:{turn.index}:full",
                                meta={"window": "full-retention"}))
        elif self.head_chars > 0 and turn.prompt:
            out.append(Residual(surface=self.id, turn_id=turn.index,
                                kind="head", text=turn.prompt[:self.head_chars],
                                linkage_key=f"{self.id}:{turn.index}:head",
                                meta={"chars": min(self.head_chars,
                                                   len(turn.prompt))}))
        self._store.extend(out)
        return list(out)

    def read(self, user_id: str = "") -> list[Residual]:
        return list(self._store)

    def clear(self, user_id: str = "") -> int:
        n = len(self._store)
        self._store.clear()
        return n
