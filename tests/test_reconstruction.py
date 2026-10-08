"""Stateless-inference reconstruction (P14) — engine, API and client tests.

Hermetic: synthetic values only, seeded, no network beyond the local
`http.client` round trip through the client app's own HTTP handler.
"""
from __future__ import annotations

import re
import threading
from http.client import HTTPConnection
from http.server import ThreadingHTTPServer

import pytest

import dashboard
from iforensics.sim import reconstruction as recon
from recon_client import app as rclient

client = None  # fastapi TestClient, bound lazily


@pytest.fixture(autouse=True)
def _client():
    global client
    from fastapi.testclient import TestClient
    client = TestClient(dashboard.app)
    recon.STATE.reset()
    yield
    recon.STATE.reset()


# --------------------------------------------------------------------------- #
# catalogue
# --------------------------------------------------------------------------- #

def test_catalogue_lists_eight_surfaces():
    d = client.get("/api/recon/surfaces").json()
    ids = [s["id"] for s in d["surfaces"]]
    assert ids == recon.ALL_IDS
    assert len(ids) == 8
    roles = [s["role"] for s in d["surfaces"]]
    assert roles.count("store") == 6 and roles.count("linker") == 1
    assert roles.count("analysis") == 1
    assert [s["role"] for s in d["surfaces"] if s["id"] == "amplification"] == ["analysis"]
    assert len(d["scenarios"]) == 3
    assert set(d["store_ids"]) == set(recon.STORE_IDS)
    assert d["rates"]["ops_paste"] < d["rates"]["logging_flagged"] < 1.0
    for s in d["surfaces"]:
        assert s["diagram"].startswith("flowchart"), s["id"]
        assert "-->" in s["diagram"] and s["diagram"].count("\n") >= 2


def test_scenarios_are_three_and_use_reserved_values():
    for sc in recon.SCENARIOS.values():
        assert len(sc["fields"]) == 2 and len(sc["carriers"]) >= 3
    for sid in recon.SCENARIOS:
        sess = recon.build_session(sid, seed=42, n=24)
        truth = sess["truth"]
        assert set(truth) == set(recon.SCENARIOS[sid]["fields"])
        for f, v in truth.items():
            if f == "ssn":
                assert v.startswith("9"), "must be never-issued 900-series"
            elif f in ("credit_card", "card"):
                assert v.startswith("4242")
            elif f == "email":
                assert v.endswith("example.com")
            elif f == "phone":
                assert v.startswith("555")


# --------------------------------------------------------------------------- #
# engine
# --------------------------------------------------------------------------- #

def test_report_gradient_and_amplification():
    res = recon.run_session("stateless_coding", seed=42, n=48)
    rep = res["report"]
    by_id = {s["id"]: s for s in rep["surfaces"]}

    assert rep["n_fields"] == 2
    # vectors carry no text, so vector-only accuracy is zero and never faked
    assert by_id["embeddings"]["accuracy"] == 0.0
    assert by_id["embeddings"]["text_records"] == 0
    assert by_id["embeddings"]["linkage"]["linked_ratio"] > 0.5
    assert by_id["embeddings"]["linkage"]["n_families"] >= 1
    # the gradient: some surface is strong, none is trivially weak-but-equal
    assert by_id["human_ops"]["accuracy"] >= 0.9
    assert 0.2 < by_id["billing"]["accuracy"] < 1.0

    # cumulative curve is monotone — the text pool only ever grows
    accs = [c["accuracy"] for c in rep["cumulative"]]
    assert accs == sorted(accs)
    assert accs[-1] >= accs[0]

    amp = rep["amplification"]
    assert amp["delta"] > 0.3
    assert amp["pooled_accuracy"] >= amp["single_query_accuracy"]
    assert amp["turns_pooled"] == rep["n_turns"]


def test_run_is_deterministic_for_a_seed():
    a = recon.run_session("stateless_chat", seed=7, n=32)["report"]
    b = recon.run_session("stateless_chat", seed=7, n=32)["report"]
    assert a["mean_accuracy"] == b["mean_accuracy"]
    assert [s["accuracy"] for s in a["surfaces"]] == \
           [s["accuracy"] for s in b["surfaces"]]


def test_unknown_scenario_is_rejected():
    with pytest.raises(ValueError):
        recon.run_session("nope")


def test_secret_sits_after_the_head_windows():
    """A turn that only reaches logging's 180-char head must lose the secret."""
    sess = recon.build_session("stateless_coding", seed=42, n=24)
    long_turns = [t for t in sess["turns"] if len(t["prompt"]) > recon.HEAD_CHARS]
    assert long_turns, "carriers must be longer than the logged head"
    truth = sess["truth"]
    for t in long_turns[:6]:
        head = t["prompt"][:recon.HEAD_CHARS]
        assert all(v not in head for v in truth.values())


# --------------------------------------------------------------------------- #
# API flow
# --------------------------------------------------------------------------- #

def test_full_flow_begin_ingest_reconstruct_report():
    truth = {"api_key": "sk-test-000000000000", "db_password": "s3cret" * 3}
    r = client.post("/api/recon/begin",
                    json={"user_id": "u-test", "truth": truth})
    assert r.status_code == 200 and r.json()["fields"] == sorted(truth)

    # a turn whose whole text survives somewhere: the bare value is present
    client.post("/api/recon/ingest", json={
        "prompt": "here it is " + truth["api_key"],
        "metadata": {"user_id": "u-test"}, "step": 5})

    rec = client.post("/api/recon/reconstruct", json={
        "user_id": "u-test", "surfaces": ["logging", "cache"],
        "amplify": False}).json()
    assert rec["mode"] == "single-request"
    assert rec["fields"]["api_key"]["recovered"] is True
    assert rec["fields"]["api_key"]["accuracy"] == 1.0
    assert rec["fields"]["db_password"]["recovered"] is False
    # two fields, one present: the mean cannot reach 1.0
    assert 0.0 < rec["headline_accuracy"] < 1.0

    rep = client.get("/api/recon/report", params={"user_id": "u-test"}).json()
    assert rep["user_id"] == "u-test"
    assert rep["n_records"] >= 1


def test_reconstruct_unknown_user_is_404():
    r = client.post("/api/recon/reconstruct", json={"user_id": "ghost"})
    assert r.status_code == 404


def test_run_endpoints_and_persistence():
    r = client.post("/api/recon/run",
                    json={"scenario": "stateless_support", "n": 32, "seed": 3})
    assert r.status_code == 200
    body = r.json()
    run_id = body["run_id"]
    assert body["report"]["n_fields"] == 2

    runs = client.get("/api/recon/runs").json()["runs"]
    assert run_id in runs

    loaded = client.get("/api/recon/run", params={"run_id": run_id}).json()
    # keyed by scenario; newest file first
    first = loaded[next(iter(loaded))]
    assert first["report"]["n_fields"] == 2
    assert first["user_id"] == body["user_id"]

    missing = client.get("/api/recon/run", params={"run_id": "nope"})
    assert missing.status_code == 404

    bad = client.post("/api/recon/run", json={"scenario": "nope"})
    assert bad.status_code == 400


def test_residuals_endpoint_filters_and_bounds():
    client.post("/api/recon/run", json={"scenario": "stateless_coding",
                                        "n": 24, "seed": 11})
    uid = "u-recon-coding"
    all_ = client.get("/api/recon/residuals", params={"user_id": uid}).json()
    assert all_["total"] > 0 and all_["with_text"] >= 0

    log = client.get("/api/recon/residuals",
                     params={"user_id": uid, "surface": "logging"}).json()
    assert log["surface"] == "logging"
    assert {r["surface"] for r in log["records"]} == {"logging"}
    assert log["total"] <= all_["total"]
    # vector payloads never leave the store in a residual dump
    assert all("vector" not in r["meta"] for r in log["records"])

    emb = client.get("/api/recon/residuals",
                     params={"user_id": uid, "surface": "embeddings"}).json()
    assert all(not r["text"] for r in emb["records"])

    bad = client.get("/api/recon/residuals",
                     params={"user_id": uid, "surface": "wat"})
    assert bad.status_code == 400


def test_reset_clears_truth_and_records():
    client.post("/api/recon/begin", json={"user_id": "u-x", "truth": {"ssn": "900-11-2222"}})
    client.post("/api/recon/ingest", json={"prompt": "900-11-2222",
                                           "metadata": {"user_id": "u-x"}})
    assert client.get("/api/recon/residuals",
                      params={"user_id": "u-x"}).json()["total"] > 0
    out = client.post("/api/recon/reset").json()
    assert out["ok"] is True
    assert client.get("/api/recon/residuals",
                      params={"user_id": "u-x"}).json()["total"] == 0
    assert client.post("/api/recon/reconstruct",
                       json={"user_id": "u-x"}).status_code == 404


def test_ingest_requires_a_prompt():
    assert client.post("/api/recon/ingest", json={"prompt": ""}).status_code == 400


def test_rate_limits_cover_the_recon_routes():
    for route in ("/api/recon/run", "/api/recon/ingest", "/api/recon/reset"):
        assert route in dashboard.POST_LIMITS


# --------------------------------------------------------------------------- #
# client app
# --------------------------------------------------------------------------- #

def test_client_settings_and_unwrap():
    settings = rclient.load_settings()
    assert settings["server"].startswith("http") and settings["port"] == 8311
    assert settings["scenario"] in recon.SCENARIOS
    assert isinstance(settings["n_turns"], int)

    payload = {"stateless_coding": {"run_id": "r1", "scenario": "stateless_coding",
                                    "user_id": "u", "report": {"n_fields": 2}}}
    assert rclient._unwrap(payload)["run_id"] == "r1"
    assert rclient._unwrap({"report": {"x": 1}})["report"]["x"] == 1
    assert rclient._unwrap({"a": 1}) == {"a": 1}


def test_client_print_report_is_plain_text(capsys):
    res = recon.run_session("stateless_coding", seed=42, n=32)
    rclient.print_report(res["report"])
    out = capsys.readouterr().out
    assert "cumulative" in out and "amplification" in out
    assert "api_key" in out and "\n  fields:" in out


def test_client_api_talks_to_the_server(monkeypatch):
    """Drive the client's own HTTP handler in-process against a fake API."""
    class FakeAPI:
        server = "http://fake.test"

        def health(self):
            return {"status": "ok", "service": "fake"}

        def surfaces(self):
            return client.get("/api/recon/surfaces").json()

        def runs(self):
            return client.get("/api/recon/runs").json()

        def load_run(self, rid):
            return client.get("/api/recon/run", params={"run_id": rid}).json()

        def residuals(self, uid, surface="", limit=100):
            return client.get("/api/recon/residuals",
                              params={"user_id": uid, "surface": surface,
                                      "limit": limit}).json()

        def run(self, scenario, n=48, seed=42):
            return client.post("/api/recon/run", json={
                "scenario": scenario, "n": n, "seed": seed}).json()

        def report(self, uid):
            return client.get("/api/recon/report",
                              params={"user_id": uid}).json()

        def reconstruct(self, uid, surfaces=None, amplify=True):
            return client.post("/api/recon/reconstruct", json={
                "user_id": uid, "surfaces": surfaces or [],
                "amplify": amplify}).json()

        def reset(self):
            return client.post("/api/recon/reset").json()

    fake = FakeAPI()
    monkeypatch.setattr(rclient, "api_for", lambda server=None: fake)

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), rclient.Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    port = httpd.server_address[1]

    def get(path, method="GET", body=None):
        conn = HTTPConnection("127.0.0.1", port, timeout=20)
        conn.request(method, path, body=body,
                     headers={"Content-Type": "application/json"})
        r = conn.getresponse()
        raw = r.read().decode()
        conn.close()
        return r.status, raw

    try:
        status, raw = get("/")
        assert status == 200 and "reconstruction" in raw

        status, raw = get("/config")
        assert status == 200 and "server" in raw

        status, raw = get("/health")
        assert status == 200 and "fake" in raw

        status, raw = get("/api/state")
        assert status == 200 and len(__import__("json").loads(raw)["surfaces"]) == 8

        status, raw = get("/api/recon/run", method="POST",
                          body='{"scenario":"stateless_chat","n":24,"seed":5}')
        assert status == 200 and "report" in raw

        status, raw = get("/api/recon/residuals?user_id=u-recon-chat&surface=all")
        assert status == 200

        status, _ = get("/api/nope")
        assert status == 404
    finally:
        httpd.shutdown()
        httpd.server_close()


def test_client_surfaces_command(capsys):
    class Fake:
        server = "http://fake"
        def surfaces(self):
            return client.get("/api/recon/surfaces").json()
    rclient.cmd_surfaces(Fake())
    out = capsys.readouterr().out
    assert "human_ops" in out and "amplification" in out
    assert "stateless_coding" in out
    # no real secrets anywhere in the catalogue
    assert not re.search(r"\b\d{3}-\d{2}-\d{4}\b", out)


# --------------------------------------------------------------------------- #
# dashboard: the panel lives on its own tab
# --------------------------------------------------------------------------- #
def test_residuals_tab_is_registered_in_the_sidebar():
    assert '<button data-t=residuals>Stateless recon</button>' in dashboard.PAGE
    assert '<section id=s-residuals>' in dashboard.PAGE
    # the sim tab no longer carries the panel
    sim = dashboard.PAGE.split('<section id=s-sim>')[1].split('</section>')[0]
    assert 'b-recon-run' not in sim and 'recon-surfaces' not in sim
    assert 'sel-recon-sc' not in sim


def test_residuals_tab_carries_the_whole_panel():
    sec = dashboard.PAGE.split('<section id=s-residuals>')[1].split('</section>')[0]
    for eid in ("res-sum", "b-res-reset", "sel-res-sc", "inp-res-n", "inp-res-seed",
                "b-res-run", "res-runmsg", "res-blurb", "res-kpis", "res-bottom",
                "res-grid", "res-cum", "res-amp", "res-fields", "sel-res-surface",
                "inp-res-user", "b-res-insp", "res-insp", "sel-res-run",
                "b-res-load", "res-hist"):
        assert f"id={eid}" in sec, eid


def test_residuals_element_ids_are_unique_in_the_page():
    ids = re.findall(r'id=([a-zA-Z][\w-]*)', dashboard.PAGE)
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    assert not dupes, dupes


def test_residuals_tab_static_bundle_is_wired():
    js = open("static/app.js", encoding="utf-8").read()
    css = open("static/app.css", encoding="utf-8").read()
    assert "if(name==='residuals'){loadReconTab();}" in js
    # every element the residuals block touches exists in the HTML
    blk = js.split("/* ---- Stateless-inference residual reconstruction")[1]
    blk = blk.split("/* ---- AKM shell")[0]
    want = set(re.findall(r"\$\('([a-z0-9-]+)'\)", blk))
    have = set(re.findall(r"id=([a-zA-Z][\w-]*)", dashboard.PAGE))
    dynamic = {"res-rep"}  # injected by renderRecon into #res-amp
    assert (want - dynamic) <= have, sorted(want - dynamic - have)
    assert ".res-cols{" in css and ".res-surface{" in css
    # no orphaned pre-tab ids left behind
    for old in ("recon-sum", "recon-surfaces", "recon-runmsg", "b-recon-run",
                "sel-recon-sc", "recon-insp"):
        assert old not in js, old
        assert f"id={old}" not in dashboard.PAGE, old


def test_residuals_tab_still_renders_a_live_report():
    d = client.post("/api/recon/run",
                    json={"scenario": "stateless_coding", "n": 24, "seed": 1}).json()
    assert d["report"]["surfaces"]
    assert d["report"]["cumulative"][-1]["accuracy"] >= 0
    assert d["report"]["amplification"]["delta"] >= 0
