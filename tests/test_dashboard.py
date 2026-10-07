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
