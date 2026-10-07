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
