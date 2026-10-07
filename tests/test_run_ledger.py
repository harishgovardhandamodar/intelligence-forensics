"""Unit tests for run ledger instrumentation (P7.28)."""
import os

from iforensics import agents as ag
from iforensics import ledger as led


def _rows():
    return [
        {"id": "1", "service": "svc-a", "model": "m",
         "prompt": "summarise the build log in three bullet points",
         "prompt_tokens": 40, "completion_tokens": 5, "ts": 1.0,
         "status": "complete"},
        {"id": "2", "service": "svc-b", "model": "m",
         "prompt": "translate this error message to french",
         "prompt_tokens": 30, "completion_tokens": 5, "ts": 2.0,
         "status": "complete"},
    ]


def _mock_llm(monkeypatch):
    monkeypatch.setattr(ag, "scout", lambda inv, model, num_predict=256:
                        {"agent": "scout", "content": "svc-a, svc-b"})
    monkeypatch.setattr(ag, "profiler",
                        lambda s, p, model, np: {"agent": "profiler", "service": s,
                                                "parsed": {"project": "p"},
                                                "prompt_tokens": 1,
                                                "completion_tokens": 1})
    monkeypatch.setattr(ag, "critic",
                        lambda s, p, po, model, np: {"agent": "critic",
                                                    "service": s,
                                                    "content": "- gap: none"})
    monkeypatch.setattr(ag, "reporter",
                        lambda profs, heuristic=None, security=None,
                        model="", num_predict=512: {"agent": "reporter",
                                                    "content": "brief"})
    import iforensics.security_agent as sa
    monkeypatch.setattr(sa, "deterministic_report",
                        lambda **kw: {"risk_rating": "low", "totals": {},
                                      "n_findings": 0, "secrets": [],
                                      "injections": [], "permissions": [],
                                      "exposure": []})


def test_run_emits_ledger_trail(monkeypatch, tmp_path):
    _mock_llm(monkeypatch)
    monkeypatch.setattr(ag, "AGENT_DIR", str(tmp_path / "agentic"))
    monkeypatch.setenv("IF_LEDGER_DIR", str(tmp_path / "ledger"))
    res = ag.run_deep_investigation(_rows(), model="test-model", quick=True)
    run_id = res["run_id"]
    entries = led.read(run_id, base_dir=str(tmp_path / "ledger"))
    actions = [(e["actor"], e["action"]) for e in entries]
    assert ("orchestrator", "run.start") in actions
    assert ("scout", "task.complete") in actions
    assert ("profiler:svc-a", "task.complete") in actions
    assert ("reporter", "task.complete") in actions
    assert ("orchestrator", "run.complete") in actions
    # every completed task points at a real artifact with a recorded hash
    for e in entries:
        if e["action"] == "task.complete" and e["artifact"]:
            assert os.path.isfile(e["artifact"])
            assert len(e["artifact_sha256"]) == 64
    out = led.verify(run_id, base_dir=str(tmp_path / "ledger"))
    assert out["ok"] is True
    # heuristic section carries collectible intel for the runs sub-tabs
    heur = res["heuristic_investigation"]["svc-a"]
    assert heur["requests"] == 1 and "total_tokens" in heur
    assert isinstance(heur["models"], dict) and "evidence" in heur


def test_ledger_never_breaks_run(monkeypatch, tmp_path):
    _mock_llm(monkeypatch)
    monkeypatch.setattr(ag, "AGENT_DIR", str(tmp_path / "agentic"))
    monkeypatch.setenv("IF_LEDGER_DIR", os.path.join(str(tmp_path), "nope"))
    import iforensics.ledger as ledger_mod
    monkeypatch.setattr(ledger_mod, "append",
                        lambda *a, **k: (_ for _ in ()).throw(OSError("disk gone")))
    res = ag.run_deep_investigation(_rows(), model="test-model", quick=True)
    assert res["run_id"]  # run survived a dead ledger


def _mock_llm_no_profiler(monkeypatch):
    # scout/critic/reporter/security mocked; profiler+critic run on workers
    monkeypatch.setattr(ag, "scout", lambda inv, model, num_predict=256:
                        {"agent": "scout", "content": "svc-a, svc-b"})
    monkeypatch.setattr(ag, "reporter",
                        lambda profs, heuristic=None, security=None,
                        model="", num_predict=512: {"agent": "reporter",
                                                    "content": "brief"})
    import iforensics.security_agent as sa
    monkeypatch.setattr(sa, "deterministic_report",
                        lambda **kw: {"risk_rating": "low", "totals": {},
                                      "n_findings": 0, "secrets": [],
                                      "injections": [], "permissions": [],
                                      "exposure": []})


def test_swarm_mode_collects_worker_results(monkeypatch, tmp_path):
    _mock_llm_no_profiler(monkeypatch)
    monkeypatch.setattr(ag, "AGENT_DIR", str(tmp_path / "agentic"))
    monkeypatch.setenv("IF_LEDGER_DIR", str(tmp_path / "ledger"))
    monkeypatch.setenv("IF_SWARM_DIR", str(tmp_path / "swarm"))
    import iforensics.swarm as swarm_mod

    def fake_collect(task_ids, timeout_s=900.0, poll_s=2.0, base_dir=None):
        return {"done": {tid: {"parsed": {"project": "p",
                                          "evidence_quotes": []},
                               "content_head": "gap notes",
                               "prompt_tokens": 1, "completion_tokens": 1}
                         for tid in task_ids},
                "failed": {}, "missing": []}

    monkeypatch.setattr(swarm_mod, "collect_results", fake_collect)
    res = ag.run_deep_investigation(_rows(), model="m", quick=False,
                                    swarm=True)
    assert res["agents"]["profilers"]["svc-a"]["parsed"]["project"] == "p"
    assert "svc-a" in res["agents"]["critics"]
    assert res["agents"]["critics"]["svc-a"]["content"] == "gap notes"
    entries = led.read(res["run_id"], base_dir=str(tmp_path / "ledger"))
    kinds = {(e["actor"], e["action"]) for e in entries}
    assert ("orchestrator", "run.complete") in kinds
    assert ("profiler:svc-a", "task.complete") in kinds
    out = led.verify(res["run_id"], base_dir=str(tmp_path / "ledger"))
    assert out["ok"] is True


def test_swarm_mode_missing_tasks_become_errors(monkeypatch, tmp_path):
    _mock_llm_no_profiler(monkeypatch)
    monkeypatch.setattr(ag, "AGENT_DIR", str(tmp_path / "agentic"))
    monkeypatch.setenv("IF_LEDGER_DIR", str(tmp_path / "ledger"))
    monkeypatch.setenv("IF_SWARM_DIR", str(tmp_path / "swarm"))
    import iforensics.swarm as swarm_mod
    monkeypatch.setattr(swarm_mod, "collect_results",
                        lambda tids, **kw: {"done": {}, "failed": {},
                                            "missing": list(tids)})
    res = ag.run_deep_investigation(_rows(), model="m", quick=True,
                                    swarm=True, swarm_timeout=1.0)
    assert res["agents"]["profilers"]["svc-a"]["error"] == \
        "worker timeout: no result collected"
    assert any(e.startswith("profiler:svc-a") for e in res["errors"])
