"""Visualization payloads for AGENTIC reconstructions.

Turns stored agent JSONs (evidence/agentic/<run_id>/*.json) into
chart-ready structures: pipeline DAG, per-agent costs, per-service
confidence + heuristic-vs-LLM agreement, critic gaps, cross-run trends.
No LLM calls — pure reshaping of recorded evidence.
"""
import json
import os
import re

from . import agents as ag

_STOP = {"the", "a", "an", "of", "for", "and", "to", "in", "on", "with",
        "service", "app", "system", "engine", "tool", "platform"}


def _tokens(s: str) -> set[str]:
    return {t for t in re.sub(r"[^a-z0-9 ]", " ", (s or "").lower()).split()
            if len(t) > 2 and t not in _STOP}


def agreement(heuristic: str, llm: str) -> str:
    """match / partial / disagree / unknown between heuristic label and LLM label."""
    if not heuristic or not llm:
        return "unknown"
    h, l = heuristic.lower().strip(), llm.lower().strip()
    if h == l or h in l or l in h:
        return "match" if h == l else "partial"
    if len(_tokens(h) & _tokens(l)) >= 2:
        return "partial"
    return "disagree"


def _gaps(content: str, limit: int = 6) -> list[str]:
    out = []
    for line in (content or "").split("\n"):
        s = line.strip()
        if re.match(r"^([-*•]\s+|\d+[.)\]]\s+|#{1,3}\s+)", s):
            s = re.sub(r"^([-*•]\s+|\d+[.)\]]\s+|#{1,3}\s+)", "", s).strip()
            if len(s) > 15:
                out.append(s[:180])
        if len(out) >= limit:
            break
    return out


def _agent_file(run_dir: str, name: str) -> dict:
    p = os.path.join(run_dir, name)
    if not os.path.exists(p):
        return {}
    try:
        with open(p) as f:
            return json.load(f)
    except Exception:  # noqa: BLE001
        return {}


def build_run_graph(run_id: str) -> dict | None:
    run_dir = os.path.join(ag.AGENT_DIR, run_id)
    manifest = ag.load_run(run_id)
    if not manifest:
        return None
    heur = manifest.get("heuristic_investigation") or {}
    agents = manifest.get("agents") or {}
    nodes, edges = [], []
    tot_pt = tot_ct = 0.0
    ok = err = 0

    def add(nid: str, layer: str, label: str, payload: dict):
        nonlocal tot_pt, tot_ct, ok, err
        status = "error" if payload.get("error") else ("ok" if payload.get("content") else "empty")
        ok, err = ok + (status == "ok"), err + (status == "error")
        tot_pt += payload.get("prompt_tokens", 0) or 0
        tot_ct += payload.get("completion_tokens", 0) or 0
        ms = payload.get("ms", 0) or 0
        toks = (payload.get("prompt_tokens", 0) or 0) + (payload.get("completion_tokens", 0) or 0)
        nodes.append({"id": nid, "layer": layer, "label": label,
                      "sub": f"{ms / 1000:.1f}s · {toks} tok",
                      "ms": ms,
                      "prompt_tokens": payload.get("prompt_tokens", 0) or 0,
                      "completion_tokens": payload.get("completion_tokens", 0) or 0,
                      "status": status})

    scout = agents.get("scout") or {}
    if scout:
        add("scout", "scout", "scout", scout)
    services = manifest.get("services", [])
    for s in services:
        pid = f"profiler:{s}"
        add(pid, "profiler", f"profiler:{s[:18]}",
            (agents.get("profilers") or {}).get(s, {}))
        if scout:
            edges.append({"from": "scout", "to": pid})
    critics = agents.get("critics") or {}
    for s, c in critics.items():
        cid = f"critic:{s}"
        add(cid, "critic", f"critic:{s[:18]}", c)
        edges.append({"from": f"profiler:{s}", "to": cid})
    if agents.get("reporter"):
        add("reporter", "reporter", "reporter", agents["reporter"])
        for s in services:
            edges.append({"from": f"profiler:{s}", "to": "reporter"})

    svc_rows = []
    for s in services:
        prof = (agents.get("profilers") or {}).get(s, {})
        parsed = prof.get("parsed") or {}
        hproj = (heur.get(s) or {}).get("project", "")
        lproj = parsed.get("project", "")
        what = (parsed.get("what_building") or "")[:280]
        crit = critics.get(s, {})
        svc_rows.append({
            "service": s,
            "heuristic_project": hproj,
            "llm_project": lproj,
            "agreement": agreement(hproj, f"{lproj} {what}"),
            "confidence": parsed.get("confidence"),
            "what_building": what,
            "pipeline_llm": parsed.get("pipeline") or [],
            "evidence_quotes": (parsed.get("evidence_quotes") or [])[:4],
            "critic_gaps": _gaps(crit.get("content", "")),
            "ms": prof.get("ms", 0) or 0,
        })

    return {"run_id": run_id, "model": manifest.get("model"),
            "quick": manifest.get("quick"), "elapsed_s": manifest.get("elapsed_s"),
            "errors": manifest.get("errors", []),
            "totals": {"prompt_tokens": int(tot_pt), "completion_tokens": int(tot_ct),
                       "agents_ok": ok, "agents_error": err,
                       "local_cost_usd": 0.0},
            "nodes": nodes, "edges": edges, "services": svc_rows,
            "reporter_text": (agents.get("reporter") or {}).get("content", "")}


def compare_runs(limit: int = 5) -> dict:
    """Confidence per service across the last N runs (cross-run trend)."""
    runs = ag.list_runs()[:limit]
    services: list[str] = []
    for r in runs:
        g = build_run_graph(r["run_id"])
        for s in (g or {}).get("services", []):
            if s["service"] not in services:
                services.append(s["service"])
    cols = []
    for r in runs:
        g = build_run_graph(r["run_id"])
        m = ag.load_run(r["run_id"]) or {}
        conf = {s["service"]: s["confidence"] for s in (g or {}).get("services", [])}
        cols.append({"run_id": r["run_id"], "quick": m.get("quick"),
                     "elapsed_s": m.get("elapsed_s"),
                     "confidence": {s: conf.get(s) for s in services}})
    return {"runs": [c["run_id"] for c in cols], "services": services, "cols": cols}
