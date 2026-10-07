"""Agentic forensic workflows on the local Qwen 3.8-27B (via Ollama).

Pipeline (all agents = same local model, different roles):

    scout ──► profiler (per service, threaded) ──► critic (per service) ──► reporter
    heuristics                                            LLM review      executive brief
    + traffic                                             gaps/risks      markdown

Every agent I/O is persisted under evidence/agentic/<run_id>/ so the
dashboard can show the full reasoning chain, not just the final report.
"""
import json
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import config, ollama_client
from . import infer as infer_mod
from . import security as security_mod
from . import security_agent

AGENT_DIR = os.path.join(config.EVIDENCE_DIR, "agentic")

SCOUT_SYSTEM = (
    "You are a forensic traffic scout. You read LLM-gateway telemetry summaries "
    "(which service called which model, how often, token volumes, cadence) and "
    "rank which services are worth a deep investigation. Be terse and concrete."
)

PROFILER_SYSTEM = (
    "You are a forensic software investigator. Given observed LLM prompt templates, "
    "instruction sentences and traffic stats from ONE unknown service, infer what "
    "codebase that service is running: its purpose, pipeline stages, input/output "
    "schema, and what product it is building. Ground every claim in the quoted "
    "evidence. Never invent repo names or file paths; mark guesses with confidence."
)

CRITIC_SYSTEM = (
    "You are a reconstruction critic. Given a forensic profile of a service plus its "
    "heuristic reconstruction plan, list concrete gaps: what the logs CANNOT prove, "
    "what completions/outputs are missing, and the smallest next observation that "
    "would close each gap. Short bullet list."
)

REPORTER_SYSTEM = (
    "You are an intelligence brief writer. Given per-service forensic profiles, write "
    "a tight executive brief: what each node in the mesh is building, shared topics "
    "across services, and the single most valuable reconstruction target. Markdown, "
    "under 40 lines."
)


def _compact_profile(service: str, profile: dict, max_tpl: int = 4,
                     max_ins: int = 6) -> str:
    p = profile
    lines = [
        f"service: {service}",
        f"requests: {p.get('requests')} tokens: {p.get('total_tokens')} "
        f"models: {p.get('models')} query_types: {p.get('query_types')}",
        f"heuristic guess: {p.get('project')} :: {p.get('pipeline_summary')}",
        f"heuristic pipeline: {' -> '.join(p.get('pipeline', []))}",
        f"schema hints: {p.get('schema_hints')}",
        "instructions:",
        *[f"  - {s[:200]}" for s in (p.get("instructions") or [])[:max_ins]],
        "templates:",
        *[f"  - (x{t.get('count')}) {(t.get('template') or '')[:280]}"
          for t in (p.get("fingerprint", {}).get("templates") or [])[:max_tpl]],
    ]
    return "\n".join(lines)


def scout(investigation: dict, model: str, num_predict: int) -> dict:
    rows = []
    for svc, p in investigation.get("services", {}).items():
        rows.append(f"- {svc}: {p['requests']} reqs, {p['total_tokens']} toks, "
                    f"models={list(p.get('models', {}))}, guess={p.get('project')}")
    out = ollama_client.ask_json(
        SCOUT_SYSTEM,
        "Rank these observed services for deep forensic investigation.",
        untrusted="\n".join(rows), untrusted_label="telemetry",
        model=model, num_predict=max(num_predict, 512))
    return {"agent": "scout", **out}


def profiler(service: str, profile: dict, model: str, num_predict: int) -> dict:
    compact = _compact_profile(service, profile)
    out = ollama_client.ask_json(
        PROFILER_SYSTEM,
        "Profile the service described in the untrusted data. Keys: project, "
        "what_building (2 sentences), pipeline (list of stage names), inputs, "
        "outputs, confidence (0-1), evidence_quotes (list, max 4 short).",
        untrusted=compact, untrusted_label=f"service={service}",
        model=model, num_predict=max(num_predict, 768))
    risk = security_mod.injection_risk(compact)
    res = {"agent": "profiler", "service": service, "injection_risk": risk}
    if risk:
        res["injection_findings"] = security_mod.scan_injection(compact, service)
    return {**res, **out}


def critic(service: str, profile: dict, profiler_out: dict,
           model: str, num_predict: int) -> dict:
    out = ollama_client.ask(
        CRITIC_SYSTEM,
        f"Critique the reconstruction of service {service}.",
        untrusted=(
            f"heuristic plan: {profile.get('pipeline_summary')} "
            f"pipe={' -> '.join(profile.get('pipeline', []))}\n"
            f"profiler said: {json.dumps(profiler_out.get('parsed', {}))[:1500]}"),
        untrusted_label=f"service={service}",
        model=model, num_predict=num_predict)
    return {"agent": "critic", "service": service, **out}


def reporter(profiler_outs: list[dict], heuristic: dict | None = None,
             model: str = "", num_predict: int = 512,
             security: dict | None = None) -> dict:
    heuristic = heuristic or {}
    digest = []
    for po in profiler_outs:
        d = po.get("parsed") or {}
        svc = po.get("service", "?")
        if d:
            digest.append(f"- {svc}: {json.dumps(d)[:700]}")
        else:
            # fallback: never feed the reporter empty {} — use raw + heuristic
            h = heuristic.get(svc, {})
            raw = (po.get("content") or "")[:500].replace("\n", " ")
            digest.append(f"- {svc} (heuristic: {h.get('project')}; "
                          f"llm-raw: {raw})")
    if security:
        totals = security.get("totals") or {}
        digest.append(f"- security: risk={security.get('risk_rating')} "
                      f"totals={totals} "
                      f"tracked_evidence={security.get('tracked_evidence', {}).get('count')}")
    instr = "Write the brief."
    if security:
        instr += (" Include a short '## Security posture' section: risk rating, "
                  "the top issues and their remediation.")
    out = ollama_client.ask(
        REPORTER_SYSTEM, instr,
        untrusted="\n".join(digest), untrusted_label="service-profiles",
        model=model, num_predict=num_predict + 256)
    return {"agent": "reporter", **out}


def _write(run_dir: str, name: str, payload: dict) -> None:
    with open(os.path.join(run_dir, name), "w") as f:
        json.dump(payload, f, indent=1, default=str)


def _log(run_id: str, actor: str, action: str, task_id: str = "",
         artifact: str = "", detail: str = "") -> None:
    """Ledger event that must never break the run (P7.28)."""
    try:
        from . import ledger as ledger_mod
        ledger_mod.append(run_id, actor, action, task_id=task_id,
                          artifact=artifact, detail=detail)
    except Exception:  # noqa: BLE001
        pass


def run_deep_investigation(rows: list[dict], model: str | None = None,
                           quick: bool = False,
                           only: list[str] | None = None,
                           max_workers: int = 4) -> dict:
    """Full agentic run. Returns manifest dict; artifacts land in AGENT_DIR/<run_id>/."""
    model = model or ollama_client.MODEL
    inv = infer_mod.investigate_all(rows)
    services = [s for s in inv["services"] if (not only or s in only)]
    if quick:
        services = sorted(services,
                          key=lambda s: -inv["services"][s]["requests"])[:3]
    np = 256 if quick else 512
    run_id = time.strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(AGENT_DIR, run_id)
    os.makedirs(run_dir, exist_ok=True)
    manifest: dict = {"run_id": run_id, "model": model, "quick": quick,
                      "services": services, "agents": {}, "errors": []}
    t0 = time.time()
    _log(run_id, "orchestrator", "run.start", detail=f"model={model} quick={quick}")

    # 1. scout (heuristic shortlist + LLM rank)
    try:
        manifest["agents"]["scout"] = scout(inv, model, num_predict=256)
    except Exception as e:  # noqa: BLE001 — one agent must not kill the run
        manifest["errors"].append(f"scout: {type(e).__name__}: {e}")
    _write(run_dir, "scout.json", manifest["agents"].get("scout", {}))
    _log(run_id, "scout", "task.complete", task_id=f"{run_id}-scout",
         artifact=os.path.join(run_dir, "scout.json"))

    # 2. profilers in parallel
    profs: dict[str, dict] = {}
    for s in services:
        _log(run_id, "orchestrator", "task.issued",
             task_id=f"{run_id}-profile-{s}", detail=f"service={s}")
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(profiler, s, inv["services"][s], model, np): s
                for s in services}
        for fut in as_completed(futs):
            s = futs[fut]
            try:
                profs[s] = fut.result()
            except Exception as e:  # noqa: BLE001
                manifest["errors"].append(f"profiler:{s}: {type(e).__name__}: {e}")
                profs[s] = {"agent": "profiler", "service": s, "error": str(e)}
            _write(run_dir, f"profiler.{s}.json", profs[s])
            _log(run_id, f"profiler:{s}", "task.complete",
                 task_id=f"{run_id}-profile-{s}",
                 artifact=os.path.join(run_dir, f"profiler.{s}.json"))
    manifest["agents"]["profilers"] = profs

    # 3. critics (skipped in quick mode)
    crits: dict[str, dict] = {}
    if not quick:
        for s in services:
            if "error" not in profs.get(s, {}):
                _log(run_id, "orchestrator", "task.issued",
                     task_id=f"{run_id}-critic-{s}", detail=f"service={s}")
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futs = {ex.submit(critic, s, inv["services"][s], profs[s], model, 256): s
                    for s in services if "error" not in profs[s]}
            for fut in as_completed(futs):
                s = futs[fut]
                try:
                    crits[s] = fut.result()
                except Exception as e:  # noqa: BLE001
                    manifest["errors"].append(f"critic:{s}: {type(e).__name__}: {e}")
                else:
                    _write(run_dir, f"critic.{s}.json", crits[s])
                    _log(run_id, f"critic:{s}", "task.complete",
                         task_id=f"{run_id}-critic-{s}",
                         artifact=os.path.join(run_dir, f"critic.{s}.json"))
    manifest["agents"]["critics"] = crits

    # 4. deterministic security scan (no LLM) — folded into the brief
    sec_report: dict = {}
    try:
        sec_report = security_agent.deterministic_report()
        manifest["security"] = {"risk_rating": sec_report.get("risk_rating"),
                                "totals": sec_report.get("totals"),
                                "n_findings": sec_report.get("n_findings")}
        _write(run_dir, "security.json", sec_report)
        _log(run_id, "sentinel", "task.complete", task_id=f"{run_id}-security",
             artifact=os.path.join(run_dir, "security.json"))
    except Exception as e:  # noqa: BLE001
        manifest["errors"].append(f"security: {type(e).__name__}: {e}")

    # 5. reporter
    try:
        ok_profs = [p for p in profs.values() if "error" not in p]
        manifest["agents"]["reporter"] = reporter(
            ok_profs,
            heuristic={s: {"project": inv["services"][s].get("project")}
                       for s in services},
            security=sec_report or None,
            model=model, num_predict=np)
    except Exception as e:  # noqa: BLE001
        manifest["errors"].append(f"reporter: {type(e).__name__}: {e}")
    _write(run_dir, "reporter.json", manifest["agents"].get("reporter", {}))
    _log(run_id, "reporter", "task.complete", task_id=f"{run_id}-reporter",
         artifact=os.path.join(run_dir, "reporter.json"))

    manifest["elapsed_s"] = round(time.time() - t0, 1)
    manifest["heuristic_investigation"] = {
        s: {"project": inv["services"][s].get("project"),
            "requests": inv["services"][s].get("requests"),
            # groundable source text for claims validation (P5.21):
            # evidence quotes must appear here (normalized substring).
            "evidence": {
                "templates": [(t.get("template") or "")[:400]
                              for t in (inv["services"][s].get("fingerprint", {})
                                        .get("templates") or [])[:4]],
                "instructions": [(i or "")[:300]
                                 for i in (inv["services"][s].get("instructions")
                                           or [])[:6]],
                "sample_heads": (inv["services"][s].get("sample_heads") or [])[:3],
            }}
        for s in services
    }
    _write(run_dir, "manifest.json", manifest)
    _log(run_id, "orchestrator", "run.complete",
         detail=f"errors={len(manifest['errors'])} elapsed_s={manifest['elapsed_s']}")

    # human-readable brief
    brief = ["# Agentic forensic brief", f"run: {run_id} model: {model}",
             f"elapsed: {manifest['elapsed_s']}s quick={quick}", ""]
    rep = (manifest["agents"].get("reporter") or {}).get("content", "")
    brief.append(rep or "_reporter produced no output_")
    if sec_report:
        brief += ["", "---", "", security_agent.render_markdown(sec_report)]
    with open(os.path.join(run_dir, "BRIEF.md"), "w") as f:
        f.write("\n".join(brief))
    return {"run_id": run_id, "run_dir": run_dir, **manifest}


def list_runs() -> list[dict]:
    if not os.path.isdir(AGENT_DIR):
        return []
    runs = []
    for rid in sorted(os.listdir(AGENT_DIR), reverse=True):
        mp = os.path.join(AGENT_DIR, rid, "manifest.json")
        if os.path.exists(mp):
            try:
                with open(mp) as f:
                    m = json.load(f)
                runs.append({"run_id": rid,
                             "model": m.get("model"),
                             "services": m.get("services", []),
                             "elapsed_s": m.get("elapsed_s"),
                             "errors": len(m.get("errors", []))})
            except Exception:  # noqa: BLE001
                runs.append({"run_id": rid, "error": "unreadable manifest"})
    return runs


def load_run(run_id: str) -> dict | None:
    mp = os.path.join(AGENT_DIR, run_id, "manifest.json")
    if not os.path.exists(mp):
        return None
    with open(mp) as f:
        manifest = json.load(f)
    brief_path = os.path.join(AGENT_DIR, run_id, "BRIEF.md")
    manifest["brief"] = (open(brief_path).read()
                         if os.path.exists(brief_path) else "")
    return manifest


# background-run registry so the dashboard can fire-and-forget.
# Disk-backed (swarm.register_run) — a restart no longer loses runs, and
# container workers observe the same state. No in-process _RUNS global.


def launch_background(rows_fn, model: str, quick: bool,
                      only: list[str] | None) -> str:
    from . import swarm as swarm_mod
    run_key = f"pending-{time.strftime('%Y%m%d_%H%M%S')}"
    swarm_mod.register_run(run_key, {"status": "running",
                                     "started": time.time()})

    def _work():
        try:
            res = run_deep_investigation(rows_fn(), model=model,
                                         quick=quick, only=only)
            swarm_mod.update_run(run_key, {"status": "done", **res})
        except Exception as e:  # noqa: BLE001
            swarm_mod.update_run(run_key, {"status": "error", "error": str(e)})

    threading.Thread(target=_work, daemon=True).start()
    return run_key


def background_status(key: str) -> dict:
    from . import swarm as swarm_mod
    return swarm_mod.get_run(key)
