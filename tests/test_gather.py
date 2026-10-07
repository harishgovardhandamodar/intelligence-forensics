"""Unit tests for discrete gatherer tasks (P7.29)."""
import json
import os
import time

from iforensics import gather as gather_mod


def test_gather_one_ok_and_unknown(monkeypatch):
    from iforensics import fox_client
    monkeypatch.setattr(fox_client, "llm_queue", lambda: {"pending": [1, 2]})
    out = gather_mod.gather_one("llm_queue")
    assert out == {"source": "llm_queue", "ok": True, "data": {"pending": [1, 2]},
                   "elapsed_s": out["elapsed_s"], "attempts": 1}
    bad = gather_mod.gather_one("nope")
    assert bad["ok"] is False and "unknown source" in bad["error"]


def test_gather_one_timeout_and_retry(monkeypatch):
    from iforensics import fox_client
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) == 1:
            time.sleep(5)
        return {"ok": True}

    monkeypatch.setattr(fox_client, "llm_queue", flaky)
    out = gather_mod.gather_one("llm_queue", timeout_s=0.2, retries=1)
    assert out["ok"] is True and out["attempts"] == 2

    def always_slow():
        time.sleep(5)
        return {"ok": True}

    monkeypatch.setattr(fox_client, "llm_queue", always_slow)
    out2 = gather_mod.gather_one("llm_queue", timeout_s=0.05, retries=0)
    assert out2["ok"] is False and out2["attempts"] == 1
    assert "imeout" in out2["error"]


def test_gather_one_error_envelope(monkeypatch):
    from iforensics import fox_client

    def boom():
        raise ConnectionError("down")
    monkeypatch.setattr(fox_client, "llm_queue", boom)
    out = gather_mod.gather_one("llm_queue", retries=1)
    assert out["ok"] is False
    assert out["error"] == "ConnectionError: down"
    assert out["attempts"] == 2


def test_gather_artifact_spill(tmp_path, monkeypatch):
    from iforensics import fox_client
    monkeypatch.setattr(fox_client, "llm_queue", lambda: {"pending": list(range(50))})
    out = gather_mod.gather_one("llm_queue", artifact_dir=str(tmp_path),
                                task_id="t-1")
    assert out["ok"] is True and out["data"] is None
    assert out["artifact"] == os.path.join(str(tmp_path), "t-1.json")
    assert len(json.load(open(out["artifact"]))) == 1


def test_gather_all_and_dispatch(tmp_path, monkeypatch):
    from iforensics import fox_client
    monkeypatch.setattr(fox_client, "llm_queue", lambda: {"a": 1})

    def mesh_down():
        raise RuntimeError("mesh down")
    monkeypatch.setattr(fox_client, "mesh_status", mesh_down)
    out = gather_mod.gather_all(["llm_queue", "mesh_status"])
    assert out["llm_queue"]["ok"] is True
    assert out["mesh_status"]["ok"] is False
    assert out["mesh_status"]["error"] == "RuntimeError: mesh down"
    tasks = gather_mod.dispatch_gather("r1", ["llm_queue", "mesh_status"],
                                       base_dir=str(tmp_path))
    assert [t["kind"] for t in tasks] == ["gather", "gather"]
    assert all(t["run_id"] == "r1" for t in tasks)
