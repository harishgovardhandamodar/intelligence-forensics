"""In-tab scenario runner + scenario catalogue (P8 trigger + diagrams).

`run_scenario` executes a client scenario *inside the server* (same builders
the `sim/run.py` client uses, same report shape it prints) so the Sim tab can
trigger experiments with one click instead of shelling out. `describe`
returns per-scenario metadata with a mermaid flowchart the tab renders —
what each scenario leaks, step by step.
"""
from __future__ import annotations

BUILDERS = {
    "chatbot_health": "sim.scenarios.chatbot_health",
    "chatbot_financial": "sim.scenarios.chatbot_financial",
    "coding_api_keys": "sim.scenarios.coding_api_keys",
    "coding_secrets": "sim.scenarios.coding_secrets",
}

META = {
    "chatbot_health": {
        "title": "Health chatbot",
        "blurb": "Repeated checkup questions; SSN and blood pressure surface "
                 "through progressive masked disclosure.",
        "fields": ["ssn", "bp"],
        "diagram": ("flowchart TB\n"
                    '    U["user u-health<br/>checkup questions"] --> Q1["q1: trends? (no secret)"]\n'
                    '    U --> Q2["q2: + BP 140/90"]\n'
                    '    U --> Q3["q3: + SSN ***-**-6789"]\n'
                    '    Q1 --> G["gateway: embed + store"]\n'
                    '    Q2 --> G\n    Q3 --> G\n'
                    '    G --> A["structure attack<br/>merge masks by shape"]\n'
                    '    A --> R["full SSN + BP recovered"]\n'),
    },
    "chatbot_financial": {
        "title": "Financial chatbot",
        "blurb": "Balance questions leaking account number and card PAN, "
                 "including spaced multi-token secrets.",
        "fields": ["account_number", "credit_card"],
        "diagram": ("flowchart TB\n"
                    '    U["user u-finance<br/>balance questions"] --> Q1["q1: balance? (no secret)"]\n'
                    '    U --> Q2["q2: + acct 8611-****-****"]\n'
                    '    U --> Q3["q3: + card 4242 **** **** ****"]\n'
                    '    Q1 --> G["gateway: embed + store"]\n'
                    '    Q2 --> G\n    Q3 --> G\n'
                    '    G --> A["structure attack<br/>spaced spans stay whole"]\n'
                    '    A --> R["account + PAN recovered"]\n'),
    },
    "coding_api_keys": {
        "title": "Coding assistant (API keys)",
        "blurb": "Integration questions pasting API and AWS keys. Styles: "
                 "one-off (single paste), regular (progressive), vibe (full "
                 "secret in turn one through sheer repetition).",
        "fields": ["api_key", "aws_key"],
        "diagram": ("flowchart TB\n"
                    '    O["one-off: 3 turns<br/>direct read, no assembly"] --> L["log holds bare secret"]\n'
                    '    R["regular: masked steps<br/>+ paraphrase + noise"] --> A["structure attack"]\n'
                    '    V["vibe: full paste, turn 1<br/>sloppy carriers"] --> L\n'
                    '    A --> F["assembly from fragments"]\n'
                    '    L --> F\n'),
    },
    "coding_secrets": {
        "title": "Coding assistant (secrets)",
        "blurb": "DB passwords and second-service keys in debug output. Runs "
                 "the partial regime: the final slot is never disclosed, so "
                 "the curve plateaus below 1.0.",
        "fields": ["db_password", "api_key"],
        "diagram": ("flowchart TB\n"
                    '    U["user u-secrets<br/>debug output"] --> Q1["q1: ***partial***"]\n'
                    '    U --> Q2["q2: ***partial***"]\n'
                    '    U --> Q3["q3: still masked<br/>last slot held"]\n'
                    '    Q1 --> G["gateway: embed + store"]\n'
                    '    Q2 --> G\n    Q3 --> G\n'
                    '    G --> A["structure attack"]\n'
                    '    A --> P["plateau ~0.95<br/>never completes"]\n'),
    },
}


def available() -> list[str]:
    return list(BUILDERS)


def describe() -> list[dict]:
    """Catalogue entries for the Sim tab (no secrets, field names only)."""
    return [{"id": k, **{kk: v for kk, v in m.items() if kk != "diagram"},
             "diagram": m["diagram"]} for k, m in META.items()]


def _builder(name: str):
    import importlib
    if name not in BUILDERS:
        raise ValueError(f"unknown scenario: {name!r}")
    mod = importlib.import_module(BUILDERS[name])
    return mod.build


def _log(run_id: str, actor: str, action: str, task_id: str = "",
         artifact: str = "", detail: str = "") -> None:
    """Ledger event that must never break a sim run."""
    try:
        from .. import ledger as ledger_mod
        ledger_mod.append(run_id, actor, action, task_id=task_id,
                          artifact=artifact, detail=detail)
    except Exception:  # noqa: BLE001
        pass


def run_scenario(name: str, n: int = 60, seed: int = 42,
                 threshold: float = 0.6, style: str = "regular",
                 dlp_mode: str = "off", out_dir: str | None = None,
                 run_id: str | None = None,
                 log_complete: bool = True) -> dict:
    """Execute one scenario server-side; same result shape as the client."""
    import json
    import os
    import time
    from . import state as sim_state
    st = sim_state.STATE
    if run_id is None:
        run_id = f"sim-{time.strftime('%Y%m%d_%H%M%S')}"
    _log(run_id, "orchestrator", "run.start",
         detail=f"scenario={name} n={n} seed={seed} style={style} dlp={dlp_mode}")
    sc = _builder(name)(seed=seed, n=n, style=style)
    user_id, truth = sc["user_id"], sc["truth"]
    st.reset()
    st.set_policy(dlp_mode)
    st.register_truth(user_id, truth)
    for i, t in enumerate(sc["turns"]):
        st.gateway.process_query(t["prompt"], t["metadata"], mask=t["mask"],
                                 step=t["step"], dlp=st.policy)
    from . import attacks as sim_attacks
    texts, vecs = st.store.texts_vectors(
        filtr={"user_id": user_id} if user_id else None)
    attack = sim_attacks.progressive_attack(texts, vecs, threshold)
    from .reporting import build_report
    report = build_report(st, user_id)
    probes = {}
    for field, value in truth.items():
        hit = sim_attacks.membership_candidate(
            value, texts, st.embedder.embed_one)
        miss = sim_attacks.membership_candidate(
            "never-logged-random-value-zzz-999", texts, st.embedder.embed_one)
        probes[field] = {"true_score": hit["max_score"],
                         "fresh_score": miss["max_score"],
                         "likely_member": hit["likely_member"]}
    result = {"scenario": name, "user_id": user_id,
              "n_turns": len(sc["turns"]), "style": sc.get("style", "regular"),
              "run_id": run_id, "truth": truth,
              "attack": {"n_clusters": attack["n_clusters"],
                         "mean_cohesion": attack["mean_cohesion"]},
              "report": report, "membership": probes}
    rdir = out_dir or os.path.join(_reports_root(), run_id)
    os.makedirs(rdir, exist_ok=True)
    rpath = os.path.join(rdir, f"{name}.json")
    with open(rpath, "w") as f:
        json.dump(result, f, indent=1)
    _log(run_id, f"sim:{name}", "task.complete", task_id=f"{run_id}-{name}",
         artifact=rpath,
         detail=f"recovered={report['recovered']}/{report['n_fields']} "
                f"mean={report['mean_accuracy']}")
    if out_dir is None and log_complete:
        _log(run_id, "orchestrator", "run.complete",
             detail=f"scenario={name} user={user_id}")
    return result


def _reports_root() -> str:
    import os
    from .. import config
    return os.path.join(config.EVIDENCE_DIR, "sim-reports")
