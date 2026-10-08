"""Monotone cumulative + solo keyed by store."""
from __future__ import annotations

from iforensics.sim import reconstruction as eng
from iforensics.sim.recon.core import metrics


def test_cumulative_is_monotone():
    eng.run_session("stateless_chat", seed=5, n=16)
    cum = metrics.cumulative("u-recon-chat")
    accs = [c["accuracy"] for c in cum]
    assert len(accs) == len(eng.STORE_IDS)
    assert metrics.check_monotone(accs)
    assert metrics.check_monotone([0.0, 0.0, 0.5, 0.5, 1.0])
    assert not metrics.check_monotone([0.5, 0.4])
    eng.STATE.purge("u-recon-chat")


def test_solo_keyed_by_store_ids():
    eng.run_session("stateless_support", seed=5, n=12)
    assert sorted(metrics.solo("u-recon-support")) == sorted(eng.STORE_IDS)
    eng.STATE.purge("u-recon-support")
