"""Swarm task queue (P7.32): file-based work distribution for isolated workers.

No broker to operate (house pattern: files under evidence/). Layout:

    evidence/swarm/queue/pending/<task_id>.json
    evidence/swarm/queue/claimed/<task_id>.json   (+ claimed_by, claimed_at)
    evidence/swarm/queue/done/<task_id>.json      (+ result)
    evidence/swarm/queue/failed/<task_id>.json    (+ error)

Claiming is an atomic `os.rename` — two workers racing for the same task
resolve to exactly one winner, on any shared volume (including across
containers). Crashed workers are recovered by mtime: a claim older than
`stale_s` is moved back to pending with `attempts` bumped, so no task is
ever stuck behind a dead container.
"""
from __future__ import annotations

import glob
import json
import os
import random
import time

try:
    import fcntl  # noqa — POSIX advisory locks for container workers
except ImportError:  # pragma: no cover — non-POSIX fallback
    fcntl = None  # type: ignore

STALE_S = 600
MAX_ATTEMPTS = 5


def queue_dir(base_dir: str | None = None) -> str:
    from . import config
    if base_dir is not None:
        base = base_dir
    else:
        base = os.environ.get("IF_SWARM_DIR") or config.EVIDENCE_DIR
    return base if os.path.basename(base) == "swarm" else os.path.join(base, "swarm")


def _dirs(base_dir: str | None = None) -> dict[str, str]:
    root = os.path.join(queue_dir(base_dir), "queue")
    dirs = {k: os.path.join(root, k) for k in ("pending", "claimed", "done", "failed")}
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)
    return dirs


def _write(path: str, doc: dict) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + f".tmp-{os.getpid()}"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(doc, f, indent=1, default=str)
    os.rename(tmp, path)


def _read(path: str) -> dict | None:
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def enqueue(kind: str, payload: dict | None = None, run_id: str = "",
            base_dir: str | None = None) -> dict:
    """Add a task. Returns the task doc (with task_id)."""
    task_id = f"t-{int(time.time())}-{random.randint(0, 0xFFFF):04x}"
    task = {"task_id": task_id, "run_id": run_id, "kind": kind,
            "payload": payload or {}, "created_at": time.time(), "attempts": 0}
    _write(os.path.join(_dirs(base_dir)["pending"], task_id + ".json"), task)
    return task


def _requeue_stale(dirs: dict[str, str], now: float, stale_s: float) -> int:
    recovered = 0
    for path in glob.glob(os.path.join(dirs["claimed"], "*.json")):
        try:
            if now - os.path.getmtime(path) > stale_s:
                task = _read(path) or {}
                task.pop("claimed_by", None)
                task.pop("claimed_at", None)
                _write(os.path.join(dirs["pending"], os.path.basename(path)), task)
                os.remove(path)
                recovered += 1
        except OSError:
            continue
    return recovered


def claim(worker: str, kinds: list[str] | None = None,
          base_dir: str | None = None, stale_s: float = STALE_S) -> dict | None:
    """Atomically claim one pending task (optionally filtered by kind).

    Returns the task doc with claimed_by/claimed_at, or None when the
    queue is empty. Losers of a race get FileNotFoundError internally and
    move on to the next candidate.
    """
    dirs = _dirs(base_dir)
    now = time.time()
    _requeue_stale(dirs, now, stale_s)
    try:
        names = sorted(os.listdir(dirs["pending"]))
    except OSError:
        return None
    for name in names:
        if not name.endswith(".json"):
            continue
        src = os.path.join(dirs["pending"], name)
        dst = os.path.join(dirs["claimed"], name)
        try:
            os.rename(src, dst)  # atomic winner election
        except OSError:
            continue  # lost the race (or a requeue moved it) — next candidate
        task = _read(dst) or {"task_id": name[:-5]}
        if kinds and task.get("kind") not in kinds:
            try:
                os.rename(dst, src)  # not ours — put it back, keep looking
            except OSError:
                pass
            continue
        task["attempts"] = task.get("attempts", 0) + 1
        task["claimed_by"] = worker
        task["claimed_at"] = now
        try:
            _write(dst, task)
        except OSError:
            return None
        return task
    return None


def complete(task_id: str, result: dict | None = None,
             base_dir: str | None = None) -> bool:
    """Move a claimed task to done with its result summary."""
    dirs = _dirs(base_dir)
    src = os.path.join(dirs["claimed"], task_id + ".json")
    task = _read(src)
    if task is None:
        return False
    task["result"] = result or {}
    task["completed_at"] = time.time()
    try:
        _write(os.path.join(dirs["done"], task_id + ".json"), task)
        os.remove(src)
        return True
    except OSError:
        return False


def fail(task_id: str, error: str, base_dir: str | None = None,
         requeue: bool = True) -> bool:
    """Record a failure; optionally return the task to pending for retry."""
    dirs = _dirs(base_dir)
    src = os.path.join(dirs["claimed"], task_id + ".json")
    task = _read(src)
    if task is None:
        return False
    task["error"] = error
    task["failed_at"] = time.time()
    try:
        if requeue and task.get("attempts", 0) < MAX_ATTEMPTS:
            task.pop("claimed_by", None)
            task.pop("claimed_at", None)
            _write(os.path.join(dirs["pending"], task_id + ".json"), task)
        else:
            _write(os.path.join(dirs["failed"], task_id + ".json"), task)
        os.remove(src)
        return True
    except OSError:
        return False


def status(base_dir: str | None = None) -> dict:
    """Queue depths per state (for the dashboard / orchestrator)."""
    dirs = _dirs(base_dir)
    out = {}
    for state, d in dirs.items():
        try:
            out[state] = len([f for f in os.listdir(d) if f.endswith(".json")])
        except OSError:
            out[state] = 0
    return out


# ------------------------------------------------------------------ registry
# Disk-backed run registry (P7.30): replaces the in-process _RUNS global so a
# dashboard restart no longer loses background runs, and container workers
# see the same state. One JSON doc; fcntl-guarded like the ledger.

def _registry_path() -> str:
    from . import config
    return os.path.join(config.EVIDENCE_DIR, "agentic", "registry.json")


def _locked_registry():
    """Read the registry; an unreadable file is an empty registry, never a crash."""
    path = _registry_path()
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_registry(reg: dict) -> None:
    path = _registry_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a+", encoding="utf-8") as f:
        if fcntl is not None:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            except OSError:
                pass
        try:
            f.seek(0)
            raw = f.read()
            try:
                disk = json.loads(raw) if raw.strip() else {}
            except ValueError:
                disk = {}
            if isinstance(disk, dict):
                reg = {**disk, **reg}
            f.seek(0)
            f.truncate()
            json.dump(reg, f, indent=1, default=str)
        finally:
            if fcntl is not None:
                try:
                    fcntl.flock(f.fileno(), fcntl.LOCK_UN)
                except OSError:
                    pass


def register_run(run_key: str, info: dict | None = None) -> dict:
    """Record a background run (merge over any existing entry)."""
    reg = _locked_registry()
    entry = {"status": "running", "started": time.time(), **(info or {})}
    reg[run_key] = {**reg.get(run_key, {}), **entry, "updated": time.time()}
    _write_registry(reg)
    return reg[run_key]


def update_run(run_key: str, info: dict) -> dict:
    """Merge new fields into a run entry (status transitions live here)."""
    reg = _locked_registry()
    reg[run_key] = {**reg.get(run_key, {}), **info, "updated": time.time()}
    _write_registry(reg)
    return reg[run_key]


def get_run(run_key: str) -> dict:
    """One run entry; unknown keys report as unknown (dashboard contract)."""
    return dict(_locked_registry().get(run_key, {"status": "unknown"}))


def all_runs() -> dict:
    """Every registry entry (for pending-run listing)."""
    reg = _locked_registry()
    return dict(reg) if isinstance(reg, dict) else {}


def recoverable_tasks(run_id: str, base_dir: str | None = None) -> list[dict]:
    """Pending + claimed queue tasks for a run: what a crash left behind.

    Claimed tasks belong to a presumably dead worker; the caller can requeue
    them (via fail(requeue=True)) or leave them for stale recovery.
    """
    dirs = _dirs(base_dir)
    out = []
    for state in ("pending", "claimed"):
        try:
            names = sorted(os.listdir(dirs[state]))
        except OSError:
            continue
        for name in names:
            if not name.endswith(".json"):
                continue
            task = _read(os.path.join(dirs[state], name)) or {}
            if task.get("run_id") == run_id:
                task["_state"] = state
                out.append(task)
    return out


def collect_results(task_ids: list[str], timeout_s: float = 900.0,
                    poll_s: float = 2.0,
                    base_dir: str | None = None) -> dict:
    """Wait for dispatched tasks to land in done/failed. Never raises.

    Returns {"done": {task_id: result}, "failed": {task_id: error},
    "missing": [task_id]} — the orchestrator turns missing/failed into the
    same per-service error entries the threaded path produces, so a dead
    worker degrades a run exactly like a raised exception does.
    """
    import time as _time
    dirs = _dirs(base_dir)
    want = set(task_ids)
    done: dict[str, dict] = {}
    failed: dict[str, str] = {}
    deadline = _time.time() + max(1.0, timeout_s)
    while want and _time.time() < deadline:
        for tid in sorted(want):
            for state, store in (("done", done), ("failed", failed)):
                path = os.path.join(dirs[state], tid + ".json")
                task = _read(path)
                if task is not None:
                    store[tid] = task.get("result", {}) if state == "done" \
                        else task.get("error", "unknown failure")
                    want.discard(tid)
                    break
        if want:
            _time.sleep(min(poll_s, max(0.1, deadline - _time.time())))
    return {"done": done, "failed": failed, "missing": sorted(want)}
