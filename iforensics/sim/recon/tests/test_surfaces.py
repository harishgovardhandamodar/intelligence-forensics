"""Surfaces: engine-backed readers + staged determinism + reserved secrets."""
from __future__ import annotations

from iforensics.sim import reconstruction as eng
from iforensics.sim.recon.core import retention, secrets
from iforensics.sim.recon.core.surfaces import base
from iforensics.sim.recon.core.surfaces import (
    apm_error,
    api_gateway,
    backup_snapshot,
    billing,
    cache,
    embeddings,
    feature_store,
    gpu_debug,
    human_ops,
    infrastructure,
    logging,
    product_analytics,
    rag_index,
    rate_limit_quota,
    session_correlation,
    tool_use,
    training,
    waf_dlp,
)

ENGINE_MODULES = (logging, billing, embeddings, cache, training,
                  infrastructure, human_ops)
STAGED_MODULES = (api_gateway, rate_limit_quota, apm_error, waf_dlp,
                  product_analytics, feature_store, rag_index, tool_use,
                  session_correlation, backup_snapshot, gpu_debug)


def test_retention_constants_are_the_engine_objects():
    assert retention.RATE is eng.RATE
    assert retention.STORE_IDS == eng.STORE_IDS
    assert len(retention.SURFACES) == 8


def test_engine_surface_ids_match_store_ids():
    assert sorted(m.SURFACE.id for m in ENGINE_MODULES) == sorted(eng.STORE_IDS)


def test_engine_surfaces_read_live_records():
    eng.run_session("stateless_coding", seed=11, n=12)
    for m in ENGINE_MODULES:
        rows = m.SURFACE.read("u-recon-coding")
        assert isinstance(rows, list)
        assert all(isinstance(r, base.Residual) for r in rows)
    eng.STATE.purge("u-recon-coding")


def test_embeddings_text_accuracy_is_zero():
    assert embeddings.SURFACE.text_accuracy() == 0.0
    assert embeddings.POLICY["text_accuracy"] == 0.0


def test_staged_surfaces_are_deterministic():
    for m in STAGED_MODULES:
        assert m.SURFACE.staged is True
        a, b = type(m.SURFACE)(), type(m.SURFACE)()
        turns = [base.Turn(index=i, user_id="u",
                           prompt=f"turn number {i} with ssn 900-11-2222 "
                                  f"padded to some length {i * 7}")
                 for i in range(60)]
        ra = [r.text for t in turns for r in a.retain(t)]
        rb = [r.text for t in turns for r in b.retain(t)]
        assert ra == rb and ra, m.SURFACE.id
        assert len(a.read()) == len(ra)
        assert a.clear() == len(ra) and a.read() == []


def test_staged_rates_match_retention_catalogue():
    for m in STAGED_MODULES:
        cat = retention.STAGED_RATES[m.SURFACE.id]
        assert (m.SURFACE.rate_num, m.SURFACE.rate_den) == cat["full"]
        assert m.SURFACE.head_chars == cat["head"]


def test_secrets_are_reserved_only():
    for shape in secrets.SHAPES:
        v = secrets.generate(shape, seed=3)["value"]
        assert secrets.is_reserved(shape, str(v)), (shape, v)


def test_truth_registry_refuses_non_reserved():
    reg = secrets.TruthRegistry()
    reg.register("u", {"ssn": "900-11-2222"})
    assert reg.get("u") == {"ssn": "900-11-2222"}
    try:
        reg.register("v", {"ssn": "123-45-6789"})
    except ValueError:
        pass
    else:  # pragma: no cover
        raise AssertionError("non-reserved SSN accepted")
