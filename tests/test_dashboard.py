"""Unit tests for dashboard guards: path containment and route side-effects."""
import dashboard
from dashboard import _within


def test_within_strict_containment():
    base = "/tmp/opencode/recon/quai-radar"
    recon = "/tmp/opencode/recon"
    assert _within(base, recon)
    assert _within(base + "/INVESTIGATION.md", recon)
    # a file under a sibling whose name shares the prefix must be refused
    # relative to THIS service's base...
    assert not _within("/tmp/opencode/recon/quai-radarX/other", base)
    assert not _within("/tmp/opencode/recon/quai-radarX", base)
    # ...while it is a legit sibling when measured against the recon root
    assert _within("/tmp/opencode/recon/quai-radarX", recon)
    # parent escape, non-normalized dots, equality edge
    assert not _within("/tmp/opencode/../etc/passwd", recon)
    assert not _within("/etc/passwd", recon)
    assert not _within("/tmp/opencode/recon/quai-radar2/other.md", base)
    assert _within(base, base)


def test_side_effecting_route_is_post_only():
    paths = {}
    for r in dashboard.app.routes:
        if hasattr(r, "methods"):
            paths.setdefault(r.path, set()).update(r.methods)
    assert paths["/api/investigate"] == {"POST"}
    assert "POST" in paths["/api/runs"]
    assert "POST" in paths["/api/live/start"]
    assert "POST" in paths["/api/live/stop"]


def test_live_and_timeseries_paths_registered():
    paths = {r.path for r in dashboard.app.routes}
    for p in ("/api/live/feed", "/api/live/status", "/api/live/rates",
              "/api/live/stream", "/api/live/persisted",
              "/api/stats/timeseries",
              "/api/overview", "/api/services", "/api/evidence"):
        assert p in paths, p

def test_evidence_file_preview_download_and_containment(tmp_path, monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setattr(dashboard.config, "EVIDENCE_DIR", str(tmp_path))
    (tmp_path / "a.txt").write_text("hello evidence")
    (tmp_path / "b.bin").write_bytes(b"\x00\x01\x02")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.txt").write_text("nested")
    c = TestClient(dashboard.app)

    r = c.get("/api/evidence/file", params={"name": "a.txt"})
    assert r.status_code == 200 and r.json()["text"] == "hello evidence"
    assert c.get("/api/evidence/file", params={"name": "b.bin"}).json()["binary"] is True
    assert c.get("/api/evidence/file", params={"name": "sub/c.txt"}).json()["text"] == "nested"

    r = c.get("/api/evidence/file", params={"name": "a.txt", "download": 1})
    assert r.status_code == 200 and b"hello evidence" in r.content
    assert "attachment" in r.headers.get("content-disposition", "")

    for bad in ("../secret", "/etc/passwd", "missing.txt", "", "a/../../etc/passwd"):
        assert c.get("/api/evidence/file", params={"name": bad}).status_code == 404


def test_trust_and_risk_endpoints():
    from fastapi.testclient import TestClient
    c = TestClient(dashboard.app)
    t = c.get("/api/trust")
    assert t.status_code == 200
    body = t.json()
    assert {r["rule"] for r in body["rules"]} == {"T1", "T2", "T3", "T4", "T5", "T6"}
    assert body["summary"]["fail"] == 0
    r = c.get("/api/risk")
    assert r.status_code == 200
    assert "services" in r.json() and "summary" in r.json()


def test_run_validation_endpoint(monkeypatch):
    from fastapi.testclient import TestClient
    from iforensics import agents as ag
    monkeypatch.setattr(ag, "load_run", lambda rid: {
        "run_id": rid, "services": ["s"],
        "heuristic_investigation": {"s": {"project": "p", "evidence": {"templates": [],
                                                        "instructions": [], "sample_heads": []}}},
        "agents": {"profilers": {"s": {"error": "down"}},
                   "reporter": {"content": "brief"}}} if rid == "r1" else None)
    c = TestClient(dashboard.app)
    assert c.get("/api/runs/nope/validation").status_code == 404
    r = c.get("/api/runs/r1/validation")
    assert r.status_code == 200
    body = r.json()
    assert body["summary"]["unproven"] == 1
    assert "no security scan recorded for this run" in body["brief_issues"]


def test_fidelity_endpoint():
    from fastapi.testclient import TestClient
    c = TestClient(dashboard.app)
    r = c.get("/api/reconstructions/definitely-not-a-service/fidelity")
    assert r.status_code == 404


def test_p6_endpoints():
    from fastapi.testclient import TestClient
    c = TestClient(dashboard.app)
    f = c.get("/api/findings")
    assert f.status_code == 200
    body = f.json()
    assert body["summary"]["total"] == len(body["findings"])
    sevs = [x["severity"] for x in body["findings"]]
    from iforensics.findings import SEV_RANK
    assert sevs == sorted(sevs, key=lambda s: SEV_RANK[s])
    ch = c.get("/api/chain", params={"limit": 10})
    assert ch.status_code == 200
    assert len(ch.json()["events"]) <= 10
    ts = [e["t"] for e in ch.json()["events"]]
    assert ts == sorted(ts)
    k = c.get("/api/knowledge")
    assert k.status_code == 200
    assert k.json()["summary"]["nodes"] == len(k.json()["nodes"])


def test_post_rate_limit(monkeypatch):
    from fastapi.testclient import TestClient
    monkeypatch.setattr(dashboard, "_POST_HITS", {})
    monkeypatch.setitem(dashboard.POST_LIMITS, "/api/live/stop", (2, 60))
    c = TestClient(dashboard.app)
    assert c.post("/api/live/stop").status_code == 200
    assert c.post("/api/live/stop").status_code == 200
    r = c.post("/api/live/stop")
    assert r.status_code == 429
    assert r.json()["detail"].startswith("rate limited")
    assert c.get("/api/live/status").status_code == 200  # GETs unaffected


def test_swarm_endpoints(monkeypatch, tmp_path):
    from fastapi.testclient import TestClient
    from iforensics import ledger as ledger_mod
    monkeypatch.setenv("IF_LEDGER_DIR", str(tmp_path))
    ledger_mod.append("r1", "orchestrator", "run.start")
    c = TestClient(dashboard.app)
    runs = c.get("/api/swarm/runs")
    assert runs.status_code == 200
    assert [r["run_id"] for r in runs.json()["runs"]] == ["r1"]
    lg = c.get("/api/swarm/ledger", params={"run_id": "r1"})
    assert lg.status_code == 200
    assert lg.json()["entries"][0]["action"] == "run.start"
    assert c.get("/api/swarm/ledger", params={"run_id": "nope"}).status_code == 404
    ver = c.get("/api/swarm/verify", params={"run_id": "r1"})
    assert ver.json() == {"run_id": "r1", "ok": True, "checked": 1,
                          "failed_at": None, "reason": ""}
    q = c.get("/api/swarm/queue")
    assert q.status_code == 200
    assert set(q.json()) == {"pending", "claimed", "done", "failed"}
