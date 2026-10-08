"""Embeddings alone yield text accuracy 0 (linkage only)."""
from __future__ import annotations

from iforensics.sim import reconstruction as eng
from iforensics.sim.recon.core import linkage
from iforensics.sim.recon.core import metrics


def test_embeddings_zero_text_everywhere():
    eng.run_session("stateless_coding", seed=9, n=16)
    fam = linkage.families("u-recon-coding")
    assert fam["text_accuracy"] == 0.0
    assert fam["n_vectors"] > 0
    assert metrics.solo("u-recon-coding")["embeddings"]["accuracy"] == 0.0
    eng.STATE.purge("u-recon-coding")
