"""Scenario adapters: 9 workloads over the engine's session construction.

Three workloads map 1:1 onto engine scenarios (exact engine behavior).
The other six use the framework's generic builder below, which follows the
same construction contract as `build_session` (secret at the end of long
carriers, six reveal steps, deterministic resends + distractors) over the
engine's primitives (`queries.mask_schedule`, `queries.near_duplicates`,
`stable_seed`, `sensitive.generate`). Determinism scheme is identical, so
reports are comparable across all nine.
"""
from __future__ import annotations

ENGINE_MAP = {
    "health": "stateless_chat",
    "coding_api_keys": "stateless_coding",
    "support_tickets": "stateless_support",
}


def generic_session(scenario: str, fields: list[str], carriers: list[str],
                    seed: int = 42, n: int = 48, steps: int = 6) -> dict:
    """Build turns + truth for a non-engine scenario (same contract)."""
    from ... import queries
    from ... import reconstruction as _eng
    from ..core import secrets as _secrets
    user_id = f"u-recon-{scenario}"
    truth = {f: _secrets.generate(
        f, seed=_eng.stable_seed(seed, scenario, f))["value"]
        for f in fields}
    per = max(1, n // max(1, len(fields)))
    turns: list[dict] = []
    g = 0
    for f in fields:
        masks = queries.mask_schedule(truth[f], steps, complete=True)
        last: dict | None = None
        for i in range(per):
            if len(turns) >= n:
                break
            turn: dict | None = None
            if (last is not None and _eng._frac("resend", scenario, f, i)
                    < _eng.RATE["session_resend"]):
                turn = {**last, "metadata": dict(last["metadata"])}
            if turn is None:
                mask = masks[i % len(masks)]
                step = i % len(masks)
                carrier = carriers[(i // len(masks)) % len(carriers)]
                if i >= len(masks):
                    variants = queries.near_duplicates(
                        carrier, seed=_eng.stable_seed(seed, f, i))
                    carrier = variants[i % len(variants)]
                turn = {"prompt": f"{carrier} Ref: {mask}", "mask": mask,
                        "step": step, "field": f,
                        "metadata": {"scenario": scenario, "user_id": user_id,
                                     "field": f, "step": step}}
            turns.append(turn)
            last = turn
            g += 1
            if g % 6 == 0 and len(turns) < n:
                d = _eng.DISTRACTORS[(g // 6) % len(_eng.DISTRACTORS)]
                turns.append({"prompt": d, "mask": "", "step": 0, "field": "",
                              "metadata": {"scenario": scenario,
                                           "user_id": user_id, "field": "",
                                           "step": 0}})
                g += 1
    return {"user_id": user_id, "scenario": scenario, "truth": truth,
            "turns": turns[:n]}


def run_generic(scenario: str, fields: list[str], carriers: list[str],
                seed: int = 42, n: int = 48) -> dict:
    """Execute a generic scenario through the engine ingest path."""
    from ... import reconstruction as _eng
    session = generic_session(scenario, fields, carriers, seed=seed, n=n)
    uid, truth = session["user_id"], session["truth"]
    _eng.STATE.purge(uid)
    _eng.STATE.register_truth(uid, truth)
    for t in session["turns"]:
        _eng.STATE.ingest(t["prompt"], dict(t["metadata"]),
                           mask=t["mask"], step=t["step"])
    return {"user_id": uid, "scenario": scenario,
            "n_turns": len(session["turns"]),
            "report": _eng.build_report(_eng.STATE, uid)}
