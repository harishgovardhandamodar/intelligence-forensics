"""Rogue-agent swarm engine — deterministic, dependency-free.

`run_scenario` turns a catalogue spec into a run: it builds the swarm, feeds
every agent action through the modeled OpenShell policy engine, records the
hash-chained audit trail, runs the layered detector, and persists the full
report under `evidence/rogue-reports/<run_id>/`.

Nothing is executed. `net.egress`, `proc.spawn` and `cred.use` are *decided*,
never performed — this is a model of governance, not a sandbox escape kit.
"""
from __future__ import annotations

import json
import os
import time

from . import behaviors
from . import detect as detect_mod
from . import scenarios as scen_mod
from .openshell import PolicyEngine, Rule


def _log(run_id: str, actor: str, action: str, task_id: str = "",
         artifact: str = "", detail: str = "") -> None:
    """Ledger event that must never break a run."""
    try:
        from ... import ledger as ledger_mod
        ledger_mod.append(run_id, actor, action, task_id=task_id,
                          artifact=artifact, detail=detail)
    except Exception:  # noqa: BLE001
        pass


def _apply_updates(engine: PolicyEngine, spec: dict, step: int) -> list[dict]:
    applied = []
    for upd in spec.get("policy_updates") or []:
        if upd.get("step") == step:
            rule = Rule(upd["id"], upd["kind"], upd["match"], upd["effect"],
                        upd["layer"], upd["reason"])
            entry = engine.update_policy(rule, actor="operator")
            applied.append({"id": rule.id, "at_step": step,
                            "audit_id": entry.get("audit_id")})
    return applied


def run_scenario(scenario_id: str, seed: int = 42, n: int | None = None,
                 run_id: str | None = None, mode: str | None = None,
                 persist: bool = True) -> dict:
    spec = scen_mod.get(scenario_id)
    total = int(n) if n else spec["steps"]
    total = max(2, min(24, total))
    det_mode = mode or spec["detector"]
    if run_id is None:
        run_id = f"rogue-{time.strftime('%Y%m%d_%H%M%S')}-{scenario_id}"

    _log(run_id, "openshell", "run.start",
         detail=f"scenario={scenario_id} agents={len(spec['agents'])} "
                f"steps={total} mode={det_mode}")
    engine = PolicyEngine(name=f"openshell:{scenario_id}")
    policy_updates: list[dict] = []
    events: list[dict] = []
    for step in range(total):
        for applied in _apply_updates(engine, spec, step):
            policy_updates.append(applied)
        for agent in spec["agents"]:
            for action in behaviors.actions_for(agent, step, total):
                decision = engine.evaluate(agent["id"], action)
                events.append({
                    **decision,
                    "pollute": bool(action.get("pollute")),
                    "artifact": action.get("artifact", ""),
                    "consume": action.get("consume", ""),
                    "fragment": action.get("fragment", ""),
                    "role": action.get("role", agent.get("role", "worker")),
                })

    agent_ids = [a["id"] for a in spec["agents"]]
    detection = detect_mod.detect(events, agent_ids, spec["expect"], det_mode)
    audit = engine.audit()
    integrity = engine.verify()

    notable = _notable(events)
    result = {
        "run_id": run_id, "scenario": scenario_id, "seed": seed,
        "title": spec["title"], "category": spec["category"],
        "blurb": spec["blurb"], "family": spec["family"],
        "steps": total, "stresses": spec["stresses"],
        "remediation": spec["remediation"],
        "mode": det_mode,
        "agents": [{"id": a["id"], "role": a["role"],
                    "disposition": a["disposition"],
                    "objective": a["objective"], "cell": a["cell"],
                    "trigger": a["trigger"]} for a in spec["agents"]],
        "expect": spec["expect"],
        "policy": engine.rules_snapshot(),
        "policy_updates": policy_updates,
        "audit": audit,
        "audit_verify": integrity,
        "events": len(events),
        "summary": _summary(events, audit),
        "detection": detection,
        "timeline": notable,
        "reports_root": _reports_root() if persist else "",
    }
    if persist:
        rdir = os.path.join(_reports_root(), run_id)
        os.makedirs(rdir, exist_ok=True)
        rpath = os.path.join(rdir, f"{scenario_id}.json")
        with open(rpath, "w") as f:
            json.dump(result, f, indent=1)
        _log(run_id, f"rogue:{scenario_id}", "task.complete",
             task_id=f"{run_id}-{scenario_id}", artifact=rpath,
             detail=f"verdicts={len(detection['verdicts'])} "
                    f"clusters={len(detection['clusters'])} "
                    f"audit_ok={integrity['ok']}")
        _log(run_id, "openshell", "run.complete",
             detail=f"scenario={scenario_id}")
        result["reports_root"] = rdir
    return result


def _summary(events: list[dict], audit: list[dict]) -> dict:
    denied = [e for e in events if e.get("effect") == "deny"]
    by_layer: dict[str, int] = {}
    for e in events:
        by_layer[e.get("layer", "?")] = by_layer.get(e.get("layer", "?"), 0) + 1
    deny_layer: dict[str, int] = {}
    for e in denied:
        deny_layer[e.get("layer", "?")] = deny_layer.get(e.get("layer", "?"), 0) + 1
    return {"events": len(events), "allowed": len(events) - len(denied),
            "denied": len(denied), "audit_entries": len(audit),
            "by_layer": by_layer, "denied_by_layer": deny_layer}


def _notable(events: list[dict], limit: int = 120) -> list[dict]:
    """Denied decisions + the allowed acts that carried a covert signal."""
    out = []
    for e in events:
        keep = e.get("effect") == "deny"
        if not keep and e.get("action") == "net.egress":
            payload = e.get("payload_head") or ""
            keep = len(payload) >= 12 and detect_mod.shannon(payload) >= 3.5
        if not keep and (e.get("pollute") or e.get("channel")):
            keep = True
        if keep:
            out.append({
                "seq": e.get("seq"), "step": e.get("step"),
                "agent": e.get("agent"), "action": e.get("action"),
                "target": e.get("target"), "effect": e.get("effect"),
                "rule_id": e.get("rule_id"), "layer": e.get("layer"),
                "reason": e.get("reason"), "audit_id": e.get("audit_id"),
            })
    return out[:limit]


# --------------------------------------------------------------------------- #
# Persistence                                                                 #
# --------------------------------------------------------------------------- #
def _reports_root() -> str:
    from ... import config
    return os.path.join(config.EVIDENCE_DIR, "rogue-reports")


def reports_root() -> str:
    return _reports_root()


def list_runs() -> list[str]:
    root = _reports_root()
    try:
        return sorted((d for d in os.listdir(root)
                       if os.path.isdir(os.path.join(root, d))), reverse=True)
    except OSError:
        return []


def load_run(run_id: str) -> dict:
    rdir = os.path.join(_reports_root(), run_id)
    if not os.path.isdir(rdir):
        raise FileNotFoundError(run_id)
    files = [fn for fn in os.listdir(rdir) if fn.endswith(".json")]
    files.sort(key=lambda fn: os.path.getmtime(os.path.join(rdir, fn)),
               reverse=True)
    out: dict = {}
    for fn in files:
        with open(os.path.join(rdir, fn)) as f:
            out[os.path.splitext(fn)[0]] = json.load(f)
    return out


def reset() -> dict:
    """Runs are persisted evidence; there is no shared in-memory state."""
    return {"ok": True, "cleared": False,
            "note": "rogue runs are persisted evidence; nothing to clear"}
