"""Mitigations flatten the curve: caps, never-log-full, DLP, TTL, vectors."""
from __future__ import annotations

from iforensics.sim import reconstruction as eng
from iforensics.sim.recon import mitigations as mit


def _records():
    eng.run_session("stateless_coding", seed=13, n=24)
    recs = eng.STATE.records_for("u-recon-coding")
    eng.STATE.purge("u-recon-coding")
    return recs


def test_sweep_flattens_shapes():
    recs = _records()
    assert mit.shape_fraction(recs) > 0
    sw = mit.sweep(recs, current_turn=24)
    assert sw["baseline"]["with_shapes"] >= sw["dlp_redact"]["with_shapes"] == 0.0
    assert sw["baseline"]["with_shapes"] >= sw["dlp_block"]["with_shapes"] == 0.0
    assert sw["dlp_audit"]["with_shapes"] == sw["baseline"]["with_shapes"]
    assert sw["cap_10_turns"]["with_text"] <= sw["baseline"]["with_text"]


def test_mitigations_are_pure_and_deterministic():
    recs = _records()
    before = [r["text"] for r in recs]
    assert mit.dlp(recs, "redact") != recs  # new objects
    assert [r["text"] for r in recs] == before  # inputs untouched
    assert mit.sweep(recs) == mit.sweep(recs)
    try:
        mit.dlp(recs, "destroy")
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("bad DLP mode accepted")


def test_encrypt_embeddings_withholds_vectors():
    recs = _records()
    enc = mit.encrypt_embeddings(recs)
    vecs = [r for r in enc
            if (r["surface"] if isinstance(r, dict) else "") == "embeddings"]
    assert vecs and all("vector" not in r.get("meta", {}) for r in vecs)
