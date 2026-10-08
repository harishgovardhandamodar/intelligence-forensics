"""Live wiring: tap auto-co-serve feeds the surfaces; reports stay unscored."""
from __future__ import annotations

from iforensics import live as live_mod
from iforensics.sim import reconstruction as eng
from iforensics.sim.recon import live as live_recon


def _events():
    return [
        {"seq": 201, "dir": "out", "service": "quai-radar",
         "model": "qwen3.8:latest", "prompt_head": "mempool stats summary"},
        {"seq": 202, "dir": "out", "service": "quai-radar",
         "model": "qwen3.8:latest", "prompt_head": "hourly congestion note"},
    ]


def test_tap_poll_coserves_when_enabled(monkeypatch):
    from iforensics import fox_client
    monkeypatch.setattr(fox_client, "llm_requests",
                        lambda limit=500: {"requests": [
                            {"id": 1, "service": "quai-radar",
                             "chosen_model": "qwen3.8:latest",
                             "prompt": "mempool stats summary",
                             "created_at": 9999999999.0},
                            {"id": 2, "service": "quai-radar",
                             "chosen_model": "qwen3.8:latest",
                             "prompt": "hourly congestion note",
                             "created_at": 9999999999.0}]})
    monkeypatch.setattr(fox_client, "llm_queue", lambda: {})
    monkeypatch.setattr(fox_client, "ollama_running", lambda timeout=8.0: {})
    live_mod.set_coserve(True)
    try:
        t = live_mod.LiveTap(interval_s=60.0, persist=False)
        got = t.poll_once()
        assert got["out"] == 2
        assert eng.STATE.records_for("u-live-quai-radar"), \
            "poll must co-serve new completions into the surfaces"
    finally:
        live_mod.set_coserve(False)
        eng.STATE.purge("u-live-quai-radar")


def test_tap_poll_skips_coserve_when_disabled(monkeypatch):
    from iforensics import fox_client
    monkeypatch.setattr(fox_client, "llm_requests",
                        lambda limit=500: {"requests": [
                            {"id": 9, "service": "quai-radar",
                             "chosen_model": "qwen3.8:latest",
                             "prompt": "something",
                             "created_at": 9999999999.0}]})
    monkeypatch.setattr(fox_client, "llm_queue", lambda: {})
    monkeypatch.setattr(fox_client, "ollama_running", lambda timeout=8.0: {})
    live_mod.set_coserve(False)
    t = live_mod.LiveTap(interval_s=60.0, persist=False)
    assert t.poll_once()["out"] == 1
    assert eng.STATE.records_for("u-live-quai-radar") == []


def test_live_report_unscored_but_structured():
    eng.coserve_events(_events())
    try:
        rep = live_recon.report(service="quai-radar")
        assert rep["scored"] is False
        assert rep["records"] > 0 and rep["with_text"] > 0
        assert sorted(rep["by_surface"]) == sorted(eng.STORE_IDS)
        # no accuracy KEYS anywhere (the caveat prose may say the word)
        def _keys(o):
            if isinstance(o, dict):
                for k, v in o.items():
                    yield k
                    yield from _keys(v)
            elif isinstance(o, list):
                for v in o:
                    yield from _keys(v)
        keys = set(_keys(rep))
        assert "accuracy" not in keys and "mean_accuracy" not in keys
    finally:
        eng.STATE.purge("u-live-quai-radar")


def test_truth_refused_for_live_users():
    try:
        eng.STATE.register_truth("u-live-quai-radar", {"ssn": "900-11-2222"})
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("truth accepted for a live user")
    assert live_recon.users() == [] or all(
        u["user_id"].startswith("u-live-") for u in live_recon.users())
