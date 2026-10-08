"""P15 — reconstructions integration, Fox-first Ollama, harvest/attack collection.

Three things are asserted together because they are one story: the residual
surfaces are harvested into a vector collection the moment a request lands,
attacked only when someone asks for it, and listed alongside the reconstructed
services — while the dashboard's Ollama probe routes through Fox-services.
"""
from __future__ import annotations

import json

import pytest

import dashboard
from iforensics.sim import reconstruction as recon

client = None  # fastapi TestClient, bound lazily


@pytest.fixture(autouse=True)
def _client():
    global client
    from fastapi.testclient import TestClient
    client = TestClient(dashboard.app)
    recon.STATE.reset()
    # the POST counters are module-global and outlive a single test file;
    # clear on both sides so this file neither exhausts nor silently resets
    # another file's budget
    dashboard._POST_HITS.clear()
    yield
    recon.STATE.reset()
    dashboard._POST_HITS.clear()


# --------------------------------------------------------------------------- #
# harvest now — on ingest, with no ground truth attached
# --------------------------------------------------------------------------- #

def test_ingest_harvests_into_the_collection():
    client.post("/api/recon/begin", json={"user_id": "u-col-1",
                                          "truth": {"ssn": "900-11-2222"}})
    r = client.post("/api/recon/ingest",
                    json={"prompt": "account holder ssn 900-11-2222 please verify",
                          "metadata": {"user_id": "u-col-1", "field": "ssn"}})
    assert r.json()["harvested"] >= 1
    col = client.get("/api/recon/collection").json()
    assert col["strategy"] == "harvest-now-consume-later"
    assert col["strategy_label"].startswith("harvest now")
    assert col["by_user"]["u-col-1"] >= 1
    assert col["resident"] == col["harvested"]
    assert col["consumed"] == 0


def test_harvest_carries_provenance_and_no_truth():
    client.post("/api/recon/begin", json={"user_id": "u-col-2",
                                          "truth": {"pan": "4242-4242-4242-4242"}})
    client.post("/api/recon/ingest",
                json={"prompt": "card 4242-4242-4242-4242",
                      "metadata": {"user_id": "u-col-2", "field": "pan"},
                      "step": 2})
    col = client.get("/api/recon/collection").json()
    rows = recon.collection().rows("u-col-2")
    assert rows, "harvested rows must be readable back"
    meta = rows[0]["metadata"]
    # every row names who/what/where it came from; none names a secret
    assert meta["user_id"] == "u-col-2"
    assert meta["surface"] and meta["kind"] and meta["turn"] >= 0
    assert col["by_user"]["u-col-2"] == len(rows)


# --------------------------------------------------------------------------- #
# consume / attack later — the deferred half of the strategy
# --------------------------------------------------------------------------- #

def test_attack_can_run_after_the_truth_exists():
    # harvest first, with nothing to score against
    client.post("/api/recon/ingest",
                json={"prompt": "my ssn is 900-11-2222",
                      "metadata": {"user_id": "u-late", "field": "ssn"}})
    assert client.get("/api/recon/collection").json()["by_user"]["u-late"] >= 1
    refused = client.post("/api/recon/consume", json={"user_id": "u-late"})
    assert refused.status_code == 404  # no truth yet — the row still exists

    client.post("/api/recon/begin", json={"user_id": "u-late",
                                          "truth": {"ssn": "900-11-2222"}})
    d = client.post("/api/recon/consume", json={"user_id": "u-late"}).json()
    assert d["strategy"] == "harvest-now-consume-later"
    assert d["records"] >= 1 and d["accuracy"] is not None
    assert d["n_fields"] == 1
    assert client.get("/api/recon/collection").json()["consumed"] >= 1


def test_consume_without_scoring_still_returns_rows():
    client.post("/api/recon/ingest",
                json={"prompt": "nothing to score here 900-11-2222",
                      "metadata": {"user_id": "u-raw", "field": "ssn"}})
    d = client.post("/api/recon/consume",
                    json={"user_id": "u-raw", "attack": False}).json()
    assert d["attack"] is None and d["accuracy"] is None
    assert d["records"] >= 1 and d["texts"] >= 1


def test_reset_clears_the_collection():
    client.post("/api/recon/begin", json={"user_id": "u-gone",
                                          "truth": {"ssn": "900-11-2222"}})
    client.post("/api/recon/ingest",
                json={"prompt": "900-11-2222", "metadata": {"user_id": "u-gone"}})
    assert client.get("/api/recon/collection").json()["resident"] > 0
    out = client.post("/api/recon/reset").json()
    assert out["ok"] is True and out["collection_cleared"] > 0
    col = client.get("/api/recon/collection").json()
    assert col["resident"] == 0 and col["harvested"] == 0
    assert client.post("/api/recon/consume", json={}).status_code == 404


# --------------------------------------------------------------------------- #
# reconstructions: the service dir + the persisted runs, in one list
# --------------------------------------------------------------------------- #

def test_stateless_service_dir_is_listed_and_openable():
    out = client.get("/api/reconstructions").json()
    row = next((r for r in out if r["service"] == "stateless-inference"), None)
    assert row, "the modelled service must sit in the same list as the others"
    assert row["requests"] == 330

    files = client.get("/api/reconstructions/stateless-inference").json()["files"]
    assert "RECONSTRUCTED.json" in files and "inferred_pipeline.py" in files
    meta = json.loads(files["RECONSTRUCTED.json"])
    assert meta["caveats"] and meta["pipeline_stages"][0] == "capture_prompt"
    assert meta["pipeline_stages"][-1] == "reconstruction.consume"

    one = client.get("/api/reconstructions/stateless-inference/file",
                     params={"path": "README_RECONSTRUCTED.md"}).json()
    assert "harvest now" in one["content"]


def test_stateless_runs_appear_next_to_services():
    run = client.post("/api/recon/run",
                      json={"scenario": "stateless_chat", "n": 12, "seed": 3}).json()
    rid = run["run_id"]
    out = client.get("/api/reconstructions").json()
    row = next((r for r in out if r["service"] == rid), None)
    assert row and row["kind"] == "stateless-residual"
    assert row["requests"] == run["report"]["n_records"]
    assert "stateless-inference" in [r["service"] for r in out]

    files = client.get(f"/api/reconstructions/{rid}").json()["files"]
    assert "stateless_chat" in files
    payload = json.loads(client.get(f"/api/reconstructions/{rid}/file",
                                    params={"path": "stateless_chat"}).json()["content"])
    assert payload["run_id"] == rid and payload["report"]["surfaces"]
    # and the run harvested into the collection on the way through
    col = client.get("/api/recon/collection").json()
    assert col["last_user"] == run["user_id"]


def test_a_run_does_not_double_harvest_on_replay():
    first = client.post("/api/recon/run",
                        json={"scenario": "stateless_coding", "n": 8, "seed": 5}).json()
    after_first = client.get("/api/recon/collection").json()["resident"]
    second = client.post("/api/recon/run",
                         json={"scenario": "stateless_coding", "n": 8, "seed": 5}).json()
    assert first["user_id"] == second["user_id"]
    after_second = client.get("/api/recon/collection").json()["resident"]
    assert after_second == after_first, "purge must clear the previous harvest"
    assert after_second > 0


def test_consumed_attack_matches_the_live_report():
    run = client.post("/api/recon/run",
                      json={"scenario": "stateless_coding", "n": 16, "seed": 7}).json()
    rep = run["report"]
    d = client.post("/api/recon/consume",
                    json={"user_id": run["user_id"]}).json()
    assert d["accuracy"] == pytest.approx(rep["mean_accuracy"], abs=1e-9)
    assert d["recovered"] == rep["recovered"]
    assert d["n_fields"] == rep["n_fields"]


# --------------------------------------------------------------------------- #
# fox-first Ollama probe
# --------------------------------------------------------------------------- #

def test_ollama_running_prefers_fox_services(monkeypatch):
    from iforensics import fox_client
    calls = []

    def fake_get(path, params=None, timeout=15.0):
        calls.append(path)
        return {"models": [{"name": "qwen3.8:27b"}]}

    monkeypatch.setattr(fox_client, "_get", fake_get)
    d = fox_client.ollama_running()
    assert d["via"] == "fox" and d["models"][0]["name"] == "qwen3.8:27b"
    assert calls == ["/api/ollama/running"], "must not touch :11434 first"


def test_ollama_running_falls_back_to_direct_ollama(monkeypatch):
    from iforensics import fox_client, ollama_client

    def fox_down(*a, **k):
        raise ConnectionError("fox-services unreachable")

    monkeypatch.setattr(fox_client, "_get", fox_down)
    monkeypatch.setattr(ollama_client, "ps",
                        lambda timeout=8.0: {"models": [{"model": "qwen3.8:27b"}]})
    d = fox_client.ollama_running()
    assert d["via"] == "direct" and d["models"][0]["model"] == "qwen3.8:27b"


def test_ollama_endpoint_reports_which_route_answered(monkeypatch):
    from iforensics import fox_client
    monkeypatch.setattr(fox_client, "ollama_running",
                        lambda timeout=8.0: {"models": [], "via": "fox"})
    r = client.get("/api/ollama").json()
    assert r["ok"] is True and r["via"] == "fox" and r["loaded"] == 0

    def both_down(*a, **k):
        raise ConnectionError("no route to the model server")

    monkeypatch.setattr(fox_client, "ollama_running", both_down)
    r = client.get("/api/ollama").json()
    assert r["ok"] is False and r["via"] == "none" and r["error"]


# --------------------------------------------------------------------------- #
# the tab carries the collection card, and every route it touches exists
# --------------------------------------------------------------------------- #

def test_residuals_tab_carries_the_collection_card():
    sec = dashboard.PAGE.split('<section id=s-residuals>')[1].split("</section>")[0]
    for eid in ("res-col-sum", "res-col-meta", "res-col-out",
                "b-res-consume", "b-res-col"):
        assert f"id={eid}" in sec, eid
    assert "/api/recon/consume" in dashboard.POST_LIMITS
    js = open("static/app.js", encoding="utf-8").read()
    assert "loadReconCollection" in js and "/api/recon/collection" in js


# --------------------------------------------------------------------------- #
# live subtab mirrors the recon tab and harvests tap traffic
# --------------------------------------------------------------------------- #

def test_live_srecon_subtab_mirrors_the_recon_tab():
    sec = dashboard.PAGE.split('id=lp-srecon')[1].split("</div></section>")[0]
    for eid in ("b-lres-harvest", "lres-harvmsg", "lres-harvout",
                "lres-kpis", "lres-grid", "lres-cum", "lres-amp",
                "lres-col-sum", "lres-col-meta", "lres-col-out",
                "lres-insp", "lres-hist", "b-lres-run", "b-lres-consume",
                "b-lres-insp", "b-lres-load", "b-lres-reset"):
        assert f"id={eid}" in sec, eid
    js = open("static/app.js", encoding="utf-8").read()
    assert "mirrorReconToLive" in js and "harvestLiveTraffic" in js
    assert "loadReconTab().then(" in js


def test_harvest_live_needs_the_tap_running():
    r = client.post("/api/recon/harvest-live",
                    json={"limit": 50, "dry_run": True})
    assert r.status_code == 409
    assert "/api/recon/harvest-live" in dashboard.POST_LIMITS


# --------------------------------------------------------------------------- #
# co-serving: live Fox traffic through the residual surfaces
# --------------------------------------------------------------------------- #

def _fake_tap(*events):
    class _FakeTap:
        def snapshot(self, limit=500, since_seq=0):
            return list(events)[:max(1, limit)]
    return _FakeTap()


def _live_events():
    return [
        {"seq": 101, "dir": "out", "service": "quai-radar",
         "model": "qwen3.8:latest", "query_type": "chart/price",
         "status": "complete",
         "prompt_head": "Extract structured facts about quai network stats"},
        {"seq": 102, "dir": "out", "service": "quai-radar",
         "model": "qwen3.8:latest", "query_type": "chart/price",
         "status": "complete",
         "prompt_head": "Summarise mempool congestion for the last hour"},
        {"seq": 103, "dir": "in", "service": "quai-radar",
         "prompt_head": "in-flight query (not a completion)"},
    ]


def test_coserve_needs_the_tap_running():
    r = client.post("/api/recon/coserve",
                    json={"limit": 50, "dry_run": True})
    assert r.status_code == 409
    assert "/api/recon/coserve" in dashboard.POST_LIMITS


def test_coserve_ingests_live_traffic_into_the_surfaces(monkeypatch):
    from iforensics import live as live_mod
    monkeypatch.setattr(live_mod, "tap",
                        lambda: _fake_tap(*_live_events()))
    d = client.post("/api/recon/coserve",
                    json={"limit": 50}).json()
    assert d["ingested"] == 2 and d["events"] == 3
    assert d["services"] == {"quai-radar": 2}
    assert d["users"] == ["u-live-quai-radar"]
    assert d["retained"].get("logging", 0) >= 2
    # the same engine the simulations use now holds the live rows
    insp = client.get("/api/recon/residuals",
                      params={"user_id": "u-live-quai-radar",
                              "surface": "", "limit": 100}).json()
    assert insp["total"] >= 2 and insp["with_text"] >= 2
    # and the collection harvested them on the way through
    col = client.get("/api/recon/collection").json()
    assert col["by_user"].get("u-live-quai-radar", 0) >= 1
    # live users are listed with retention counts, no truth required
    users = client.get("/api/recon/live-users").json()["users"]
    assert users and users[0]["user_id"] == "u-live-quai-radar"
    assert users[0]["records"] == insp["total"]


def test_coserve_dedups_repeated_polls(monkeypatch):
    from iforensics import live as live_mod
    monkeypatch.setattr(live_mod, "tap",
                        lambda: _fake_tap(*_live_events()))
    first = client.post("/api/recon/coserve",
                        json={"limit": 50}).json()
    second = client.post("/api/recon/coserve",
                         json={"limit": 50}).json()
    assert first["ingested"] == 2
    assert second["ingested"] == 0 and second["skipped"] >= 2
    insp = client.get("/api/recon/residuals",
                      params={"user_id": "u-live-quai-radar",
                              "limit": 1000}).json()
    # KV snapshots linger: only the newest turn keeps one, so the store
    # holds one fewer row than the gross retained count
    assert insp["total"] == sum(first["retained"].values()) - 1 > 0
    assert sum(1 for r in insp["records"]
               if r["kind"] == "kv_linger") == 1


def test_coserve_dry_run_scores_nothing_and_writes_nothing(monkeypatch):
    from iforensics import live as live_mod
    monkeypatch.setattr(live_mod, "tap",
                        lambda: _fake_tap(*_live_events()))
    d = client.post("/api/recon/coserve",
                    json={"limit": 50, "dry_run": True}).json()
    assert d["dry_run"] is True and d["ingested"] == 0 and d["out"] == 2
    assert client.get("/api/recon/live-users").json() == {"users": []}


def test_live_subtab_carries_coserve_controls():
    sec = dashboard.PAGE.split('id=lp-srecon')[1].split("</div></section>")[0]
    for eid in ("b-lres-coserve", "lsel-live-user", "lres-harvmsg",
                "lres-harvout", "b-lres-harvest"):
        assert f"id={eid}" in sec, eid
    js = open("static/app.js", encoding="utf-8").read()
    assert "coserveLive" in js and "loadLiveUsers" in js
    assert "/api/recon/coserve" in js and "/api/recon/live-users" in js


# --------------------------------------------------------------------------- #
# tap-driven co-serve + unscored live reconstruction
# --------------------------------------------------------------------------- #

def test_truth_registration_refused_for_live_users():
    r = client.post("/api/recon/begin",
                    json={"user_id": "u-live-quai-radar",
                          "truth": {"ssn": "900-11-2222"}})
    assert r.status_code == 400


def test_live_report_needs_coserved_rows():
    r = client.get("/api/recon/live-report",
                   params={"service": "no-such-service"})
    assert r.status_code == 404


def test_live_report_is_retention_only(monkeypatch):
    from iforensics import live as live_mod
    monkeypatch.setattr(live_mod, "tap",
                        lambda: _fake_tap(*_live_events()))
    client.post("/api/recon/coserve", json={"limit": 50})
    d = client.get("/api/recon/live-report",
                   params={"service": "quai-radar"}).json()
    assert d["scored"] is False and d["records"] > 0
    assert sorted(d["by_surface"]) == sorted(recon.STORE_IDS)

    def _keys(o):
        if isinstance(o, dict):
            for k, v in o.items():
                yield k
                yield from _keys(v)
        elif isinstance(o, list):
            for v in o:
                yield from _keys(v)
    assert "accuracy" not in set(_keys(d))
    # non-live users are refused: scoring them would be fabrication
    r = client.get("/api/recon/live-report",
                   params={"user_id": "u-recon-coding"})
    assert r.status_code == 400


def test_coserve_auto_toggle_reported_in_live_status():
    from iforensics import live as live_mod
    try:
        r = client.post("/api/recon/coserve-auto",
                        json={"on": True}).json()
        assert r["coserve"]["on"] is True
        r = client.post("/api/recon/coserve-auto",
                        json={"on": False}).json()
        assert r["coserve"]["on"] is False
    finally:
        live_mod.set_coserve(False)
    assert "/api/recon/coserve-auto" in dashboard.POST_LIMITS


def test_consume_attack_refused_for_live_users_but_readback_works(monkeypatch):
    from iforensics import live as live_mod
    monkeypatch.setattr(live_mod, "tap",
                        lambda: _fake_tap(*_live_events()))
    client.post("/api/recon/coserve", json={"limit": 50})
    uid = "u-live-quai-radar"
    r = client.post("/api/recon/consume",
                    json={"user_id": uid, "attack": True})
    assert r.status_code == 404
    assert "retention-only" in r.json()["detail"]
    d = client.post("/api/recon/consume",
                    json={"user_id": uid, "attack": False}).json()
    assert d["records"] > 0 and d["accuracy"] is None
