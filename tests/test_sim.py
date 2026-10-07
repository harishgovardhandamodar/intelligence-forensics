"""Unit tests for the reconstruction-simulation engine (P8.1).

Hermetic by design: hash embeddings, numpy store, seeded synthetic data.
No torch, no Milvus, no network.
"""
from iforensics.sim import analysis as anal
from iforensics.sim import attacks as att
from iforensics.sim import embeddings as emb
from iforensics.sim import gateway as gwmod
from iforensics.sim import queries as queries_mod
from iforensics.sim import sensitive as sens
from iforensics.sim import store as store_mod


def test_sensitive_seeded_and_collision_proof():
    a = sens.generate("ssn", seed=42)
    b = sens.generate("ssn", seed=42)
    assert a["value"] == b["value"] and a["sensitivity"] == "critical"
    assert a["value"].startswith("9"), "must use the never-issued 900-series"
    assert sens.generate("credit_card", seed=1)["value"].startswith("4242")
    assert sens.generate("api_key", seed=1)["value"].startswith("sk-test-")
    assert sens.generate("aws_key", seed=1)["value"].startswith("AKIA")


def test_mask_schedule_assembles():
    sched = queries_mod.mask_schedule("123-45-6789", 3)
    assert len(sched) == 3
    assert all(set(m) <= set("*-0123456789") for m in sched)
    out = att.assemble_fragments(sched)
    assert out == {"assembled": "123-45-6789", "coverage": 1.0}
    # every prefix keeps prior reveals (monotone disclosure)
    for prev, nxt in zip(sched, sched[1:]):
        for pch, nch in zip(prev, nxt):
            if pch != "*":
                assert nch == pch


def test_near_duplicates_rank_above_unrelated():
    e = emb.HashEmbedder()
    base = "What is my blood pressure trend?"
    dups = queries_mod.near_duplicates(base, seed=7)
    assert len(dups) == 4 and dups[0] == base
    bv = e.embed_one(base)
    dup_scores = [emb.cosine(bv, e.embed_one(d)) for d in dups[1:]]
    unrelated = emb.cosine(bv, e.embed_one("Deploy kubernetes with terraform"))
    assert min(dup_scores) > unrelated
    assert e.embed_one(base) == e.embed_one(base)  # deterministic


def test_store_search_filter_and_dim_guard():
    import pytest
    st = store_mod.NumpyStore(dim=8)
    e = emb.HashEmbedder(dim=8)
    st.add(["alpha beta", "gamma delta"],
           e.embed(["alpha beta", "gamma delta"]),
           [{"user_id": "u1"}, {"user_id": "u2"}])
    hits = st.search(e.embed_one("alpha beta"), top_k=5)
    assert hits[0]["text"] == "alpha beta" and hits[0]["score"] > 0.9
    assert [h["text"] for h in st.search(e.embed_one("alpha beta"),
                                        filtr={"user_id": "u2"})] == ["gamma delta"]
    with pytest.raises(ValueError):
        st.add(["x"], [[0.0] * 4], [{}])
    assert len(st) == 2 and st.clear() == 2 and len(st) == 0


def test_gateway_roundtrip():
    st = store_mod.NumpyStore()
    gw = gwmod.MockGateway(st, emb.HashEmbedder())
    out = gw.process_query("What is my BP?", {"user_id": "u"},
                           mask="140/90", step=1)
    assert "140/90" in out["response"] and len(out["ids"]) == 2
    assert len(st) == 2


def test_progressive_attack_recovers_secret():
    e = emb.HashEmbedder()
    sched = queries_mod.mask_schedule("AKIAIOSFODNN7EXAMPLE", 3)
    texts = [f"How do I connect to AWS? Key {m}" for m in sched]
    vecs = e.embed(texts)
    res = att.progressive_attack(texts, vecs)
    assert res["n_clusters"] == 1
    assert res["clusters"][0]["coverage"] == 1.0
    assert res["clusters"][0]["assembled"].replace(" ", "") == \
        "AKIAIOSFODNN7EXAMPLE" or "AKIA" in res["clusters"][0]["assembled"]
    # membership: used value scores high, fresh randomness does not
    used = att.membership_score(e.embed_one("AKIAIOSFODNN7EXAMPLE"), vecs)
    fresh = att.membership_score(e.embed_one("zzzzqqqqxxxxvvvv"), vecs)
    assert used["likely_member"] and used["max_score"] > fresh["max_score"]


def test_accuracy_and_curve():
    r = anal.char_accuracy("123-45-6789", "123-45-6789")
    assert r == {"accuracy": 1.0, "matched": 9, "total": 9, "recovered": True}
    r2 = anal.char_accuracy("123-**-****", "123-45-6789")
    assert r2["accuracy"] < 1.0 and not r2["recovered"]
    rep = anal.field_report({"ssn": "123-45-6789"}, {"ssn": "123-45-6789"})
    assert rep["recovered"] == 1 and rep["mean_accuracy"] == 1.0
    curve = anal.progression_curve(
        "123-45-6789",
        ["***-**-6789", "123-**-****", "***-45-6789", "123-45-6789"],
        att.assemble_fragments)
    assert [c["accuracy"] for c in curve][-1] == 1.0
    assert curve[-1]["recovered"] is True
    assert curve[0]["accuracy"] <= curve[-1]["accuracy"]


def test_connect_factory_defaults_to_numpy(monkeypatch):
    monkeypatch.delenv("MILVUS_URL", raising=False)
    store, note = store_mod.connect()
    assert isinstance(store, store_mod.NumpyStore) and "numpy" in note


def _sim_client():
    from fastapi.testclient import TestClient
    import dashboard
    return TestClient(dashboard.app)


def test_sim_api_full_flow():
    c = _sim_client()
    assert c.post("/api/sim/reset").status_code == 200
    b = c.post("/api/sim/begin", json={"user_id": "u1",
                                       "truth": {"ssn": "123-45-6789"}})
    assert b.status_code == 200 and b.json()["fields"] == ["ssn"]
    for i, m in enumerate(["***-**-6789", "123-**-****", "123-45-6789"]):
        r = c.post("/api/sim/ingest",
                   json={"prompt": f"What is my trend? Ref: {m}",
                         "mask": m, "step": i,
                         "metadata": {"user_id": "u1", "scenario": "t"}})
        assert r.status_code == 200 and len(r.json()["ids"]) == 2
    a = c.post("/api/sim/attack",
               json={"kind": "progressive", "user_id": "u1"})
    assert a.status_code == 200 and a.json()["n_clusters"] >= 1
    rep = c.get("/api/sim/report", params={"user_id": "u1"})
    assert rep.status_code == 200
    body = rep.json()
    assert body["fields"]["ssn"]["recovered"] is True
    assert body["curves"]["ssn"][-1]["accuracy"] == 1.0
    m = c.post("/api/sim/attack",
               json={"kind": "membership", "user_id": "u1",
                     "value": "123-45-6789"})
    assert m.json()["likely_member"] is True
    assert c.post("/api/sim/attack",
                  json={"kind": "nope", "user_id": "u1"}).status_code == 400
    assert c.get("/api/sim/report",
                 params={"user_id": "nobody"}).status_code == 404
    u = c.get("/api/sim/users")
    assert any(x["user_id"] == "u1" and x["pairs"] == 3 for x in u.json()["users"])
    c.post("/api/sim/reset")


def test_sim_demo_and_validation():
    c = _sim_client()
    c.post("/api/sim/reset")
    d = c.post("/api/sim/demo")
    assert d.status_code == 200 and d.json()["users"] == ["demo-health", "demo-code"]
    r = c.get("/api/sim/report", params={"user_id": "demo-health"})
    assert r.status_code == 200 and r.json()["mean_accuracy"] > 0
    assert c.post("/api/sim/ingest", json={"prompt": ""}).status_code == 400
    assert c.post("/api/sim/begin", json={"user_id": ""}).status_code == 400
    c.post("/api/sim/reset")


def test_structure_attack_survives_paraphrase():
    texts = [
        "What is my blood pressure trend? Ref: ***-**-6789",
        "bp reading was 123-**-**** per your last message",
        "Could you tell me the pattern? recorded as ***-45-6789, thanks",
        "Deploy the kubernetes manifest with terraform replicas",
        "My other value is 999-99-9999 ok?",
    ]
    out = att.structure_attack(texts)
    top = out["secrets"][0]
    assert top["assembled"] == "123-45-6789" and top["coverage"] == 1.0
    assert top["occurrences"] == 3
    others = [s["assembled"] for s in out["secrets"][1:]]
    assert "999-99-9999" in others  # conflicting secret stays separate


def test_structure_attack_conflicting_values_split():
    texts = ["key A is ABCD-1234 ok?", "key B is ABCD-5678 ok?"]
    out = att.structure_attack(texts)
    assert out["n_groups"] == 2
    assert {s["assembled"] for s in out["secrets"]} == {"ABCD-1234", "ABCD-5678"}


def test_candidate_membership_beats_carrier_noise():
    e = emb.HashEmbedder()
    texts = ["What is my trend? Ref: ***-**-6789",
             "bp reading was 123-**-**** lately",
             "Deploy the kubernetes manifest"]
    hit = att.membership_candidate("123-45-6789", texts, e.embed_one)
    miss = att.membership_candidate("000-00-0000", texts, e.embed_one)
    assert hit["likely_member"] and hit["max_score"] >= 0.5
    assert not miss["likely_member"] and miss["max_score"] < hit["max_score"]


def test_partial_schedule_plateaus():
    sched = queries_mod.mask_schedule("123-45-6789", 3, complete=False)
    assert all(s[-1] == "*" for s in sched)  # final slot never revealed
    out = att.assemble_fragments(sched)
    assert out["assembled"] == "123-45-678"
    # positional accuracy against truth plateaus below 1.0: the honest regime
    r = anal.char_accuracy(out["assembled"], "123-45-6789")
    assert r == {"accuracy": 0.889, "matched": 8, "total": 9,
                 "recovered": False}
    full = queries_mod.mask_schedule("123-45-6789", 3, complete=True)
    assert att.assemble_fragments(full)["coverage"] == 1.0


def test_dlp_scan_modes_and_journal():
    from iforensics.sim import dlp
    hits = dlp.scan("My SSN is 123-45-6789 ok?")
    assert any(h["kind"] == "ssn" for h in hits)
    assert dlp.scan("plain friendly text") == []
    import pytest
    with pytest.raises(ValueError):
        dlp.Policy("explode")
    assert dlp.Policy("off").inspect("sk-test-abc", "q")["blocked"] is False
    p = dlp.Policy("block")
    out = p.inspect("key AKIAIOSFODNN7EXAMPLE here", "q")
    assert out["blocked"] is True and out["text"] == ""
    r = dlp.Policy("redact").inspect("SSN 123-45-6789 noted", "q")
    assert r["blocked"] is False and "[REDACTED:ssn]" in r["text"]
    assert "123-45-6789" not in r["text"]
    a = dlp.Policy("audit").inspect("SSN 123-45-6789 noted", "q")
    assert a["text"].startswith("SSN") and len(a["findings"]) == 1
    s = p.summary()
    assert s["mode"] == "block" and s["interceptions"] == 1


def test_gateway_enforces_dlp():
    from iforensics.sim import dlp
    from iforensics.sim import embeddings as emb
    st = store_mod.NumpyStore()
    gw = gwmod.MockGateway(st, emb.HashEmbedder())
    pol = dlp.Policy("block")
    out = gw.process_query("My SSN is 123-45-6789 ok?", {"user_id": "u"},
                           dlp=pol)
    assert out["blocked"] is True
    assert "blocked" in out["response"].lower()
    assert len(st) == 2  # refusal record stored, flagged
    red = dlp.Policy("redact")
    out2 = gw.process_query("My SSN is 123-45-6789 ok?", {"user_id": "u"},
                            dlp=red)
    assert out2["blocked"] is False
    assert "123-45-6789" not in out2["response"]


def test_estimate_without_truth():
    from iforensics.sim import estimate as est
    texts = ["Ref: ***-**-6789 here", "Ref: 123-**-**** there",
             "plain carrier words only"]
    out = est.estimate_exposure(texts)
    assert out["exposure"] == 1.0
    assert out["groups"][0]["confidence"] > 0
    empty = est.estimate_exposure(["nothing secret here at all"])
    assert empty["exposure"] == 0.0


def test_worker_sim_reconstruct_kind():
    import cli
    out = cli._swarm_execute("sim_reconstruct",
                             {"texts": ["Ref: ***-**-6789", "Ref: 123-45-6789"],
                              "candidates": ["123-45-6789"]}, "m")
    assert out["n_groups"] >= 1
    assert out["membership"]["123-45-6789"]["likely_member"] is True


def test_sim_dlp_endpoints():
    c = _sim_client()
    c.post("/api/sim/reset")
    assert c.get("/api/sim/dlp").json()["mode"] == "off"
    assert c.post("/api/sim/dlp", json={"mode": "explode"}).status_code == 400
    assert c.post("/api/sim/dlp", json={"mode": "redact"}).status_code == 200
    c.post("/api/sim/begin", json={"user_id": "u9", "truth": {"ssn": "1"}})
    c.post("/api/sim/ingest", json={"prompt": "SSN 123-45-6789 here",
                                    "metadata": {"user_id": "u9"}})
    rep = c.get("/api/sim/report", params={"user_id": "u9"}).json()
    assert rep["dlp"]["mode"] == "redact"
    assert rep["dlp"]["interceptions"] >= 1
    assert "estimates" in rep and "reconstructed" in rep
    c.post("/api/sim/dlp", json={"mode": "off"})
    c.post("/api/sim/reset")


def test_coding_styles_shapes():
    import sys
    sys.path.insert(0, ".")
    from sim.scenarios import coding_api_keys as cak
    import pytest
    with pytest.raises(ValueError):
        cak.build(style="yolo")
    one = cak.build(seed=1, n=60, style="one-off")
    assert len(one["turns"]) == 3
    assert set(one["truth"]) == {"api_key", "aws_key"}
    reg = cak.build(seed=1, n=12, style="regular")
    assert len(reg["turns"]) == 12
    vibe = cak.build(seed=1, n=20, style="vibe")
    assert len(vibe["turns"]) == 20
    full_vals = [v for v in vibe["truth"].values()]
    full_hits = sum(1 for t in vibe["turns"]
                    if any(v in t["prompt"] for v in full_vals))
    assert full_hits >= 8  # vibe pastes full secrets often


def test_plausibility_table_marks_gating():
    from iforensics.sim import plausibility as plaus
    out = plaus.assess()
    assert len(out["actions"]) == 8
    gates = [a for a in out["actions"] if a.get("gating")]
    assert len(gates) == 1 and gates[0]["action"] == "attacker reads the vector store"
    assert "verdict" in out and all(
        a["plausibility"] in ("high", "medium", "low") for a in out["actions"])


def test_runner_describe_has_diagrams():
    from iforensics.sim import runner as sim_runner
    descs = sim_runner.describe()
    assert {d["id"] for d in descs} == {"chatbot_health", "chatbot_financial",
                                        "coding_api_keys", "coding_secrets"}
    for d in descs:
        assert d["title"] and d["fields"]
        assert d["diagram"].startswith("flowchart ")
        assert "```" not in d["diagram"]  # raw source, fences added by UI


def test_runner_executes_scenario_in_process(tmp_path, monkeypatch):
    from iforensics import config
    from iforensics.sim import runner as sim_runner
    monkeypatch.setattr(config, "EVIDENCE_DIR", str(tmp_path))
    out = sim_runner.run_scenario("chatbot_health", n=12, seed=7)
    assert out["user_id"] == "u-health"
    assert out["report"]["recovered"] == 2
    assert out["report"]["mean_accuracy"] == 1.0
    assert "ssn" in out["membership"]
    assert "run_id" in out
    import os
    assert os.path.isfile(os.path.join(
        str(tmp_path), "sim-reports", out["run_id"], "chatbot_health.json"))


def test_runner_rejects_unknown_scenario():
    import pytest
    from iforensics.sim import runner as sim_runner
    with pytest.raises(ValueError):
        sim_runner.run_scenario("nope")


def test_sim_run_and_scenarios_endpoints():
    c = _sim_client()
    c.post("/api/sim/reset")
    s = c.get("/api/sim/scenarios")
    assert s.status_code == 200 and len(s.json()["scenarios"]) == 4
    assert c.post("/api/sim/run", json={"scenario": "nope"}).status_code == 400
    assert c.post("/api/sim/run",
                  json={"scenario": "chatbot_health", "style": "yolo"}
                  ).status_code == 400
    r = c.post("/api/sim/run",
               json={"scenario": "chatbot_health", "n": 12, "seed": 7})
    assert r.status_code == 200
    body = r.json()["results"]["chatbot_health"]
    assert body["report"]["recovered"] == 2
    c.post("/api/sim/reset")


def test_scenario_builders_importable():
    import importlib
    from iforensics.sim import runner as sim_runner
    for dotted in sim_runner.BUILDERS.values():
        assert importlib.import_module(dotted) is not None


def test_docker_image_ships_sim_client():
    import os
    from iforensics import config
    with open(os.path.join(config.BASE_DIR, "Dockerfile")) as f:
        text = f.read()
    # the in-tab runner imports sim.scenarios.* inside the container —
    # forgetting the COPY line is exactly the ModuleNotFoundError seen live
    assert "COPY sim/ ./sim/" in text
    assert os.path.isfile(os.path.join(config.BASE_DIR, "sim", "__init__.py"))


def test_dossier_bands_findings_and_timeline():
    from iforensics.sim import dossier as dos
    results = {
        "chatbot_health": {
            "user_id": "u-health", "n_turns": 12, "style": "regular",
            "attack": {"n_clusters": 2, "mean_cohesion": 0.9},
            "membership": {},
            "report": {"recovered": 1, "n_fields": 2, "mean_accuracy": 0.5,
                       "dlp": {"mode": "off", "interceptions": 0},
                       "estimates": {"exposure": 1.0, "n_groups": 2},
                       "fields": {
                           "ssn": {"accuracy": 1.0, "matched": 9, "total": 9,
                                   "recovered": True, "direct_exposure": True,
                                   "curve": []},
                           "bp": {"accuracy": 0.0, "matched": 0, "total": 6,
                                  "recovered": False, "direct_exposure": False,
                                  "curve": []}},
                       "reconstructed": [
                           {"assembled": "123-45-6789", "coverage": 1.0,
                            "occurrences": 3}]},
        },
        "broken": {"error": "ValueError: nope"},
    }
    entries = [
        {"seq": 1, "actor": "orchestrator", "action": "run.start",
         "task_id": "", "artifact_sha256": "", "detail": "x"},
        {"seq": 2, "actor": "sim:chatbot_health", "action": "task.complete",
         "task_id": "r-chatbot_health", "artifact_sha256": "ab" * 32,
         "detail": "recovered=1/2"},
    ]
    d = dos.build_dossier("r1", results, entries,
                          {"ok": True, "checked": 2, "failed_at": None})
    assert [f["band"] for f in d["findings"]] == ["critical", "low"]
    assert d["findings"][0]["reconstructed"] == "123-45-6789"
    assert d["scenarios"]["broken"] == {"error": "ValueError: nope"}
    assert len(d["timeline"]) == 2 and d["ledger"] == {
        "ok": True, "checked": 2, "failed_at": None}
    md = dos.dossier_markdown(d)
    assert "§0 Request" in md and "§3 Ledger timeline" in md
    assert "123-45-6789" in md and "chain OK" in md


def test_dossier_attributes_assemblies_per_field():
    from iforensics.sim import dossier as dos
    results = {
        "chatbot_health": {
            "user_id": "u-health", "n_turns": 12, "style": "regular",
            "attack": {}, "membership": {},
            "truth": {"ssn": "123-45-6789", "bp": "140/90"},
            "report": {"recovered": 2, "n_fields": 2, "mean_accuracy": 1.0,
                       "dlp": {}, "estimates": {},
                       "fields": {
                           "ssn": {"accuracy": 1.0, "matched": 9, "total": 9,
                                   "recovered": True, "direct_exposure": True,
                                   "curve": []},
                           "bp": {"accuracy": 1.0, "matched": 6, "total": 6,
                                  "recovered": True, "direct_exposure": True,
                                  "curve": []}},
                       "reconstructed": [
                           {"assembled": "123-45-6789", "coverage": 1.0,
                            "occurrences": 3},
                           {"assembled": "140/90", "coverage": 1.0,
                            "occurrences": 3}]},
        },
    }
    d = dos.build_dossier("r2", results, [],
                          {"ok": True, "checked": 0, "failed_at": None})
    by_field = {f["field"]: f["reconstructed"] for f in d["findings"]}
    assert by_field == {"ssn": "123-45-6789", "bp": "140/90"}


def test_sim_batch_run_id_and_dossier_endpoints(tmp_path, monkeypatch):
    from iforensics import config
    monkeypatch.setattr(config, "EVIDENCE_DIR", str(tmp_path))
    c = _sim_client()
    r = c.post("/api/sim/run", json={"scenario": "chatbot_health",
                                     "n": 6, "seed": 7})
    assert r.status_code == 200
    run_id = r.json()["run_id"]
    assert run_id.startswith("sim-")
    d = c.get("/api/sim/dossier", params={"run_id": run_id})
    assert d.status_code == 200
    body = d.json()
    assert body["ledger"]["ok"] is True
    assert any(f["field"] == "ssn" for f in body["findings"])
    md = c.get("/api/sim/dossier.md", params={"run_id": run_id})
    assert md.status_code == 200 and "Sim dossier" in md.text
    runs = c.get("/api/sim/runs").json()["runs"]
    assert run_id in runs
    assert c.get("/api/sim/dossier", params={"run_id": "nope"}).status_code == 404
