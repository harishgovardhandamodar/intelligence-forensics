"""Report assembly for the reconstruction sim (shared by API + runner).

`build_report` folds every analysis surface for one user — cluster attack,
structure assemblies, field accuracy, progression curves, estimates,
plausibility, DLP state — into the single dict the dashboard tab, the CLI
client and the in-tab runner all consume. One builder, three callers.
"""
from __future__ import annotations


class UnknownUser(KeyError):
    pass


def build_report(state, user_id: str) -> dict:
    """Accuracy report: assembled secrets vs registered ground truth."""
    from . import analysis as sim_analysis
    from . import attacks as sim_attacks
    from . import estimate as sim_estimate
    from . import plausibility as sim_plaus
    truth = state.get_truth(user_id)
    if not truth:
        raise UnknownUser(user_id)
    items = state.store.get_all(filtr={"user_id": user_id})
    texts, _vecs = state.store.texts_vectors(filtr={"user_id": user_id})
    res = sim_attacks.progressive_attack(texts, _vecs)
    # structure path: carrier-independent assemblies (bare secret-shaped
    # spans, so positional scoring applies directly)
    struct = sim_attacks.structure_attack(texts)
    by_field: dict[str, str] = {}
    best_score: dict[str, float] = {}
    for s in struct["secrets"]:
        for field, tv in truth.items():
            r = sim_analysis.char_accuracy(s["assembled"], tv)
            if r["accuracy"] > best_score.get(field, 0):
                best_score[field] = r["accuracy"]
                by_field[field] = s["assembled"]
    rep = sim_analysis.field_report(truth, by_field, sim_analysis.window_accuracy)
    for field, tv in truth.items():
        rep["fields"][field]["direct_exposure"] = \
            any(tv in t for t in texts) if tv else False
    curves = {}
    for field, tv in truth.items():
        sched = sorted({(it["metadata"].get("step", 0), it["metadata"].get("mask", ""))
                        for it in items
                        if it["metadata"].get("mask")
                        and it["metadata"].get("field", field) == field})
        curves[field] = sim_analysis.progression_curve(
            tv, [m for _, m in sched], sim_attacks.assemble_fragments)
    rep["curves"] = curves
    rep["user_id"] = user_id
    rep["backend"] = state.backend_note
    rep["clusters"] = res["n_clusters"]
    rep["plausibility"] = sim_plaus.assess()
    rep["estimates"] = sim_estimate.estimate_exposure(texts)
    rep["dlp"] = state.get_policy()
    rep["reconstructed"] = [
        {"assembled": s["assembled"], "coverage": s["coverage"],
         "occurrences": s["occurrences"]}
        for s in struct["secrets"][:10]]
    return rep
