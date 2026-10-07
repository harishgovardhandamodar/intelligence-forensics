"""Unit tests for the canonical request-row shape (store.normalize_row)."""
import sqlite3

from iforensics.store import normalize_row, load_requests

CANON = {"id", "ts", "service", "model", "original_model", "prompt",
         "prompt_tokens", "completion_tokens", "total_tokens", "duration_ms",
         "queue_ms", "status", "query_type", "requestor", "client_ip",
         "route_reason"}


def test_normalize_db_row_keeps_total():
    r = normalize_row({"id": 7, "ts": 100.0, "service": "s", "model": "m",
                       "prompt_tokens": 10, "completion_tokens": 5,
                       "total_tokens": 20, "duration_ms": 3.5, "status": "ok",
                       "prompt": "hi", "requestor": "cron", "queue_ms": 12.0})
    assert set(r) == CANON
    assert r["id"] == 7 and r["total_tokens"] == 20
    assert r["requestor"] == "cron" and r["queue_ms"] == 12.0


def test_normalize_computes_missing_total():
    r = normalize_row({"id": 1, "prompt_tokens": 4, "completion_tokens": 6})
    assert r["total_tokens"] == 10
    assert r["service"] == "unknown" and r["model"] == "unknown"
    assert r["status"] == "complete" and r["requestor"] == "user"
    assert r["queue_ms"] is None


def test_normalize_fox_api_aliases():
    r = normalize_row({"request_id": "q1", "created_at": 50.0,
                       "chosen_model": "llama", "query": "prompt text",
                       "prompt_tokens": 3, "completion_tokens": 2})
    assert r["id"] == "q1" and r["ts"] == 50.0
    assert r["model"] == "llama" and r["prompt"] == "prompt text"


def test_normalize_tap_event():
    ev = {"seq": 5, "t": 9.0, "dir": "out", "service": "svc", "model": "m",
          "prompt_head": "head", "prompt_tokens": 1, "completion_tokens": 2,
          "qid": 42, "queue_ms": 7.0, "status": "ok"}
    r = normalize_row(ev)
    assert r["id"] == 42 and r["prompt"] == "head"
    assert r["total_tokens"] == 3 and r["queue_ms"] == 7.0


def _makedb(path):
    con = sqlite3.connect(path)
    con.execute(
        "CREATE TABLE llm_usage (id INTEGER, ts REAL, service TEXT, model TEXT,"
        " prompt_tokens INT, completion_tokens INT, total_tokens INT,"
        " duration_ms REAL, queue_ms REAL, status TEXT, prompt TEXT,"
        " request_id TEXT, client_ip TEXT, original_model TEXT,"
        " route_reason TEXT, query_type TEXT, requestor TEXT)")
    con.execute("INSERT INTO llm_usage VALUES (1,100,'a','m',10,5,15,2,1,"
                "'ok','p','r1','1.2.3.4','','r','qa','user')")
    con.execute(
        "INSERT INTO llm_usage VALUES (2,200,'a','m',0,0,NULL,NULL,NULL,NULL,"
        " 'p2','r2','','','','','')")
    con.commit()
    con.close()


def test_load_requests_canonical_and_computed_total(tmp_path):
    db = str(tmp_path / "x.db")
    _makedb(db)
    rows = load_requests(db)
    assert all(set(r) == CANON for r in rows)
    # ordered by ts DESC -> the ts=200 row (NULL total -> 0) first
    assert rows[0]["id"] == 2 and rows[0]["total_tokens"] == 0
    # NULL total with zero tokens normalises to 0, never None
    assert rows[-1]["id"] == 1 and rows[-1]["total_tokens"] == 15
    assert all(r["total_tokens"] is not None for r in rows)


def test_load_requests_respects_limit(tmp_path):
    db = str(tmp_path / "x.db")
    _makedb(db)
    assert len(load_requests(db, limit=1)) == 1