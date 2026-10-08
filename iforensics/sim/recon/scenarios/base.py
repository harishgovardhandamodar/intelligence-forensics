"""Shared scenario base: engine-mapped or generic-builder workloads."""
from __future__ import annotations

from . import ENGINE_MAP, run_generic


class Scenario:
    """One enterprise workload. `run()` executes through the engine."""

    id = ""
    title = ""
    blurb = ""
    fields: list[str] = []
    carriers: list[str] = []
    engine_id: str | None = None  # set when it maps 1:1 onto an engine scenario

    @classmethod
    def run(cls, seed: int = 42, n: int = 48) -> dict:
        if cls.engine_id is not None:
            from ... import reconstruction as _eng
            return _eng.run_session(cls.engine_id, seed=seed, n=n)
        return run_generic(cls.id, list(cls.fields), list(cls.carriers),
                           seed=seed, n=n)
