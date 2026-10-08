"""Reproducibility: same (scenario, seed, n) → identical reports."""
from __future__ import annotations

from iforensics.sim import reconstruction as eng
from iforensics.sim.recon.scenarios import finance


def _sig(rep: dict) -> tuple:
    return (rep["mean_accuracy"], rep["recovered"], rep["n_records"],
            tuple(s["accuracy"] for s in rep["surfaces"]))


def test_engine_session_reproducible():
    a = eng.run_session("stateless_coding", seed=7, n=12)["report"]
    b = eng.run_session("stateless_coding", seed=7, n=12)["report"]
    assert _sig(a) == _sig(b)
    eng.STATE.purge("u-recon-coding")


def test_generic_scenario_reproducible():
    a = finance.SCENARIO.run(seed=7, n=12)["report"]
    b = finance.SCENARIO.run(seed=7, n=12)["report"]
    assert _sig(a) == _sig(b)
