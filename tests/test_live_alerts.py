"""Unit tests for tap anomaly alerts (P5.18)."""
import time

from iforensics import live as live_mod
from iforensics.live import LiveTap


def _tap(warm=True, known=("svc", "s")):
    t = LiveTap(interval_s=5, req_limit=5, persist=False)
    t.started_at = time.time() - (3600 if warm else 0)
    t.last_poll_at = time.time()
    t._known_services.update(known)
    return t


def _ev(svc="svc", status="complete", ts=None):
    return {"t": ts if ts is not None else time.time(), "dir": "out",
            "service": svc, "model": "m", "prompt_head": "x",
            "status": status, "prompt_tokens": 1, "completion_tokens": 1,
            "duration_ms": 1, "qid": ""}


def test_error_spike_fires_at_threshold():
    t = _tap()
    for _ in range(3):
        t._push(_ev(status="error"))
    t._push(_ev(status="complete"))
    new = t.evaluate_alerts()
    assert [a["kind"] for a in new] == ["error_spike"]
    assert new[0]["severity"] == "high" and new[0]["service"] == "svc"


def test_error_spike_quiet_below_threshold_or_rate():
    t = _tap()
    for _ in range(2):
        t._push(_ev(status="error"))
    for _ in range(8):
        t._push(_ev(status="complete"))
    assert t.evaluate_alerts() == []
    t2 = _tap()  # 3 errors but only 5% of 60 -> rate gate holds
    for _ in range(3):
        t2._push(_ev(status="error"))
    for _ in range(57):
        t2._push(_ev(status="complete"))
    assert t2.evaluate_alerts() == []


def test_alert_cooldown_dedupes():
    t = _tap()
    for _ in range(4):
        t._push(_ev(status="error"))
    assert len(t.evaluate_alerts()) == 1
    assert t.evaluate_alerts() == []  # same condition, still cooling down


def test_new_service_after_warmup_only():
    t = _tap(warm=True)
    t._push(_ev(svc="brand-new"))
    new = t.evaluate_alerts()
    assert [a["kind"] for a in new] == ["new_service"]
    assert new[0]["service"] == "brand-new"
    cold = _tap(warm=False)  # restart learns silently, no page-storm
    cold._push(_ev(svc="brand-new"))
    assert cold.evaluate_alerts() == []
    assert "brand-new" in cold._known_services


def test_volume_spike_against_median():
    t = _tap()
    t._poll_out_counts.extend([2] * 6)
    new = t.evaluate_alerts(current_out=12)
    assert [a["kind"] for a in new] == ["volume_spike"]
    t2 = _tap()
    t2._poll_out_counts.extend([2] * 6)
    assert t2.evaluate_alerts(current_out=3) == []
    t3 = _tap()  # too little history -> no baseline, no alert
    assert t3.evaluate_alerts(current_out=50) == []


def test_stale_edge_fires_once_and_resets():
    t = _tap()
    t.last_poll_at = time.time() - 3600
    assert [a["kind"] for a in t.evaluate_alerts()] == ["stale"]
    assert t.evaluate_alerts() == []
    t.last_poll_at = time.time()  # polls resume -> re-arms
    t.evaluate_alerts()
    assert t._stale_alerted is False


def test_status_carries_alerts():
    t = _tap()
    for _ in range(4):
        t._push(_ev(status="error"))
    t.evaluate_alerts()
    st = t.status()
    assert st["n_alerts"] == 1
    assert st["alerts"][0]["kind"] == "error_spike"


def test_poll_once_raises_overflow_and_eviction(monkeypatch):
    t = LiveTap(interval_s=5, req_limit=2, persist=False)
    t.started_at = time.time() - 3600
    now = time.time()
    pages = [
        [{"id": 5, "service": "s", "prompt": "a", "created_at": now},
         {"id": 4, "service": "s", "prompt": "b", "created_at": now}],
        [{"id": 3, "service": "s", "prompt": "c", "created_at": now},
         {"id": 2, "service": "s", "prompt": "d", "created_at": now}],
    ]
    monkeypatch.setattr(live_mod.fox_client, "llm_requests",
                        lambda **kw: {"requests": pages.pop(0)} if pages else {"requests": []})
    monkeypatch.setattr(live_mod.fox_client, "llm_queue", lambda: {})
    models = [{"name": "m1"}]
    monkeypatch.setattr(live_mod.fox_client, "_get",
                        lambda *a, **k: {"models": list(models)})
    t.poll_once()  # anchors continuity, learns m1
    models.clear()
    t.poll_once()  # disjoint page -> overflow; m1 gone -> eviction
    kinds = {a["kind"] for a in t.alerts}
    assert "page_overflow" in kinds
    assert "model_evicted" in kinds
