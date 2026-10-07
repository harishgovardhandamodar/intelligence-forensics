"""Evidence store: snapshot live API dump + a read-safe copy of the fox SQLite DB."""
import json
import os
import shutil
import sqlite3
import tempfile
import time

from . import config, fox_client


def snapshot_api(hours: int = 168, req_limit: int = 2000) -> tuple[str, dict]:
    os.makedirs(config.EVIDENCE_DIR, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    data = fox_client.collect_all(hours=hours, req_limit=req_limit)
    path = os.path.join(config.EVIDENCE_DIR, f"api_dump_{stamp}.json")
    with open(path, "w") as f:
        json.dump({"fox_url": config.FOX_URL, "stamp": stamp, **data}, f, indent=1, default=str)
    return path, data


def snapshot_db() -> tuple[str | None, str | None]:
    """Copy fox DB to evidence (avoids WAL/readonly lock issues). Returns (src, dst)."""
    src = config.find_fox_db()
    if not src:
        return None, None
    os.makedirs(config.EVIDENCE_DIR, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    dst = os.path.join(config.EVIDENCE_DIR, f"fox_services_{stamp}.db")
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp_path = tmp.name
    try:
        shutil.copyfile(src, tmp_path)
        # also try WAL sidecars if present (best effort)
        for ext in ("-wal", "-shm"):
            if os.path.exists(src + ext):
                try:
                    shutil.copyfile(src + ext, tmp_path + ext)
                except OSError:
                    pass
        shutil.move(tmp_path, dst)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass
    return src, dst


def normalize_row(r: dict) -> dict:
    """One canonical request-row shape for every source (fox API, sqlite DB,
    tap event). infer/report/timeseries all assume these keys, so a row read
    from the live buffer and one read from history must look identical —
    otherwise the same service profiles differently depending on provenance.
    """
    pt = r.get("prompt_tokens", 0) or 0
    ct = r.get("completion_tokens", 0) or 0
    total = r.get("total_tokens")
    return {
        "id": r.get("id") or r.get("request_id") or r.get("qid") or "",
        "ts": r.get("ts") or r.get("t") or r.get("created_at")
              or r.get("completed_at") or 0,
        "service": r.get("service") or "unknown",
        "model": r.get("model") or r.get("chosen_model") or "unknown",
        "original_model": r.get("original_model") or "",
        "prompt": r.get("prompt") or r.get("query") or r.get("prompt_head") or "",
        "prompt_tokens": pt,
        "completion_tokens": ct,
        "total_tokens": total if total is not None else (pt + ct),
        "duration_ms": r.get("duration_ms", 0) or 0,
        "queue_ms": r.get("queue_ms"),
        "status": r.get("status") or "complete",
        "query_type": r.get("query_type") or "",
        "requestor": r.get("requestor") or r.get("user") or r.get("client") or "user",
        "client_ip": r.get("client_ip") or "",
        "route_reason": r.get("route_reason") or "",
    }


def load_requests(db_path: str, limit: int = 5000) -> list[dict]:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            "SELECT id, ts, service, model, prompt_tokens, completion_tokens, total_tokens,"
            " duration_ms, queue_ms, status, prompt, request_id, client_ip,"
            " original_model, route_reason, query_type, requestor"
            " FROM llm_usage ORDER BY ts DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [normalize_row(dict(r)) for r in rows]
    finally:
        con.close()


def load_stats(db_path: str) -> dict:
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    try:
        n = con.execute("SELECT COUNT(*) c FROM llm_usage").fetchone()["c"]
        svcs = [dict(r) for r in con.execute(
            "SELECT service, COUNT(*) c, SUM(total_tokens) t FROM llm_usage GROUP BY service ORDER BY c DESC")]
        qts = [dict(r) for r in con.execute(
            "SELECT query_type, COUNT(*) c FROM llm_usage GROUP BY query_type ORDER BY c DESC")]
        return {"total": n, "by_service": svcs, "by_query_type": qts}
    finally:
        con.close()
