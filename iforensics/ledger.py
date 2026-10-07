"""Auditable action ledger (P7.27): append-only, hash-chained, tamper-evident.

Every swarm action — task issued/claimed/completed/failed, artifact written,
LLM call made, human approval — is exactly one JSONL entry under
`evidence/ledger/<run_id>.jsonl`. Each entry commits to the previous entry's
hash, so silent edits, deletions, or reorderings are detectable by
recomputation (`verify`).

Sensitive text never enters the chain: prompts and findings live in the
referenced artifacts; the ledger carries SHA-256 hashes + pointers, so it can
be shown, diffed, and verified freely.

Entry shape:
    {seq, ts, run_id, actor, action, task_id, inputs_hash, artifact,
     artifact_sha256, detail, prev_hash, hash}

`hash` covers the whole entry minus itself (canonical JSON, sorted keys).
The genesis entry commits to `genesis:<run_id>`.
"""
from __future__ import annotations

import hashlib
import json
import os
import threading
import time

from . import config

LEDGER_DIRNAME = "ledger"
INDEX = "index.json"

_lock = threading.Lock()


def ledger_dir(base_dir: str | None = None) -> str:
    base = base_dir or config.EVIDENCE_DIR
    return base if os.path.basename(base) == LEDGER_DIRNAME else os.path.join(base, LEDGER_DIRNAME)


def _path(run_id: str, base_dir: str | None = None) -> str:
    return os.path.join(ledger_dir(base_dir), f"{run_id}.jsonl")


def _sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _entry_hash(entry: dict) -> str:
    body = {k: v for k, v in entry.items() if k != "hash"}
    return hashlib.sha256(
        json.dumps(body, sort_keys=True, separators=(",", ":"),
                   default=str).encode()).hexdigest()


def _read_all(path: str) -> list[dict]:
    out = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    out.append(json.loads(line))
    except FileNotFoundError:
        pass
    return out


def append(run_id: str, actor: str, action: str, task_id: str = "",
           inputs_hash: str = "", artifact: str = "",
           artifact_sha256: str = "", detail: str = "",
           base_dir: str | None = None) -> dict:
    """Append one action entry. Hashes the artifact file when it exists."""
    if artifact and not artifact_sha256 and os.path.isfile(artifact):
        try:
            artifact_sha256 = _sha256_file(artifact)
        except OSError:
            pass
    with _lock:
        path = _path(run_id, base_dir)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        prev = _read_all(path)
        entry = {
            "seq": len(prev) + 1,
            "ts": time.time(),
            "run_id": run_id,
            "actor": actor,
            "action": action,
            "task_id": task_id,
            "inputs_hash": inputs_hash,
            "artifact": artifact,
            "artifact_sha256": artifact_sha256,
            "detail": detail,
            "prev_hash": prev[-1]["hash"] if prev else f"genesis:{run_id}",
        }
        entry["hash"] = _entry_hash(entry)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, sort_keys=True, default=str) + "\n")
        _touch_index(run_id, path, base_dir)
        return entry


def _touch_index(run_id: str, path: str, base_dir: str | None = None) -> None:
    idx_path = os.path.join(ledger_dir(base_dir), INDEX)
    try:
        with open(idx_path, encoding="utf-8") as f:
            index = json.load(f)
        if not isinstance(index, dict):
            index = {}
    except (OSError, ValueError):
        index = {}
    index[run_id] = {"path": path, "updated_at": time.time()}
    try:
        with open(idx_path, "w", encoding="utf-8") as f:
            json.dump(index, f, indent=1, default=str)
    except OSError:
        pass


def read(run_id: str, base_dir: str | None = None) -> list[dict]:
    """All entries for a run, in chain order."""
    return _read_all(_path(run_id, base_dir))


def verify(run_id: str, base_dir: str | None = None) -> dict:
    """Recompute the chain. Tampering is reported at the exact seq."""
    entries = _read_all(_path(run_id, base_dir))
    if not entries:
        return {"run_id": run_id, "ok": False, "checked": 0,
                "error": "no ledger for run"}
    prev_hash = f"genesis:{run_id}"
    for i, e in enumerate(entries, start=1):
        if e.get("seq") != i or e.get("prev_hash") != prev_hash:
            return {"run_id": run_id, "ok": False, "checked": e.get("seq", 0),
                    "failed_at": e.get("seq"), "reason": "chain link broken"}
        if _entry_hash(e) != e.get("hash"):
            return {"run_id": run_id, "ok": False, "checked": e.get("seq", 0),
                    "failed_at": e.get("seq"), "reason": "entry hash mismatch"}
        prev_hash = e["hash"]
    return {"run_id": run_id, "ok": True, "checked": len(entries),
            "failed_at": None, "reason": ""}
