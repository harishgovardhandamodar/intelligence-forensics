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
              "/api/overview", "/api/services", "/api/evidence"):
        assert p in paths, p