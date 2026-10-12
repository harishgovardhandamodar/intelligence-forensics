"""Rogue-agent swarm simulation — engine, grounding and API tests (Assure).

Hermetic: synthetic catalogue only, seeded, deterministic, no network. The
OpenShell runtime is a *model* (sandbox · policy engine · supervisor ·
privacy router · hash-chained audit); nothing is executed. Runs persist under
`evidence/rogue-reports/` exactly like recon runs.
"""
from __future__ import annotations

import pytest

import dashboard
from iforensics.sim import rogue

client = None  # fastapi TestClient, bound lazily

_GAP = {"detect_policy_only": 0.5, "detect_missed_subtle": 0.0}


@pytest.fixture(autouse=True)
def _client():
    global client
    from fastapi.testclient import TestClient
    client = TestClient(dashboard.app)
    yield


def _labels(r: dict) -> dict[str, str]:
    return {v["agent"]: v["label"] for v in r["detection"]["verdicts"]}


# --------------------------------------------------------------------------- #
# catalogue
# --------------------------------------------------------------------------- #

def test_catalogue_is_exhaustive():
    sc = rogue.scenarios()
    assert len(sc) == 57
    cats = rogue.categories()
    assert [(c["id"], c["count"]) for c in cats] == [
        ("single", 15), ("swarm", 10), ("collude", 10),
        ("pollute", 10), ("detect", 9), ("control", 3),
    ]
    seen = set()
    for c in cats:
        assert set(c["ids"]) == {s["id"] for s in sc
                                 if s["category"] == c["id"]}
        seen |= set(c["ids"])
    assert seen == {s["id"] for s in sc} and len(seen) == 57


def test_catalogue_entries_well_formed():
    for s in rogue.scenarios():
        assert s["id"] and s["title"] and s["blurb"]
        assert s["diagram"].startswith("flowchart"), s["id"]
        assert "-->" in s["diagram"] and "OpenShell" in s["diagram"]
        assert s["n_agents"] > 0
        assert set(s["expect"]) == {"rogue", "colluders", "polluters",
                                    "benign", "missed"}
        assert s["detector"] in ("full", "policy_only", "behavior_only",
                                 "graph_only", "provenance_only")
        assert s["steps"] >= 2


# --------------------------------------------------------------------------- #
# engine determinism + zero false positives across the whole catalogue
# --------------------------------------------------------------------------- #

def test_every_scenario_runs_clean():
    """All 57 scenarios: audit chain must verify, no false positives,
    every intentional miss acknowledged, full-mode runs reach 100% recall."""
    for s in rogue.scenarios():
        r = rogue.run_scenario(s["id"], seed=42, persist=False)
        assert r["scenario"] == s["id"]
        assert r["audit_verify"]["ok"] is True, s["id"]
        assert r["events"] > 0
        m = r["detection"]["metrics"]
        assert m["false_positive"] == [], s["id"]
        assert m["missed_as_expected"] is True, s["id"]
        if r["mode"] == "full":
            # full detector catches everything except the two honest gaps
            expected = (1.0 if s["id"] not in _GAP else _GAP[s["id"]])
            assert m["recall"] == expected, s["id"]


def test_gap_scenarios_are_exactly_the_acknowledged_blind_spots():
    r = rogue.run_scenario("detect_policy_only", seed=42, persist=False)
    m = r["detection"]["metrics"]
    assert m["recall"] == 0.5 and m["false_negative"] == ["p1"]
    assert m["expected_missed"] == ["p1"]

    r = rogue.run_scenario("detect_missed_subtle", seed=42, persist=False)
    m = r["detection"]["metrics"]
    assert m["recall"] == 0.0 and m["false_negative"] == ["r1"]
    assert m["expected_missed"] == ["r1"]


def test_control_scenarios_never_flag():
    for sid in ("baseline_benign", "benign_noisy", "benign_buggy"):
        r = rogue.run_scenario(sid, seed=42, persist=False)
        assert set(_labels(r).values()) == {"benign"}, sid
        assert r["detection"]["metrics"]["false_positive"] == []


def test_deterministic_same_seed():
    a = rogue.run_scenario("collude_split_payload", seed=7, persist=False)
    b = rogue.run_scenario("collude_split_payload", seed=7, persist=False)
    assert _labels(a) == _labels(b)
    assert a["detection"]["metrics"] == b["detection"]["metrics"]
    assert a["audit_verify"] == b["audit_verify"]
    # a different seed may still collide, but the audit trail must verify
    c = rogue.run_scenario("collude_split_payload", seed=999, persist=False)
    assert c["audit_verify"]["ok"] is True


# --------------------------------------------------------------------------- #
# grounding: every verdict pins to a real audit entry + policy rule
# --------------------------------------------------------------------------- #

def test_verdict_grounding_resolves_to_audit_and_policy():
    for sid in ("rogue_exfil_net", "collude_split_payload", "pollute_corpus"):
        r = rogue.run_scenario(sid, seed=42, persist=False)
        audit_ids = {e["audit_id"] for e in r["audit"]}
        rule_ids = {r_["id"] for r_ in r["policy"]}
        for v in r["detection"]["verdicts"]:
            for ev in v["evidence"]:
                assert ev["audit_id"] in audit_ids, (sid, v["agent"])
                if ev["rule_id"]:
                    assert ev["rule_id"] in rule_ids, (sid, ev["rule_id"])
            for sig in v["signals"]:
                if sig["rule_id"]:
                    assert sig["rule_id"] in rule_ids, (sid, sig["rule_id"])
                if sig["audit_id"]:
                    assert sig["audit_id"] in audit_ids, (sid, v["agent"])
                # graph / provenance signals are layer-tagged and rule-free
                if sig["kind"] == "collusion":
                    assert sig["layer"] == "graph" and not sig["rule_id"]
                if sig["kind"] == "provenance":
                    assert sig["layer"] == "provenance" and not sig["rule_id"]
        malicious = [v for v in r["detection"]["verdicts"]
                     if v["label"] in ("rogue", "colluder", "polluter")]
        assert all(v["grounded"] for v in malicious), sid


def test_audit_chain_is_hash_linked():
    r = rogue.run_scenario("collude_split_payload", seed=42, persist=False)
    entries = r["audit"]
    assert entries and entries[0]["prev_hash"] == "openshell:genesis"
    for i in range(1, len(entries)):
        prev = entries[i - 1]
        assert entries[i]["prev_hash"] == prev["audit_id"]


def test_audit_integrity_breaks_when_tampered():
    r = rogue.run_scenario("collude_split_payload", seed=42, persist=False)
    assert r["audit_verify"]["ok"] is True
    assert r["audit_verify"]["checked"] == len(r["audit"])


# --------------------------------------------------------------------------- #
# detector modes: honestly expose coverage gaps
# --------------------------------------------------------------------------- #

def test_graph_layer_catches_collusion_alone():
    r = rogue.run_scenario("collude_split_payload", seed=42,
                           mode="graph_only", persist=False)
    m = r["detection"]["metrics"]
    assert m["recall"] == 1.0 and m["false_positive"] == []
    assert len(r["detection"]["clusters"]) == 1
    assert set(r["detection"]["clusters"][0]["members"]) == {"c1", "c2", "c3"}


def test_provenance_layer_catches_pollution_alone():
    r = rogue.run_scenario("pollute_corpus", seed=42,
                           mode="provenance_only", persist=False)
    m = r["detection"]["metrics"]
    assert m["recall"] == 1.0 and m["false_positive"] == []
    assert _labels(r)["p1"] == "polluter"


def test_off_layer_goes_blind():
    # collusion is invisible without the graph layer
    r = rogue.run_scenario("collude_split_payload", seed=42,
                           mode="policy_only", persist=False)
    assert r["detection"]["metrics"]["recall"] == 0.0
    # pollution is invisible without the provenance layer
    r = rogue.run_scenario("pollute_corpus", seed=42,
                           mode="graph_only", persist=False)
    assert r["detection"]["metrics"]["recall"] == 0.0
    # the honest suspect-only scenario stays blind in every single layer
    for mode in ("policy_only", "behavior_only", "graph_only",
                 "provenance_only"):
        r = rogue.run_scenario("detect_missed_subtle", seed=42,
                               mode=mode, persist=False)
        assert r["detection"]["metrics"]["recall"] == 0.0, mode


# --------------------------------------------------------------------------- #
# API
# --------------------------------------------------------------------------- #

def test_api_catalogue():
    d = client.get("/api/rogue/catalogue").json()
    assert len(d["scenarios"]) == 57
    assert [(c["id"], c["count"]) for c in d["categories"]] == [
        ("single", 15), ("swarm", 10), ("collude", 10),
        ("pollute", 10), ("detect", 9), ("control", 3),
    ]
    for s in d["scenarios"]:
        assert s["diagram"].startswith("flowchart")


def test_api_policy_surface():
    d = client.get("/api/rogue/policy").json()
    rules = d["policy"]
    assert len(rules) >= 20
    kinds = {x["kind"] for x in rules}
    assert {"fs.read", "fs.write", "net.egress", "proc.spawn",
            "cred.use", "memory.write", "model.call"} <= kinds
    layers = {x["layer"] for x in rules}
    assert {"filesystem", "network", "process", "credential",
            "privacy", "memory"} <= layers
    effects = {x["effect"] for x in rules}
    assert "allow" in effects and "deny" in effects


def test_api_run_persist_and_load():
    r = client.post("/api/rogue/run",
                    json={"scenario": "collude_split_payload", "seed": 42})
    assert r.status_code == 200
    body = r.json()
    run_id = body["run_id"]
    assert body["detection"]["metrics"]["recall"] == 1.0
    assert body["audit_verify"]["ok"] is True

    runs = client.get("/api/rogue/runs").json()["runs"]
    assert run_id in runs

    loaded = client.get("/api/rogue/run", params={"run_id": run_id}).json()
    first = loaded[next(iter(loaded))]
    assert first["detection"]["metrics"]["recall"] == 1.0

    missing = client.get("/api/rogue/run", params={"run_id": "nope"})
    assert missing.status_code == 404

    bad = client.post("/api/rogue/run", json={"scenario": "nope"})
    assert bad.status_code == 400

    reset = client.post("/api/rogue/reset").json()
    assert reset["ok"] is True and reset["cleared"] is False
    assert "persisted evidence" in reset["note"]


def test_api_mode_passthrough():
    r = client.post("/api/rogue/run", json={"scenario": "pollute_corpus",
                                            "mode": "provenance_only",
                                            "seed": 42}).json()
    assert r["mode"] == "provenance_only"
    assert r["detection"]["metrics"]["recall"] == 1.0