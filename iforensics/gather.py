"""Discrete gatherer tasks (P7.29): one source, one timeout, retries.

`collect_all` reads every fox surface in one best-effort loop: a hung source
only logs `_error` and the run silently narrows, with no per-source timing.
Gatherers split that into independently schedulable units — runnable inline
(here, threaded with a hard timeout) or claimed by container workers through
the swarm queue (`swarm.enqueue("gather", {"source": ...})`, executed by
`cli.py swarm-worker`).

Large payloads (llm_requests pages) are spilled to
`evidence/swarm/results/<task_id>.json` when `artifact_dir` is set, so queue
result docs stay small summaries instead of megabyte blobs.
"""
from __future__ import annotations

import concurrent.futures as _fut
import json
import os
import time

GATHER_TIMEOUT_S = 60.0
GATHER_RETRIES = 1


def _sources():
    from . import fox_client, store
    return {
        "llm_requests": (fox_client.llm_requests, {"limit": 500}),
        "llm_queue": (fox_client.llm_queue, {}),
        "mesh_status": (fox_client.mesh_status, {}),
        "mesh_peers": (fox_client.mesh_peers, {}),
        "docker_projects": (fox_client.docker_projects, {}),
        "service_model": (fox_client.service_model, {"hours": 168}),
        "snapshot_db": (store.snapshot_db, {}),
    }


def gather_one(source: str, params: dict | None = None,
               timeout_s: float = GATHER_TIMEOUT_S,
               retries: int = GATHER_RETRIES,
               artifact_dir: str | None = None,
               task_id: str = "") -> dict:
    """Fetch one source with a hard timeout. Never raises — the envelope
    carries ok/data|error plus timing, so slow sources are visible."""
    try:
        fn, defaults = _sources()[source]
    except KeyError:
        return {"source": source, "ok": False, "data": None,
                "error": f"unknown source: {source!r}", "elapsed_s": 0.0,
                "attempts": 0}
    args = {**defaults, **(params or {})}
    last_error, elapsed = "no attempts", 0.0
    for attempt in range(1 + max(0, retries)):
        t0 = time.time()
        try:
            with _fut.ThreadPoolExecutor(max_workers=1) as ex:
                data = ex.submit(fn, **args).result(timeout=timeout_s)
            elapsed = round(time.time() - t0, 2)
            if source == "snapshot_db":
                data = {"src": data[0], "db_path": data[1]}
            if artifact_dir and task_id:
                os.makedirs(artifact_dir, exist_ok=True)
                apath = os.path.join(artifact_dir, f"{task_id}.json")
                with open(apath, "w", encoding="utf-8") as f:
                    json.dump(data, f, default=str)
                return {"source": source, "ok": True, "data": None,
                        "artifact": apath, "elapsed_s": elapsed,
                        "attempts": attempt + 1}
            return {"source": source, "ok": True, "data": data,
                    "elapsed_s": elapsed, "attempts": attempt + 1}
        except Exception as e:  # noqa: BLE001
            elapsed = round(time.time() - t0, 2)
            last_error = f"{type(e).__name__}: {e}"
    return {"source": source, "ok": False, "data": None, "error": last_error,
            "elapsed_s": elapsed, "attempts": 1 + max(0, retries)}


def gather_all(sources: list[str] | None = None,
               timeout_s: float = GATHER_TIMEOUT_S,
               max_workers: int = 4) -> dict:
    """Inline fan-out (dashboard/CLI/tests). Keys missing on failure."""
    from concurrent.futures import ThreadPoolExecutor, as_completed
    wanted = sources or list(_sources())
    out: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(gather_one, s, None, timeout_s, 0): s for s in wanted}
        for fut in as_completed(futs):
            try:
                out[futs[fut]] = fut.result()
            except Exception as e:  # noqa: BLE001
                out[futs[fut]] = {"source": futs[fut], "ok": False,
                                  "data": None, "error": str(e),
                                  "elapsed_s": 0.0, "attempts": 0}
    return out


def dispatch_gather(run_id: str, sources: list[str] | None = None,
                    base_dir: str | None = None) -> list[dict]:
    """Enqueue one swarm task per source for container workers (P7.32)."""
    from . import swarm as swarm_mod
    wanted = sources or [s for s in _sources() if s != "snapshot_db"]
    tasks = []
    for s in wanted:
        tasks.append(swarm_mod.enqueue("gather", {"source": s}, run_id=run_id,
                                       base_dir=base_dir))
    return tasks
