"""Base types for every residual surface in the framework.

`Turn` is the immutable input (one request). `Residual` is what the insider
can read back. `SurfacePolicy.retain()` is the deterministic retention
decision; engine-backed surfaces implement `read()` over `ReconState`
because their retention lives in `reconstruction._residuals` (single source
of truth — never duplicated here).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Turn:
    index: int
    user_id: str
    prompt: str
    field: str = ""
    mask: str = ""
    response: str = ""


@dataclass
class Residual:
    surface: str
    turn_id: int
    kind: str
    text: str = ""
    vector: list[float] | None = None
    linkage_key: str = ""
    meta: dict = field(default_factory=dict)

    @property
    def has_text(self) -> bool:
        return bool(self.text)


class SurfacePolicy(ABC):
    """One residual surface's retention contract."""

    id: str = ""
    title: str = ""
    staged: bool = False  # True = policy-complete here, not in the engine yet

    @abstractmethod
    def retain(self, turn: Turn) -> list[Residual]:
        """Deterministic retention decision for one turn (no RNG state)."""

    @abstractmethod
    def read(self, user_id: str = "") -> list[Residual]:
        """Residuals an insider holding this surface would see."""

    @abstractmethod
    def clear(self, user_id: str = "") -> int:
        """Drop held rows; return how many were dropped."""


class EngineSurface(SurfacePolicy):
    """Adapter over the engine's residual store for one P14 surface."""

    staged = False

    def retain(self, turn: Turn) -> list[Residual]:  # pragma: no cover
        raise NotImplementedError(
            f"{self.id}: retention lives in reconstruction._residuals — "
            "use the engine ingest path, never a copy")

    def read(self, user_id: str = "") -> list[Residual]:
        from ....reconstruction import STATE, residuals
        if not user_id:
            return []
        out = []
        for r in residuals(STATE, user_id, self.id or None)["records"]:
            out.append(Residual(surface=r["surface"], turn_id=r["turn"],
                                kind=r["kind"], text=r["text"] or "",
                                linkage_key=str(r["id"]), meta=r["meta"]))
        return out

    def clear(self, user_id: str = "") -> int:
        if not user_id:
            return 0
        from ....reconstruction import STATE
        return STATE.purge(user_id)
