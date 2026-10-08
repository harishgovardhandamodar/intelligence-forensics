"""Assembly: scored recovery, unscored candidates, complementary merge."""
from __future__ import annotations

from iforensics.sim.recon.attacks import membership, near_dup, progressive
from iforensics.sim.recon.core import assembly as asm
from iforensics.sim import reconstruction as eng


def test_full_disclosure_recovers():
    out = asm.assemble(["call 900-11-2222 now"], {"ssn": "900-11-2222"})
    assert out["scored"] is True and out["recovered"] == 1
    assert out["mean_accuracy"] == 1.0 and out["coverage"] == 1.0


def test_without_truth_no_scored_claim():
    out = asm.assemble(["call 900-11-2222 now"])
    assert out["scored"] is False and out["mean_accuracy"] == 0.0
    assert out["candidates"] and out["candidates"][0]["shape"] == "###-##-####"


def test_complementary_fragments_merge():
    from iforensics.sim import queries
    masks = queries.mask_schedule("900-11-2222", 6, complete=True)
    out = asm.assemble([f"note {m} here" for m in masks],
                       {"ssn": "900-11-2222"})
    assert out["fields"]["ssn"]["assembled"] == "900-11-2222"
    assert out["mean_accuracy"] == 1.0


def test_attack_strategies_run_on_engine_user():
    eng.run_session("stateless_chat", seed=4, n=12)
    uid = "u-recon-chat"
    assert progressive.progressive(uid)["strategy"] == "progressive"
    nd = near_dup.near_dup(uid)
    assert nd["strategy"] == "near-dup" and nd["mean_accuracy"] >= 0.0
    assert nd["families"] >= 0
    mb = membership.membership(uid, ["900-11-2222", "000-00-0000"])
    assert mb["strategy"] == "membership" and mb["n_hits"] >= 0
    eng.STATE.purge(uid)
