"""SAST + DAST workflows with local-LLM evaluation (deterministic core)."""
from __future__ import annotations

import dashboard
from iforensics import dast, ollama_client, sast

client = None


def setup_function(_):
    global client
    from fastapi.testclient import TestClient
    client = TestClient(dashboard.app)
    dashboard._POST_HITS.clear()


def _tree(tmp_path):
    (tmp_path / "a.py").write_text(
        "import os\nos.system('ls ' + name)\n"
        "db.execute(f\"SELECT * FROM t WHERE x='{v}'\")\n")
    (tmp_path / "b.js").write_text(
        "el.innerHTML = '<b>' + name + '</b>';\n")
    (tmp_path / "node_modules").mkdir()
    (tmp_path / "node_modules" / "evil.js").write_text("eval('1');\n")
    return str(tmp_path)


def test_sast_scan_finds_sinks_and_skips_vendored(tmp_path):
    found = sast.scan(_tree(tmp_path))
    by_check = {f["check"] for f in found}
    assert {"exec-sink", "sql-concat", "xss-sink"} <= by_check
    assert all("node_modules" not in f["file"] for f in found)
    assert [f["id"] for f in found] == sorted(f["id"] for f in found)
    # deterministic across runs
    again = sast.scan(str(tmp_path))
    assert [(f["check"], f["file"], f["line"], f["match"]) for f in found] == \
           [(f["check"], f["file"], f["line"], f["match"]) for f in again]


def test_sast_scan_ids_ordered_and_shaped(tmp_path):
    found = sast.scan(_tree(tmp_path))
    assert found[0]["id"] == "SAST-001"
    for f in found:
        assert set(f) >= {"id", "check", "severity", "file", "line",
                          "match", "detail"}


def _fake_judge(monkeypatch, verdicts):
    def fake(system, user, untrusted=None, untrusted_label="", **kw):
        assert "UNTRUSTED" in (untrusted or system).upper() or untrusted
        return {"content": "{}", "parsed": {"verdicts": verdicts},
                "model": "m", "ms": 1, "prompt_tokens": 2,
                "completion_tokens": 3}
    monkeypatch.setattr(ollama_client, "ask_json", fake)


def test_sast_judge_maps_verdicts_and_marks_rest_unjudged(monkeypatch,
                                                          tmp_path):
    _fake_judge(monkeypatch, [{"id": "SAST-001", "verdict": "dismissed",
                               "severity": "info", "rationale": "test",
                               "fix": "none"}])
    out = sast.judge(sast.scan(_tree(tmp_path)), max_findings=50)
    assert out["judged"] == 1 and out["total"] >= 1
    first = next(f for f in out["verdicts"] if f["id"] == "SAST-001")
    assert first["verdict"] == "dismissed" and first["adj_severity"] == "info"
    rest = [f for f in out["verdicts"] if f["id"] != "SAST-001"]
    assert rest and all(f["verdict"] == "unjudged" for f in rest)
    assert out["llm"]["status"] == "ok"


def test_sast_judge_survives_llm_outage(monkeypatch, tmp_path):
    def boom(*a, **k):
        raise ollama_client.OllamaError("down")
    monkeypatch.setattr(ollama_client, "ask_json", boom)
    out = sast.judge(sast.scan(_tree(tmp_path)))
    assert out["verdicts"] == [] and out["llm"]["status"] == "unavailable"


def test_sast_evaluate_scope_guard():
    try:
        sast.evaluate(scope="workspace")
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("workspace SAST triage allowed")


def test_dast_rejects_non_loopback_targets():
    for bad in ("http://example.com/", "http://100.101.3.115:8211/",
                "https://127.0.0.1:8211/"):
        try:
            dast._check_target(bad)
        except ValueError:
            pass
        else:  # pragma: no cover
            raise AssertionError(f"accepted {bad}")
    assert dast._check_target("http://127.0.0.1:8211/").endswith(":8211")


def test_dast_probes_shape_and_ids(monkeypatch):
    def fake_exchange(base, method, path, body=None):
        if path == "/":
            return 200, {"server": "uvicorn",
                         "x-content-type-options": "nosniff"}, "<html>"
        if "etc/passwd" in path:
            return 404, {}, "not found"
        if path == "/api/security/scan":
            return 405, {}, "method not allowed"
        if path.startswith("/api/reconstructions/"):
            return 404, {}, '{"detail":"unknown"}'
        if path == "/api/evidence":
            return 200, {}, '["a.jsonl"]'
        if path == "/api/recon/begin":
            return 400, {}, '{"detail":"user_id required"}'
        return 200, {}, "{}"
    monkeypatch.setattr(dast, "_exchange", fake_exchange)
    out = dast.evaluate(use_llm=False)
    assert out["workflow"] == "dast" and out["probes"] == 8
    assert out["failed"] == 1  # only the accepted-risk no-auth listing
    failed = [f for f in out["items"] if f["result"] == "fail"]
    assert failed[0]["probe"] == "no-auth-listing"
    assert [f["id"] for f in out["items"]] == sorted(
        f["id"] for f in out["items"])


def test_dast_traversal_fail_detected(monkeypatch):
    def fake_exchange(base, method, path, body=None):
        if "etc" in path and "passwd" in path:
            return 200, {}, "root:x:0:0:leaked"
        return 404, {}, "{}"
    monkeypatch.setattr(dast, "_exchange", fake_exchange)
    out = dast.evaluate(use_llm=False)
    trav = next(f for f in out["items"] if f["probe"] == "traversal")
    assert trav["result"] == "fail" and trav["severity"] == "high"


def test_dast_judge_batches_failures_only(monkeypatch):
    seen = {}

    def fake_exchange(base, method, path, body=None):
        return 200, {}, "root:x:0:0:leaked" if "passwd" in path else "{}"
    monkeypatch.setattr(dast, "_exchange", fake_exchange)

    def fake_judge(findings, max_findings=20, model=None, timeout=240.0,
                   system=None, subject=""):
        seen["n"] = len(findings)
        seen["system"] = system
        return {"verdicts": [], "judged": 0, "total": len(findings),
                "llm": {"status": "ok"}}
    monkeypatch.setattr(sast, "judge", fake_judge)
    out = dast.evaluate()
    assert seen["system"] is dast.DAST_SYSTEM
    assert seen["n"] == out["failed"] >= 1


def test_evaluate_endpoint_validation():
    r = client.post("/api/security/evaluate", json={"workflow": "nope"})
    assert r.status_code == 400
    r = client.post("/api/security/evaluate",
                    json={"workflow": "dast",
                          "base_url": "http://example.com/"})
    assert r.status_code == 400
    r = client.post("/api/security/evaluate",
                    json={"workflow": "sast", "use_llm": False})
    assert r.status_code == 200
    body = r.json()
    assert body["workflow"] == "sast" and body["sast"]["findings"] >= 0
    assert "/api/security/evaluate" in dashboard.POST_LIMITS


def test_evaluate_endpoint_dast_offline(monkeypatch):
    def fake_exchange(base, method, path, body=None):
        return 404, {}, "{}"
    monkeypatch.setattr(dast, "_exchange", fake_exchange)
    r = client.post("/api/security/evaluate",
                    json={"workflow": "dast", "use_llm": False})
    assert r.status_code == 200
    assert r.json()["dast"]["probes"] == 8


def test_security_tab_carries_appsec_controls():
    for eid in ("b-sast", "b-dast", "sec-eval-msg", "sec-eval"):
        assert f"id={eid}" in dashboard.PAGE, eid
    js = open("static/app.js", encoding="utf-8").read()
    assert "runAppSec" in js and "/api/security/evaluate" in js


def test_posture_endpoint_is_deterministic_and_llm_free(monkeypatch):
    def fake_exchange(base, method, path, body=None):
        return 404, {}, "{}"
    monkeypatch.setattr(dast, "_exchange", fake_exchange)
    r = client.get("/api/security/posture")
    assert r.status_code == 200
    body = r.json()
    assert body["workflow"] == "dast" and body["probes"] == 8
    assert "triage" not in body
    assert "sec-posture" in dashboard.PAGE


def test_security_analytics_helpers_render():
    js = open("static/app.js", encoding="utf-8").read()
    for fn in ("riskDial", "sevDonut", "verdictBars", "loadPosture"):
        assert fn in js, fn
