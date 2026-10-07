"""Unified investigation report (P4.16 / P4.17).

One artifact that folds together everything the system knows, with a
provenance block an analyst can trust:

    heuristic inference  (infer.investigate_all)
  + quality scores       (score.score_profile)
  + agentic findings     (agents run manifest / run_viz graph)
  + critic gaps          (carried in the agentic graph)
  + security findings    (security_agent.deterministic_report)
  + trust boundaries     (trust.audit)
  + per-service risk     (risk.service_risk)
  + provenance           (source DB path, SHA-256, size, mtime, model, host)

Reports are versioned on disk (`evidence/reports/<id>/`) and each new run
diffs itself against the previous one, so "what changed since last time" is a
first-class part of the report rather than a manual chore.
"""
from __future__ import annotations

import glob
import hashlib
import html
import json
import os
import platform
import socket
import time

from . import config, infer, risk as risk_mod, score as score_mod
from . import security_agent, trust

REPORT_DIR = os.path.join(config.EVIDENCE_DIR, "reports")
INDEX = "index.json"


def _sha256(path: str) -> str:
    h = hashlib.sha256()
    try:
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return ""


def newest_db() -> str | None:
    cands = sorted(glob.glob(os.path.join(config.EVIDENCE_DIR, "fox_services_*.db")))
    return cands[-1] if cands else None


def provenance(db_path: str | None, model: str = "", quick: bool = False,
               run_id: str | None = None) -> dict:
    p: dict = {"generated_at": time.time(), "generated_at_iso":
               time.strftime("%Y-%m-%d %H:%M:%S"),
               "host": socket.gethostname(), "platform": platform.platform(),
               "model": model, "quick": quick, "run_id": run_id or ""}
    if db_path and os.path.exists(db_path):
        st = os.stat(db_path)
        p.update({"db_path": os.path.abspath(db_path), "db_sha256": _sha256(db_path),
                  "db_bytes": st.st_size, "db_mtime": time.strftime(
                      "%Y-%m-%d %H:%M:%S", time.localtime(st.st_mtime))})
    else:
        p.update({"db_path": "", "db_sha256": "", "db_bytes": 0, "db_mtime": ""})
    return p


def _agentic(run_id: str | None) -> dict | None:
    try:
        from . import run_viz
    except Exception:  # noqa: BLE001
        return None
    rid = run_id
    if not rid:
        try:
            runs = __import__("iforensics.agents", fromlist=["agents"]).list_runs()
            rid = runs[0]["run_id"] if runs else None
        except Exception:  # noqa: BLE001
            rid = None
    if not rid:
        return None
    try:
        return run_viz.build_run_graph(rid)
    except Exception:  # noqa: BLE001
        return None


def assemble(rows: list[dict] | None = None, db_path: str | None = None,
             run_id: str | None = None, model: str = "", quick: bool = False,
             with_security: bool = True) -> dict:
    """Collect every analysis surface into one serializable bundle."""
    if db_path is None:
        db_path = newest_db()
    if rows is None:
        from . import store
        rows = store.load_requests(db_path) if db_path and os.path.exists(db_path) else []

    inv = infer.investigate_all(rows) if rows else {"n_services": 0, "n_requests": 0,
                                                    "services": {}}
    services = []
    for svc, p in inv.get("services", {}).items():
        sc = score_mod.score_profile(p)
        services.append({
            "service": svc, "project": p.get("project", ""),
            "requests": p.get("requests", 0), "total_tokens": p.get("total_tokens", 0),
            "models": list((p.get("models") or {}).keys()),
            "pipeline": p.get("pipeline", []),
            "score": sc.get("score"), "grade": sc.get("grade"),
        })

    ag = _agentic(run_id)
    bundle: dict = {
        "provenance": provenance(db_path, model=model, quick=quick,
                                 run_id=run_id or (ag or {}).get("run_id")),
        "heuristic": {"n_services": inv.get("n_services", 0),
                      "n_requests": inv.get("n_requests", 0)},
        "services": services,
        "agentic": ag,
        "security": {},
        "trust": {},
        "risk": {},
        "diff": None,
    }
    if with_security:
        try:
            bundle["security"] = security_agent.deterministic_report()
        except Exception as e:  # noqa: BLE001
            bundle["security"] = {"error": f"{type(e).__name__}: {e}"}
    try:
        bundle["trust"] = trust.audit()
    except Exception as e:  # noqa: BLE001
        bundle["trust"] = {"error": f"{type(e).__name__}: {e}"}
    try:
        bundle["risk"] = risk_mod.service_risk(rows)
    except Exception as e:  # noqa: BLE001
        bundle["risk"] = {"error": f"{type(e).__name__}: {e}"}
    return bundle


# ---------------------------------------------------------------- diffing ---

def _svc_map(bundle: dict) -> dict:
    return {s["service"]: s for s in bundle.get("services", [])}


def compute_diff(cur: dict, prev: dict | None) -> dict:
    """Human-scale changes between two bundles (new run vs previous)."""
    if not prev:
        return {"first_run": True}
    diff: dict = {"first_run": False,
                  "db_changed": cur.get("provenance", {}).get("db_sha256")
                  != prev.get("provenance", {}).get("db_sha256")}
    a, b = _svc_map(cur), _svc_map(prev)
    diff["services_added"] = sorted(set(a) - set(b))
    diff["services_removed"] = sorted(set(b) - set(a))
    score_changes = []
    for svc in sorted(set(a) & set(b)):
        if a[svc].get("score") != b[svc].get("score") or a[svc].get("grade") != b[svc].get("grade"):
            score_changes.append({"service": svc, "from": b[svc].get("score"),
                                  "to": a[svc].get("score"),
                                  "from_grade": b[svc].get("grade"),
                                  "to_grade": a[svc].get("grade")})
    diff["score_changes"] = score_changes

    def _tot(b, k):
        return ((b.get("security") or {}).get("totals") or {}).get(k, 0)
    diff["security"] = {"observed": {k: _tot(cur, k) for k in ("critical", "high", "medium", "low")},
                        "previous": {k: _tot(prev, k) for k in ("critical", "high", "medium", "low")}}
    diff["risk_band_changes"] = _band_changes(cur, prev)
    diff["trust_changes"] = _trust_changes(cur, prev)
    return diff


def _band_changes(cur, prev):
    a = {s["service"]: s.get("band") for s in (cur.get("risk") or {}).get("services", [])}
    b = {s["service"]: s.get("band") for s in (prev.get("risk") or {}).get("services", [])}
    return [{"service": s, "from": b[s], "to": a[s]}
            for s in sorted(set(a) & set(b)) if a[s] != b[s]]


def _trust_changes(cur, prev):
    a = {r["rule"]: r.get("status") for r in (cur.get("trust") or {}).get("rules", [])}
    b = {r["rule"]: r.get("status") for r in (prev.get("trust") or {}).get("rules", [])}
    return [{"rule": r, "from": b.get(r), "to": a.get(r)}
            for r in sorted(set(a) | set(b)) if a.get(r) != b.get(r)]


# --------------------------------------------------------------- persist ---

def _index_path(out_dir: str) -> str:
    return os.path.join(out_dir, INDEX)


def load_index(out_dir: str | None = None) -> list[dict]:
    out = out_dir or REPORT_DIR
    try:
        with open(os.path.join(out, INDEX)) as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except (OSError, ValueError):
        return []


def load_previous(out_dir: str | None = None) -> dict | None:
    """The most recent persisted bundle, if any."""
    for entry in reversed(load_previous_index(out_dir)):
        try:
            with open(entry["json"]) as f:
                return json.load(f)
        except (OSError, ValueError, KeyError):
            continue
    return None


def load_previous_index(out_dir: str | None = None) -> list[dict]:
    out = out_dir or REPORT_DIR
    entries = load_index(out)
    return [e for e in entries if e.get("json") and os.path.exists(e["json"])]


def persist(bundle: dict, out_dir: str | None = None, report_id: str | None = None) -> dict:
    out = out_dir or REPORT_DIR
    rid = report_id or time.strftime("%Y%m%d_%H%M%S")
    dest = os.path.join(out, rid)
    n = 2
    while os.path.exists(dest):  # two runs in the same second
        rid = f"{report_id or time.strftime('%Y%m%d_%H%M%S')}-{n}"
        dest = os.path.join(out, rid)
        n += 1
    os.makedirs(dest, exist_ok=True)
    md = render_markdown(bundle)
    html_text = render_html(bundle)
    jpath = os.path.join(dest, "report.json")
    mpath = os.path.join(dest, "report.md")
    hpath = os.path.join(dest, "report.html")
    with open(mpath, "w", encoding="utf-8") as f:
        f.write(md)
    with open(hpath, "w", encoding="utf-8") as f:
        f.write(html_text)
    with open(jpath, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=1, default=str)

    entry = {"id": rid, "generated_at": bundle.get("provenance", {}).get("generated_at"),
             "db_sha256": bundle.get("provenance", {}).get("db_sha256"),
             "risk": (bundle.get("security") or {}).get("risk_rating"),
             "n_findings": (bundle.get("security") or {}).get("n_findings"),
             "n_services": len(bundle.get("services", [])),
             "markdown": mpath, "html": hpath, "json": jpath}
    index = load_index(out)
    index = [e for e in index if e.get("id") != rid] + [entry]
    with open(os.path.join(out, INDEX), "w", encoding="utf-8") as f:
        json.dump(index, f, indent=1, default=str)
    return {"id": rid, "dir": dest, "markdown": mpath, "html": hpath,
            "json": jpath, "entry": entry}


def run_report(rows: list[dict] | None = None, db_path: str | None = None,
               run_id: str | None = None, model: str = "", out_dir: str | None = None,
               with_security: bool = True) -> dict:
    """Assemble + diff-against-previous + persist. The one call the UI/CLI makes."""
    prev = load_previous(out_dir)
    bundle = assemble(rows=rows, db_path=db_path, run_id=run_id, model=model,
                      with_security=with_security)
    bundle["diff"] = compute_diff(bundle, prev)
    paths = persist(bundle, out_dir=out_dir)
    return {"bundle": bundle, "paths": paths}


# ------------------------------------------------------------- rendering ---


def render_markdown(bundle: dict) -> str:
    p = bundle.get("provenance", {})
    L: list[str] = ["# Intelligence Forensics — unified report", ""]
    L += ["## Provenance", "",
          "| field | value |", "|---|---|",
          f"| generated | {p.get('generated_at_iso')} |",
          f"| host | {p.get('host')} ({p.get('platform')}) |",
          f"| source DB | `{p.get('db_path')}` |",
          f"| DB SHA-256 | `{p.get('db_sha256')}` |",
          f"| DB size | {p.get('db_bytes')} bytes, mtime {p.get('db_mtime')} |",
          f"| model | {p.get('model') or '(none)'} |",
          f"| agent run | {p.get('run_id') or '(none)'} |",
          f"| requests / services | {bundle.get('heuristic', {}).get('n_requests')} / "
          f"{p.get('n_services') or bundle.get('heuristic', {}).get('n_services')} |", ""]

    d = bundle.get("diff") or {}
    if p and bundle.get("diff"):
        L += ["## Changes since last run", ""]
        if bundle["diff"].get("first_run"):
            L.append("_First run — no previous version to diff._")
        else:
            L.append(f"- source DB changed: **{bundle['diff'].get('db_changed')}**")
            for k in ("services_added", "services_removed"):
                if bundle["diff"].get(k):
                    L.append(f"- {k.replace('_', ' ')}: {', '.join(bundle['diff'][k])}")
            for c in bundle["diff"].get("score_changes", []):
                L.append(f"- score {c['service']}: {c['from']} -> {c['to']} "
                         f"({c['from_grade']} -> {c['to_grade']})")
            for c in bundle["diff"].get("risk_band_changes", []):
                L.append(f"- risk {c['service']}: {c['from']} -> {c['to']}")
            for c in bundle["diff"].get("trust_changes", []):
                L.append(f"- trust {c['rule']}: {c['from']} -> {c['to']}")
            if not any((bundle.get("diff", {}).get(k) for k in
                        ("services_added", "services_removed", "score_changes",
                         "risk_band_changes", "trust_changes"))):
                L.append("- no material change since the previous run")
        L.append("")

    L += ["## Services", "",
          "| service | project | reqs | tokens | score | grade |",
          "|---|---|---|---|---|---|"]
    for s in bundle.get("services", []):
        L.append(f"| {s['service']} | {s.get('project','')} | {s.get('requests')} | "
                 f"{s.get('total_tokens')} | {s.get('score')} | {s.get('grade')} |")
    L.append("")

    sec = bundle.get("security") or {}
    if sec and "error" not in sec:
        tot = sec.get("totals") or {}
        L += ["## Security posture", "",
              f"Risk rating: **{sec.get('risk_rating')}** "
              f"({sec.get('n_findings')} findings; "
              + ", ".join(f"{k}={v}" for k, v in tot.items()) + ")", ""]
        for group, title in (("secrets", "Secret / PII survivors"),
                             ("injections", "Prompt-injection attempts"),
                             ("permissions", "Over-permissive files"),
                             ("exposure", "Dashboard exposure")):
            rows = sec.get(group) or []
            if not rows:
                continue
            L += [f"### {title}", ""]
            for f in rows[:20]:
                loc = f.get("source", "")
                if f.get("line"):
                    loc += f":{f['line']}"
                L.append(f"- **{f.get('severity')}** {f.get('kind')} — {loc} "
                         f"→ {f.get('remediation','')}")
            L.append("")

    tr = bundle.get("trust") or {}
    if tr.get("rules"):
        L += ["## Trust boundaries", "",
              "| rule | status | severity | detail |", "|---|---|---|---|"]
        for r in tr["rules"]:
            L.append(f"| {r['rule']} | {r['status']} | {r['severity']} | {r['detail']} |")
        L.append(f"\n_{tr.get('summary')}_")
        L.append("")

    rk = bundle.get("risk") or {}
    if rk.get("services"):
        L += ["## Inflow risk by service", "",
              "| service | band | score | prompts | PII | injections | reuse |",
              "|---|---|---|---|---|---|---|"]
        for s in rk["services"]:
            g = s.get("signals") or {}
            L.append(f"| {s['service']} | {s['band']} | {s['score']} | {s['n']} | "
                     f"{g.get('pii',0)} | {g.get('injection',0)} | "
                     f"{g.get('cross_service_reuse',0)} |")
        L.append("")

    ag = bundle.get("agentic")
    if ag:
        L += ["## Agentic deep investigation", "",
              f"run `{ag.get('run_id')}` model={ag.get('model')} "
              f"elapsed={ag.get('elapsed_s')}s "
              f"agents_ok={ag.get('totals',{}).get('agents_ok')}", ""]
        for s in ag.get("services", []):
            L.append(f"### {s['service']}")
            L.append(f"- heuristic: {s.get('heuristic_project')}")
            L.append(f"- LLM: {s.get('llm_project')} (confidence {s.get('confidence')})")
            L.append(f"- agreement: {s.get('agreement')}")
            for g in (s.get("critic_gaps") or [])[:4]:
                L.append(f"- gap: {g}")
            L.append("")
        if ag.get("reporter_text"):
            L += ["### Reporter brief", "", ag["reporter_text"], ""]

    L += ["---",
          "_Caveat: fox telemetry stores truncated, secret-redacted, PII-masked prompt "
          "heads; completions are not logged. Reconstructions recover templates and "
          "pipeline, not exact source._"]
    return "\n".join(L)


def _e(v) -> str:
    return html.escape(str(v if v is not None else ""))


def _table(headers, rows, raw_cols=frozenset()) -> str:
    th = "".join(f"<th>{_e(h)}</th>" for h in headers)
    body = ""
    for r in rows:
        body += "<tr>" + "".join(
            f"<td>{c if i in raw_cols else _e(c)}</td>" for i, c in enumerate(r)) + "</tr>"
    return f"<table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table>"


_CSS = """body{font:14px/1.5 system-ui,sans-serif;background:#0a0e14;color:#e6edf3;margin:0;padding:24px}
h1,h2,h3{color:#79c0ff}table{border-collapse:collapse;width:100%;margin:8px 0}
th,td{border:1px solid #30363d;padding:4px 8px;text-align:left;vertical-align:top}
th{background:#161b22}code,pre{background:#161b22;padding:2px 4px;border-radius:4px}
pre{white-space:pre-wrap}.crit{color:#ff7b72}.high{color:#ffa657}.med{color:#d29922}
.pass{color:#3fb950}.fail{color:#ff7b72}.warn{color:#d29922}.card{background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:12px 16px;margin:12px 0}
.grid{display:flex;gap:12px;flex-wrap:wrap}.stat{min-width:90px;text-align:center}
.stat .v{font-size:22px}.mut{color:#8b949e}"""


def render_html(bundle: dict) -> str:
    p = bundle.get("provenance", {})
    parts = ["<!doctype html><html><head><meta charset=utf-8>",
             "<title>Intelligence Forensics report</title>",
             f"<style>{_CSS}</style></head><body>",
             "<h1>Intelligence Forensics — unified report</h1>"]
    parts.append('<div class=card><h2>Provenance</h2>' + _table(
        ["field", "value"],
        [["generated", p.get("generated_at_iso")],
         ["host", f"{p.get('host')} ({p.get('platform')})"],
         ["source DB", p.get("db_path")],
         ["DB SHA-256", p.get("db_sha256")],
         ["DB size", f"{p.get('db_bytes')} bytes @ {p.get('db_mtime')}"],
         ["model", p.get("model") or "(none)"],
         ["agentic run", p.get("run_id") or "(none)"]]) + "</div>")

    sec = bundle.get("security") or {}
    if sec and "error" not in sec:
        tot = sec.get("totals") or {}
        parts.append('<div class=card><h2>Security posture</h2>')
        parts.append(f"<p>Risk rating <b>{_e(sec.get('risk_rating'))}</b> — "
                     f"{_e(sec.get('n_findings'))} findings</p>")
        parts.append('<div class=grid>' + "".join(
            f"<div class='card stat'><div class='v'>{_e(tot.get(k,0))}</div>"
            f"<div class=mut>{_e(k)}</div></div>"
            for k in ("critical", "high", "medium", "low")) + "</div>")
        srows = [[f.get("severity"), f.get("kind"),
                  f"{f.get('source')}:{f.get('line')}", f.get("match"),
                  f.get("remediation")] for f in (sec.get("secrets") or [])
                 + (sec.get("injections") or [])][:60]
        parts.append(_table(["sev", "kind", "where", "match", "remediation"], srows))
        parts.append("</div>")

    rk = bundle.get("risk") or {}
    if rk.get("services"):
        parts.append('<div class=card><h2>Inflow risk by service</h2>' + _table(
            ["service", "band", "score", "prompts", "PII", "injections", "reuse"],
            [[s["service"], s["band"], s["score"], s["n"],
              (s.get("signals") or {}).get("pii", 0),
              (s.get("signals") or {}).get("injection", 0),
              (s.get("signals") or {}).get("cross_service_reuse", 0)]
             for s in rk["services"]]) + "</div>")

    tr = bundle.get("trust") or {}
    if tr.get("rules"):
        parts.append('<div class=card><h2>Trust boundaries</h2>' + _table(
            ["rule", "status", "severity", "detail"],
            [[r["rule"], f"<span class={r['status']}>{r['status']}</span>",
              r["severity"], r["detail"]] for r in tr["rules"]], raw_cols={1}) + "</div>")

    parts.append('<div class=card><h2>Services</h2>' + _table(
        ["service", "project", "reqs", "tokens", "score", "grade"],
        [[s["service"], s.get("project"), s.get("requests"), s.get("total_tokens"),
          s.get("score"), s.get("grade")] for s in bundle.get("services", [])]) + "</div>")

    diff = bundle.get("diff")
    if diff and not diff.get("first_run"):
        lines = []
        for k in ("services_added", "services_removed"):
            if diff.get(k):
                lines.append(f"{k.replace('_',' ')}: {', '.join(diff[k])}")
        for c in diff.get("score_changes", []):
            lines.append(f"score {c['service']}: {c['from']} -> {c['to']}")
        for c in diff.get("risk_band_changes", []):
            lines.append(f"risk {c['service']}: {c['from']} -> {c['to']}")
        for c in diff.get("trust_changes", []):
            lines.append(f"trust {c['rule']}: {c['from']} -> {c['to']}")
        parts.append('<div class=card><h2>Changes since last run</h2><ul>'
                     + "".join(f"<li>{_e(x)}</li>" for x in lines) + "</ul></div>")

    ag = bundle.get("agentic")
    if ag and ag.get("reporter_text"):
        parts.append('<div class=card><h2>Agentic reporter brief</h2><pre>'
                     + _e(ag["reporter_text"]) + "</pre></div>")

    parts.append("</body></html>")
    return "".join(parts)