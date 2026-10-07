#!/usr/bin/env python3
"""Investigation dashboard — view everything intelligence-forensics collected.

Run with the repo venv (has fastapi/uvicorn):
    /home/fox/codebase/.venv/bin/python dashboard.py [--port 8211]
or:
    IF_PORT=8211 /home/fox/codebase/.venv/bin/python -m uvicorn dashboard:app --host 0.0.0.0 --port 8211
"""
import argparse
import glob
import json
import os
import re
import sys
import time
from collections import deque

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from iforensics import config, store, infer, agents as ag, ollama_client
from iforensics import security_agent

app = FastAPI(title="Intelligence Forensics Dashboard", version="0.2.0")
app.mount("/static", StaticFiles(directory=os.path.join(config.BASE_DIR, "static")), name="static")

# Bump on every deploy — shown in the header so cached pages are detectable.
APP_VERSION = "0.5.0-live"

# POST rate limits (P5.22): max calls per window per path. No auth by design
# (T5: LAN/tailnet deployment), so this is abuse friction, not access
# control — it stops a runaway tab or LAN neighbour fork-bombing Ollama via
# POST /api/runs while leaving normal clicks untouched.
POST_LIMITS = {
    "/api/runs": (10, 60),
    "/api/investigate": (10, 60),
    "/api/security/scan": (10, 60),
    "/api/reports/run": (10, 60),
    "/api/live/start": (30, 60),
    "/api/live/stop": (30, 60),
    "/api/sim/run": (10, 300),
    "/api/sim/ingest": (1000, 300),
    "/api/sim/attack": (60, 60),
    "/api/sim/begin": (60, 60),
    "/api/sim/reset": (30, 60),
    "/api/sim/demo": (10, 60),
}
_POST_HITS: dict[str, deque] = {}


@app.middleware("http")
async def _post_rate_limit(request, call_next):
    if request.method == "POST" and request.url.path in POST_LIMITS:
        now = time.time()
        limit, window = POST_LIMITS[request.url.path]
        hits = _POST_HITS.setdefault(request.url.path, deque())
        while hits and now - hits[0] > window:
            hits.popleft()
        if len(hits) >= limit:
            return JSONResponse({"detail": "rate limited: too many POSTs"}, 429)
        hits.append(now)
    return await call_next(request)

PAGE = """<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Intelligence Forensics</title>
<link rel="stylesheet" href="/static/app.css"></head><body>
<header><h1>&#x1f575; Intelligence Forensics</h1><span class=sub id=hdr>loading&hellip;</span><span style="flex:1"></span><button id=b-theme title="toggle light/dark theme">◐</button></header>
<nav id=tabs>
<button data-t=overview class=on>Overview</button><button data-t=findings>Findings</button><button data-t=live>Live tap</button><button data-t=timeline>Timeline</button><button data-t=services>Services</button><button data-t=recon>Reconstructions</button><button data-t=agents>Agentic runs</button><button data-t=ledger>Ledger</button><button data-t=mesh>Mesh</button><button data-t=graph>Graph</button><button data-t=evidence>Evidence</button><button data-t=security>Security</button><button data-t=design>Design</button><button data-t=sim>Sim</button>
</nav><main>
<section id=s-overview class=on><div class=grid id=stats></div><div class=card><h3>Latest brief <span class=mut style="font-weight:normal">— rendered markdown</span></h3><div id=brief class=md>loading&hellip;</div></div>
<div class=card><h3>Run investigation</h3><div class=row>
<button class=act id=b-inv>Re-run heuristic investigation</button>
<button class=act id=b-agent>Launch agentic run (Qwen 3.8-27B)</button>
<button class=act id=b-report>Generate unified report</button>
<label class=mut><input type=checkbox id=opt-quick checked> quick (top-3, no critic)</label>
<span class=mut id=runmsg></span></div>
<div class=mut id=report-list></div></div></section>
<section id=s-findings><div class=card><div class=row><h3>What needs attention</h3><span class=mut id=find-sum></span><span style="flex:1"></span><select id=sel-find><option value="">all areas</option><option>security</option><option>risk</option><option>trust</option><option>claims</option><option>fidelity</option><option>alert</option></select></div><div id=find-bars class=mut>loading&hellip;</div></div><div class=card><table id=t-find><thead><tr><th>sev</th><th>area</th><th>finding</th><th>detail</th></tr></thead><tbody></tbody></table></div></section>
<section id=s-services><div class=card><div class=row><input id=filt-svc placeholder="filter services&hellip;"><button class=act data-x=t-svc data-name=services-CSV>CSV</button><button class=act data-x=t-svc data-name=services-JSON>JSON</button><span class=mut id=svc-msg></span></div><table id=t-svc><thead><tr><th>service</th><th>reqs</th><th>tokens</th><th>models</th><th>inferred build</th><th>score / vibe</th></tr></thead><tbody></tbody></table></div></section>
<section id=s-live><div class=card><h3>Tap <span class=mut id=live-state style="font-weight:normal"></span></h3>
<div class=row><button class=act id=b-live-start>Start tap</button><button class=act id=b-live-stop>Stop</button>
<label class=mut>every <input id=inp-live-int type=number value=5 min=1 max=60 style="width:56px">s</label>
<span class=mut>API-level sniff of fox :8210 — queue IN, completed OUT, model load SYS. Raw pcap needs the <code>pcap</code> compose profile (see README).</span></div></div>
<div class=card><h3>Rates <span class=mut style="font-weight:normal">— live window</span></h3><table id=t-rates><thead><tr><th>service</th><th>req</th><th>tokens</th><th>req/min</th><th>tok/min</th></tr></thead><tbody><tr><td class=mut colspan=5>tap not running</td></tr></tbody></table></div>
<div class=card><h3>Live reconstruction <span class=mut style="font-weight:normal">— recent history + live rows since tap started</span></h3>
<div class=row><select id=sel-live></select><select id=sel-lmode><option value=cumulative>cumulative</option><option value=window>window</option></select>
<button class=act id=b-live-recon>Reconstruct live</button><span class=mut id=live-recon-msg></span></div>
<table id=t-liveprog><thead><tr><th>step</th><th>score</th><th>queries</th><th>inferred build</th><th>Δ vs prev</th></tr></thead><tbody></tbody></table></div>
<div class=card><h3>Feed <span class=mut style="font-weight:normal">— newest first, auto-refresh</span></h3><table id=t-feed><thead><tr><th>time</th><th>dir</th><th>service</th><th>model</th><th>detail</th></tr></thead><tbody><tr><td class=mut colspan=5>tap not running</td></tr></tbody></table></div>
<div class=card><h3>Traffic <span class=mut style="font-weight:normal">— requests &amp; tokens per bucket</span></h3>
<div class=row><span class=mut>bucket</span><select id=sel-tsbucket><option value=1m>1m</option><option value=5m selected>5m</option><option value=15m>15m</option><option value=1h>1h</option></select>
<span class=mut>window</span><select id=sel-tswindow><option value=15m>15m</option><option value=1h selected>1h</option><option value=6h>6h</option><option value=24h>24h</option></select>
<label class=mut><input type=checkbox id=chk-tsauto checked> auto</label><span class=mut id=ts-msg></span></div>
<div id=ts-chart class="mut loading">loading&hellip;</div><div id=ts-legend class=mut></div>
<div id=ts-models class=mut></div><div id=ts-heatmap class=mut></div></div></section>
<section id=s-timeline><div class=card><div class=row><h3>Chain of events</h3><span class=mut id=chain-sum></span></div><div class=row><span class=mut>service</span><select id=sel-chain><option value="">all</option></select><span class=mut>limit</span><select id=sel-chain-n><option>50</option><option selected>100</option><option>200</option></select><button class=act id=b-chain>Reload</button></div><div class=mut>IN arrivals linked to OUT completions by queue id — queue-wait visible inline.</div><div id=chain class=mut>loading&hellip;</div></div></section>
<section id=s-recon><div class=card><div class=row><select id=sel-recon></select><select id=sel-file></select></div><pre id=recon-view>pick a reconstruction&hellip;</pre></div>
<div class=card><h3>Partial &amp; progressive reconstruction <span class=mut style="font-weight:normal">— same service, re-profiled as Fox queries accumulate</span></h3>
<div class=row><select id=sel-pmode><option value=cumulative>cumulative (0..k — confidence growth)</option><option value=window>window (slice k alone — partial views)</option></select>
<label class=mut>steps <input id=inp-pn type=number value=5 min=2 max=12 style="width:56px"></label>
<button class=act id=b-prog>Build progression</button><span class=mut id=prog-msg></span></div>
<table id=t-prog><thead><tr><th>step</th><th>score</th><th>queries seen</th><th>window</th><th>inferred build</th><th>pipeline</th><th>Δ vs prev</th></tr></thead><tbody><tr><td class=mut colspan=7>pick a service, then Build progression</td></tr></tbody></table></div>
<div class=card><h3>Score curve <span class=mut style="font-weight:normal">— bars = queries seen, line = reconstruction score, ◆ = label flip</span></h3><div id=prog-chart class=mut>build a progression to chart it</div></div>
<div class=card><h3>Step detail</h3><pre id=prog-detail>click a step row&hellip;</pre></div></section>
<section id=s-agents><div class=card><table id=t-runs><thead><tr><th>run</th><th>model</th><th>services</th><th>elapsed</th><th>errors</th></tr></thead><tbody></tbody></table></div>
<div class=card><h3>Reconstruction graph <span class=mut id=rg-title style="font-weight:normal"></span></h3>
<div id=run-dag class=mut>click a run above&hellip;</div>
<h3>Agent cost <span class=mut style="font-weight:normal">— tokens + wall time per agent (local model: $0.00)</span></h3><div id=run-cost></div>
<h3>Confidence &amp; agreement <span class=mut style="font-weight:normal">— LLM profiler vs heuristic rules</span></h3><table id=t-conf><thead><tr><th>service</th><th>confidence</th><th>heuristic says</th><th>LLM says</th><th>agree</th></tr></thead><tbody></tbody></table>
<h3>Critic gaps</h3><div id=run-gaps></div>
<h3>Evidence quotes <span class=mut style="font-weight:normal">— prompt lines the profiler cited</span></h3><div id=run-quotes></div></div>
<div class=card><h3>Across runs <span class=mut style="font-weight:normal">— profiler confidence per service, newest first</span></h3><table id=t-trend><thead><tr><th>service</th><th>trend</th></tr></thead><tbody></tbody></table></div>
<div class=card><h3>Brief <span class=mut style="font-weight:normal">— rendered markdown</span></h3><div id=run-brief class=md>click a run&hellip;</div></div></section>
<section id=s-ledger><div class=card><div class=row><h3>Action ledger</h3><span class=mut id=ledger-verdict></span></div><div class=row><span class=mut>run</span><select id=sel-ledger></select><button class=act id=b-ledger>Reload</button><input id=filt-ledger placeholder="filter task/actor/action&hellip;"><span class=mut>every action, hash-chained — tampering breaks verification at the exact entry</span></div><table id=t-ledger><thead><tr><th>seq</th><th>actor</th><th>action</th><th>task</th><th>artifact sha</th></tr></thead><tbody></tbody></table></div><div class=card><div class=row><h3>Task queue</h3><span class=mut id=queue-sum></span></div><table id=t-queue><thead><tr><th>state</th><th>depth</th></tr></thead><tbody></tbody></table></div></section>
<section id=s-mesh><div class=card><h3>Topology <span class=mut style="font-weight:normal">— service → container → peer → model</span></h3><div id=topo class=mut>loading&hellip;</div></div><div class=card><table id=t-mesh><thead><tr><th>node</th><th>online</th><th>hw</th><th>llm/1h</th><th>services</th></tr></thead><tbody></tbody></table></div></section>
<section id=s-graph><div class=card><div class=row><h3>Knowledge graph</h3><span class=mut id=kg-sum></span></div><div class=mut>Services, prompt templates, models, findings and built evidence — a template node with edges into two services is cross-service leakage made visible.</div><div id=kg class=mut>loading&hellip;</div></div></section>
<section id=s-evidence><div class=card><div class=row><input id=filt-ev placeholder="filter files&hellip;"><button class=act data-x=t-ev data-name=evidence-CSV>CSV</button><button class=act data-x=t-ev data-name=evidence-JSON>JSON</button><span class=mut id=ev-msg></span></div><table id=t-ev><thead><tr><th>file</th><th>size</th></tr></thead><tbody></tbody></table></div>
<div class=card><h3>Preview <span class=mut id=ev-name style="font-weight:normal"></span></h3><div class=row><a id=ev-dl class=act download href="#">Download</a><span class=mut id=ev-info></span></div><pre id=ev-view>click a file&hellip;</pre></div></section>
<section id=s-security><div class=card><div class=row>
<button class=act id=b-sec-scan>Run security scan (deterministic + LLM)</button>
<select id=sel-secscope><option value=app>this app</option><option value=workspace>parent workspace (all subfolders)</option></select>
<span class=mut>view</span><select id=sel-secview><option value=table>Table</option><option value=analytics>Analytics</option></select>
<span class=mut id=sec-msg></span></div>
<div class=mut id=sec-stored></div><div class=mut id=sec-tracked></div>
<div class="grid stats" id=sec-stats></div>
<div id=sec-analytics class=mut>pick Analytics view&hellip;</div>
<div id=sec-tables>
<h3>Findings by project</h3><table class=tbl id=t-sec-proj><thead><tr><th>project</th><th>crit</th><th>high</th><th>med</th><th>low</th><th>total</th></tr></thead><tbody></tbody></table>
<h3>Dashboard exposure</h3><div id=sec-exp class=mut>loading&hellip;</div>
<h3>Secret / PII survivors</h3><table class=tbl id=t-sec-secrets><thead><tr><th>kind</th><th>sev</th><th>where</th><th>match</th><th>flags</th></tr></thead><tbody></tbody></table>
<h3>Prompt-injection attempts</h3><table class=tbl><thead><tr><th>kind</th><th>sev</th><th>where</th><th>match</th></tr></thead><tbody id=sec-inject></tbody></table>
<h3>Over-permissive files</h3><table class=tbl><thead><tr><th>file</th><th>mode</th><th>sev</th></tr></thead><tbody id=sec-perm></tbody></table>
</div></div>
<div class=card>
<div class=row><h3>Trust boundaries (D4)</h3><span class=mut id=sec-trust-sum></span></div>
<div class=mut>Assertions from design/trust-boundaries.md, re-checked against the code.</div>
<table class=tbl id=t-sec-trust><thead><tr><th>rule</th><th>status</th><th>sev</th><th>detail</th></tr></thead><tbody></tbody></table>
</div>
<div class=card>
<div class=row><h3>Inflow risk by service (D5)</h3><span class=mut id=sec-risk-sum></span></div>
<div class=mut>Ranked from secrets/injection attempts, volume outliers and cross-service prompt reuse.</div>
<table class=tbl id=t-sec-risk><thead><tr><th>service</th><th>band</th><th>score</th><th>PII</th><th>inj</th><th>vol z</th><th>reuse</th></tr></thead><tbody></tbody></table>
</div></section>
<section id=s-design><div class=row><div class=card style="min-width:230px"><h3>Documents</h3><div id=design-rail class=mut>loading&hellip;</div></div>
<div class=card style="flex:1"><h3 id=design-title>Design &amp; architecture</h3><div class=mut id=design-meta></div><div id=design-doc class=mut>pick a document&hellip;</div></div></div></section>
<section id=s-sim><div class=card><div class=row><h3>Embedding-reconstruction sim</h3><span class=mut id=sim-sum></span><span style="flex:1"></span><button class=act id=b-sim-demo>Load demo data</button><button class=act id=b-sim-reset>Reset</button></div><div class=mut>Progressive masked disclosure → cosine clustering → position-wise assembly. Run <code>python sim/run.py --all</code> for the full client, or inspect results here.</div><div class=row><span class=mut>DLP</span><select id=sel-sim-dlp><option value=off>off</option><option value=audit>audit</option><option value=redact>redact</option><option value=block>block</option></select><span class=mut id=sim-dlp-sum></span></div><div class=row><span class=mut>user</span><select id=sel-sim></select><button class=act id=b-sim-report>Report</button></div><div id=sim-curve class=mut>pick a user&hellip;</div><div id=sim-fields class=mut></div><div id=sim-est class=mut></div></div>
<div class=card><div class=row><h3>Run scenarios</h3><span class=mut id=sim-runmsg></span></div><div class=row><select id=sel-sim-sc><option value=all>all scenarios</option><option value=chatbot_health>chatbot_health</option><option value=chatbot_financial>chatbot_financial</option><option value=coding_api_keys>coding_api_keys</option><option value=coding_secrets>coding_secrets</option></select><select id=sel-sim-style><option value=regular>regular</option><option value=one-off>one-off</option><option value=vibe>vibe</option></select><button class=act id=b-sim-run>Run</button></div><div id=sim-runout class=mut></div></div>
<div class=card><h3>Scenarios</h3><div class=mut>What each experiment leaks, step by step.</div><div id=sim-scenarios class=mut>loading&hellip;</div></div></section>
</main>
<div id=tip class=tip></div>
<script src="/static/app.js" defer></script></body></html>
"""


def _newest_db() -> str | None:
    dbs = sorted(glob.glob(os.path.join(config.EVIDENCE_DIR, "fox_services_*.db")))
    if dbs:
        return dbs[-1]
    return config.find_fox_db()


def _service_rows(limit: int = 5000) -> list[dict]:
    db = _newest_db()
    if not db or not os.path.exists(db):
        return []
    return store.load_requests(db, limit=limit)


def _within(path: str, root: str) -> bool:
    """True only if *path* is root itself or strictly inside it.

    A plain startswith(root) is a prefix check, not a containment check:
    /recon/quai-radar2 passes for root /recon/quai-radar. Compare against
    root + os.sep so sibling directories with a shared prefix are refused.
    """
    root = os.path.realpath(root)
    return path == root or path.startswith(root + os.sep)


@app.get("/health")
def health():
    return {"status": "ok", "service": "intel-forensics", "model": ollama_client.MODEL}


@app.get("/", response_class=HTMLResponse)
def index():
    return PAGE


@app.get("/api/overview")
def overview():
    rows = _service_rows(limit=5000)
    svcs = {r.get("service") for r in rows}
    recon = [d for d in glob.glob(os.path.join(config.RECON_DIR, "*")) if os.path.isdir(d)]
    try:
        fox = store.snapshot_api  # touch import; real check below
        import urllib.request
        with urllib.request.urlopen(config.FOX_URL + "/health", timeout=3) as r:
            fox_ok = "ok" if r.status == 200 else str(r.status)
    except Exception as e:  # noqa: BLE001
        fox_ok = f"down ({type(e).__name__})"
    return {"requests": len(rows), "services": len(svcs),
            "reconstructions": len(recon), "agent_runs": len(ag.list_runs()),
            "fox": fox_ok, "model": ollama_client.MODEL,
            "ollama": ollama_client.OLLAMA_URL, "version": APP_VERSION}


@app.get("/api/services")
def services():
    from iforensics import score as scoring
    rows = _service_rows()
    if not rows:
        return {"services": []}
    inv = infer.investigate_all(rows)
    out = []
    for svc, p in inv["services"].items():
        s = scoring.score_profile(p)
        v = scoring.vibe_index(p, stable=True)
        out.append({"service": svc, "requests": p["requests"],
                    "total_tokens": p["total_tokens"], "models": p["models"],
                    "query_types": p.get("query_types"),
                    "project": p.get("project"),
                    "pipeline_summary": p.get("pipeline_summary"),
                    "pipeline": p.get("pipeline"),
                    "score": s["score"], "grade": s["grade"], "factors": s["factors"],
                    "vibe": v["vibe"], "vibe_label": v["label"]})
    return {"services": sorted(out, key=lambda s: -s["requests"])}


@app.get("/api/investigation")
def investigation():
    md_path = os.path.join(config.EVIDENCE_DIR, "INVESTIGATION.md")
    return {"readme": open(md_path).read() if os.path.exists(md_path) else ""}


@app.post("/api/investigate")
def investigate():
    from iforensics import report as report_mod
    from iforensics import fox_client
    api = fox_client.collect_all(hours=720, req_limit=2000)
    rows = _service_rows()
    if not rows:
        raise HTTPException(503, "no evidence DB rows available")
    inv = infer.investigate_all(rows)
    mesh = api.get("mesh_status") if isinstance(api.get("mesh_status"), dict) else None
    md = report_mod.render(inv, mesh=mesh)
    path = os.path.join(config.EVIDENCE_DIR, "INVESTIGATION.md")
    report_mod.write(md, path)
    return {"report": path, "requests": inv["n_requests"], "services": inv["n_services"]}


@app.get("/api/reports")
def reports_list():
    """Versioned unified reports (newest first)."""
    from iforensics import unified_report
    return {"reports": list(reversed(unified_report.load_index()))}


@app.post("/api/reports/run")
def reports_run():
    """Assemble heuristic + agentic + scores + critic gaps + security + provenance,
    diff against the previous run and persist md/html/json."""
    from iforensics import unified_report
    rows = _service_rows()
    out = unified_report.run_report(rows=rows or None, model=ollama_client.MODEL)
    entry = out["paths"]["entry"]
    return {"id": out["paths"]["id"], "entry": entry,
            "diff": out["bundle"].get("diff", {}), "markdown": entry["markdown"],
            "html": entry["html"]}


@app.get("/api/reconstructions")
def reconstructions():
    out = []
    for d in sorted(glob.glob(os.path.join(config.RECON_DIR, "*"))):
        if not os.path.isdir(d):
            continue
        meta_path = os.path.join(d, "RECONSTRUCTED.json")
        meta = {}
        if os.path.exists(meta_path):
            try:
                with open(meta_path) as f:
                    meta = json.load(f)
            except Exception:  # noqa: BLE001
                pass
        out.append({"service": os.path.basename(d),
                    "project": meta.get("inferred_project", ""),
                    "requests": (meta.get("reconstructed_from") or {}).get("requests", 0)})
    return out


@app.get("/api/reconstructions/{svc}")
def reconstruction(svc: str):
    base = os.path.realpath(os.path.join(config.RECON_DIR, svc))
    if not _within(base, config.RECON_DIR) or not os.path.isdir(base):
        raise HTTPException(404, "unknown service")
    files = {}
    for root, _, fns in os.walk(base):
        for fn in fns:
            fp = os.path.join(root, fn)
            rel = os.path.relpath(fp, base)
            try:
                with open(fp) as f:
                    files[rel] = f.read()[:20000]
            except Exception:  # noqa: BLE001
                pass
    return {"service": svc, "files": files}


@app.get("/api/reconstructions/{svc}/file")
def reconstruction_file(svc: str, path: str):
    base = os.path.realpath(os.path.join(config.RECON_DIR, svc))
    target = os.path.realpath(os.path.join(base, path))
    # containment must be against *this service's* dir, not the RECON_DIR
    # root: checking the root alone lets a ..-path walk into a sibling
    # service's files (e.g. quai-radarX).
    if not _within(target, base) or not os.path.isfile(target):
        raise HTTPException(404, "bad path")
    with open(target) as f:
        return {"content": f.read()[:30000]}


@app.get("/api/reconstructions/{svc}/fidelity")
def reconstruction_fidelity(svc: str):
    """How much of a service's recent traffic its recovered templates explain.

    Completions are not logged upstream, so this scores template recall
    against observed prompts — drift signal, not I/O proof.
    """
    from iforensics import fidelity as fid_mod
    rows = [r for r in _service_rows(limit=5000) if (r.get("service") or "") == svc]
    if not rows:
        raise HTTPException(404, "unknown service (no queries)")
    return fid_mod.score_service(svc, [r.get("prompt") or "" for r in rows])


@app.get("/api/reconstructions/{svc}/progression")
def reconstruction_progression(svc: str, n: int = 5, mode: str = "cumulative"):
    """Partial + progressive reconstructions from Fox-server queries.

    mode=cumulative: step k profiles queries[0..k] (confidence growth).
    mode=window: step k profiles only its own time slice (partial views).
    """
    from iforensics import progression as prog, score as scoring
    if mode not in ("cumulative", "window"):
        raise HTTPException(400, "mode must be cumulative|window")
    rows = _service_rows(limit=5000)
    if not any((r.get("service") or "") == svc for r in rows):
        raise HTTPException(404, "unknown service (no queries)")
    res = prog.progression(svc, rows, n=max(2, min(12, n)), mode=mode)
    return scoring.attach_scores(res)


class RunReq(BaseModel):
    quick: bool = True
    model: str | None = None
    only: list[str] | None = None
    swarm: bool = False


@app.get("/api/runs")
def runs():
    # in-flight runs first: otherwise a queued backlog looks like nothing happened
    return ag.pending_runs() + ag.list_runs()


@app.get("/api/runs/{run_id}")
def run_detail(run_id: str):
    m = ag.load_run(run_id)
    if not m:
        raise HTTPException(404, "unknown run")
    return m


@app.get("/api/runs/{run_id}/validation")
def run_validation(run_id: str):
    """Claims-vs-evidence check on the reporter's brief (P5.21)."""
    from iforensics import claims as claims_mod
    m = ag.load_run(run_id)
    if not m:
        raise HTTPException(404, "unknown run")
    return claims_mod.validate_run(m)


@app.get("/api/swarm/runs")
def swarm_runs():
    """Ledger index: every run with an action chain (P7.31)."""
    from iforensics import ledger as ledger_mod
    return {"runs": ledger_mod.runs()}


@app.get("/api/swarm/ledger")
def swarm_ledger(run_id: str, limit: int = 500):
    """Action entries for a run, newest last (P7.31)."""
    from iforensics import ledger as ledger_mod
    entries = ledger_mod.read(run_id)
    if not entries:
        raise HTTPException(404, "no ledger for run")
    return {"run_id": run_id, "entries": entries[-max(1, min(2000, limit)):]}


@app.get("/api/swarm/verify")
def swarm_verify(run_id: str):
    """Recompute a run's hash chain (P7.31)."""
    from iforensics import ledger as ledger_mod
    return ledger_mod.verify(run_id)


@app.get("/api/swarm/queue")
def swarm_queue():
    """Task queue depths per state (P7.31)."""
    from iforensics import swarm as swarm_mod
    return swarm_mod.status()


class SimBegin(BaseModel):
    user_id: str
    truth: dict = {}
    scenario: str = ""


class SimIngest(BaseModel):
    prompt: str
    mask: str = ""
    step: int = 0
    metadata: dict = {}


class SimAttack(BaseModel):
    kind: str = "progressive"
    user_id: str = ""
    field: str = ""
    value: str = ""
    threshold: float = 0.7
    swarm: bool = False


@app.post("/api/sim/begin")
def sim_begin(req: SimBegin):
    """Register a scenario user's ground truth (synthetic values only)."""
    from iforensics.sim import state as sim_state
    if not req.user_id:
        raise HTTPException(400, "user_id required")
    sim_state.STATE.register_truth(req.user_id, req.truth or {})
    return {"ok": True, "user_id": req.user_id,
            "fields": sorted((req.truth or {}).keys())}


@app.post("/api/sim/ingest")
def sim_ingest(req: SimIngest):
    """Embed + store one query/response pair with metadata."""
    from iforensics.sim import state as sim_state
    if not req.prompt:
        raise HTTPException(400, "prompt required")
    st = sim_state.STATE
    with st.lock:
        out = st.gateway.process_query(req.prompt, req.metadata or {},
                                       mask=req.mask, step=req.step,
                                       dlp=st.policy)
    return {"ids": out["ids"], "response": out["response"],
            "backend": st.backend_note, "stored": len(st.store)}


@app.post("/api/sim/attack")
def sim_attack(req: SimAttack):
    """Run one reconstruction attack over the stored embeddings."""
    from iforensics.sim import attacks as sim_attacks
    from iforensics.sim import state as sim_state
    st = sim_state.STATE
    filtr = {"user_id": req.user_id} if req.user_id else None
    texts, vecs = st.store.texts_vectors(filtr)
    if req.kind == "progressive" and req.swarm:
        import time as _time
        from iforensics import ledger as ledger_mod
        from iforensics import swarm as swarm_mod
        run = f"sim-{req.user_id or 'all'}-{int(_time.time())}"
        task = swarm_mod.enqueue("sim_reconstruct", {"texts": texts[:200]},
                                 run_id=run)
        try:
            ledger_mod.append(run, "orchestrator", "task.issued",
                              task_id=task["task_id"])
        except Exception:  # noqa: BLE001
            pass
        res = swarm_mod.collect_results([task["task_id"]], timeout_s=180.0)
        if task["task_id"] in res["done"]:
            out = dict(res["done"][task["task_id"]])
            out["source"] = "swarm"
            return out
        raise HTTPException(504, "swarm worker timeout: no reconstruction collected")
    if req.kind == "progressive":
        return sim_attacks.progressive_attack(texts, vecs, req.threshold)
    if req.kind == "near_duplicates":
        cls = sim_attacks.cluster(texts, vecs, req.threshold)
        return {"n_clusters": len(cls),
                "clusters": [{"size": len(c),
                              "samples": [texts[i][:120] for i in c[:3]]}
                             for c in cls if len(c) > 1]}
    if req.kind == "membership":
        if not req.value:
            raise HTTPException(400, "value required for membership")
        texts_m = st.store.get_all(filtr)
        return sim_attacks.membership_candidate(
            req.value, [t["text"] for t in texts_m], st.embedder.embed_one)
    raise HTTPException(400, f"unknown attack kind: {req.kind!r}")


@app.get("/api/sim/report")
def sim_report(user_id: str):
    """Accuracy report: assembled secrets vs registered ground truth."""
    from iforensics.sim import reporting as sim_reporting
    from iforensics.sim import state as sim_state
    try:
        return sim_reporting.build_report(sim_state.STATE, user_id)
    except sim_reporting.UnknownUser:
        raise HTTPException(404, "no ground truth for user (POST /api/sim/begin)")


@app.post("/api/sim/reset")
def sim_reset():
    """Clear embeddings + truth (fresh experiment)."""
    from iforensics.sim import state as sim_state
    return {"cleared": sim_state.STATE.reset()["ok"],
            "backend": sim_state.STATE.backend_note}


class SimDLP(BaseModel):
    mode: str = "off"
    actions: dict = {}


@app.get("/api/sim/dlp")
def sim_dlp_get():
    """Current DLP policy + interception journal summary."""
    from iforensics.sim import state as sim_state
    return sim_state.STATE.get_policy()


@app.post("/api/sim/dlp")
def sim_dlp_set(req: SimDLP):
    """Set enforcement (off|audit|redact|block) with optional per-kind actions."""
    from iforensics.sim import state as sim_state
    try:
        return sim_state.STATE.set_policy(req.mode, req.actions or {})
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.get("/api/sim/users")
def sim_users():
    """Scenario users with truth fields + stored pair counts."""
    from iforensics.sim import state as sim_state
    st = sim_state.STATE
    users = st.truth_users()
    counts = {}
    for it in st.store.get_all():
        u = it["metadata"].get("user_id")
        if u:
            counts[u] = counts.get(u, 0) + 1
    return {"users": [{"user_id": u,
                       "fields": sorted(st.get_truth(u)),
                       "pairs": counts.get(u, 0) // 2} for u in users],
            "backend": st.backend_note}


@app.post("/api/sim/demo")
def sim_demo():
    """Self-contained demo: 2 users x 3 masked steps, no client needed."""
    from iforensics.sim import queries as sim_q
    from iforensics.sim import sensitive as sim_sens
    from iforensics.sim import state as sim_state
    import random
    st = sim_state.STATE
    st.reset()
    demo = [("demo-health", "ssn", "What is my blood pressure trend?"),
            ("demo-code", "api_key", "How do I connect to the API?")]
    for user_id, field, base in demo:
        rng = random.Random(hash(user_id) & 0xFFFFFFFF)
        value = sim_sens.generate(field, seed=abs(hash(user_id)) % 100000)["value"]
        st.register_truth(user_id, {field: value})
        for i, qp in enumerate(sim_q.build_progressive(base, value, steps=3)):
            with st.lock:
                st.gateway.process_query(
                    qp["prompt"], {"user_id": user_id, "scenario": "demo",
                                   "field": field}, mask=qp["mask"], step=i)
    return {"ok": True, "users": [u for u, _, _ in demo],
            "backend": st.backend_note}


@app.get("/api/sim/scenarios")
def sim_scenarios():
    """Scenario catalogue with per-scenario mermaid diagrams (no secrets)."""
    from iforensics.sim import runner as sim_runner
    return {"scenarios": sim_runner.describe()}


class SimRun(BaseModel):
    scenario: str = "all"
    n: int = 60
    seed: int = 42
    style: str = "regular"
    dlp_mode: str = "off"
    threshold: float = 0.6


@app.post("/api/sim/run")
def sim_run(req: SimRun):
    """Trigger scenarios server-side (the Sim tab's Run button)."""
    from iforensics.sim import runner as sim_runner
    names = sim_runner.available() if req.scenario == "all" else [req.scenario]
    if req.scenario != "all" and req.scenario not in sim_runner.available():
        raise HTTPException(400, f"unknown scenario: {req.scenario!r}")
    if req.style not in ("one-off", "regular", "vibe"):
        raise HTTPException(400, "style must be one-off|regular|vibe")
    out = {}
    for name in names:
        try:
            out[name] = sim_runner.run_scenario(
                name, n=max(1, min(200, req.n)), seed=req.seed,
                threshold=req.threshold, style=req.style,
                dlp_mode=req.dlp_mode)
        except Exception as e:  # noqa: BLE001 — one scenario must not kill the batch
            out[name] = {"error": f"{type(e).__name__}: {e}"}
    return {"results": out}


@app.get("/api/findings")
def findings_hub():
    """One severity-ranked list across security, risk, trust, claims,
    fidelity and live alerts (P6.23)."""
    from iforensics import claims as claims_mod
    from iforensics import findings as fin_mod
    from iforensics import live as live_mod
    rows = _service_rows()
    tap_status = None
    t = live_mod.tap()
    if t:
        try:
            tap_status = t.status()
        except Exception:  # noqa: BLE001
            tap_status = None
    validation = None
    try:
        runs = ag.list_runs()
        if runs:
            m = ag.load_run(runs[0]["run_id"])
            if m:
                validation = claims_mod.validate_run(m)
    except Exception:  # noqa: BLE001
        validation = None
    return fin_mod.collect(rows=rows, app=app, tap_status=tap_status,
                           run_validation=validation)


@app.get("/api/chain")
def chain_events(service: str | None = None, limit: int = 200,
                 source: str = "auto"):
    """One chronological chain: history rows + live IN/OUT/SYS, linked by qid."""
    from iforensics import chain as chain_mod
    from iforensics import live as live_mod
    live_events: list[dict] = []
    if source in ("live", "auto"):
        t = live_mod.tap()
        if t:
            try:
                live_events = t.snapshot(live_mod.MAX_EVENTS)
            except Exception:  # noqa: BLE001
                live_events = []
    if not live_events and source in ("log", "auto"):
        try:
            live_events = live_mod.persisted_events(limit=5000)
        except Exception:  # noqa: BLE001
            live_events = []
    rows = _service_rows(limit=5000)
    return chain_mod.build_chain(rows=rows, live_events=live_events,
                                 service=service or None,
                                 limit=max(1, min(200, limit)))


@app.get("/api/knowledge")
def knowledge_graph():
    """Entity graph: services, templates, models, findings, evidence (P6.25)."""
    from iforensics import knowledge as kg_mod
    from iforensics import risk as risk_mod
    rows = _service_rows(limit=2000)
    try:
        risk = risk_mod.service_risk(rows)
    except Exception:  # noqa: BLE001
        risk = {"services": []}
    return kg_mod.build(rows=rows, risk=risk)


@app.get("/api/runs/{run_id}/graph")
def run_graph(run_id: str):
    """Chart-ready agentic reconstruction: DAG, costs, confidence,
    heuristic-vs-LLM agreement, critic gaps."""
    from iforensics import run_viz
    g = run_viz.build_run_graph(run_id)
    if not g:
        raise HTTPException(404, "unknown run")
    return g


@app.get("/api/runs-compare")
def runs_compare(limit: int = 5):
    """Confidence per service across the last N runs (cross-run trend)."""
    from iforensics import run_viz
    return run_viz.compare_runs(max(2, min(10, limit)))


class LiveStartReq(BaseModel):
    interval_s: float = 5.0


@app.post("/api/live/start")
def live_start(req: LiveStartReq):
    """Attach the live tap to fox :8210 (queue + request deltas + model loads)."""
    from iforensics import live as live_mod
    return live_mod.start(max(1.0, min(60.0, req.interval_s or 5.0)))


@app.post("/api/live/stop")
def live_stop():
    from iforensics import live as live_mod
    return live_mod.stop()


@app.get("/api/live/status")
def live_status():
    from iforensics import live as live_mod
    t = live_mod.tap()
    return t.status() if t else {"running": False}


@app.get("/api/live/feed")
def live_feed(limit: int = 50, since_id: int = 0):
    """Recent events. With since_id>0 returns the delta (ascending) plus
    last_seq so the client can poll incrementally without re-rendering."""
    from iforensics import live as live_mod
    t = live_mod.tap()
    if not t:
        raise HTTPException(409, "tap not running (POST /api/live/start)")
    evs = t.snapshot(max(1, min(500, limit)), since_seq=max(0, since_id))
    return {"events": evs, "last_seq": t.last_seq()}


@app.get("/api/live/stream")
def live_stream(since_id: int = 0):
    """Server-sent events: one `data:` frame per tap event, plus heartbeats.

    Cheaper than polling the whole feed: the client keeps its last seq and
    gets only new frames between heartbeats.
    """
    from iforensics import live as live_mod

    def gen():
        last = max(0, since_id)
        while True:
            t = live_mod.tap()
            if not t:
                yield "event: stopped\ndata: {}\n\n"
                return
            for e in t.snapshot(500, since_seq=last):
                last = max(last, e.get("seq", last))
                yield f"data: {json.dumps(e)}\n\n"
            yield f": hb {int(time.time())}\n\n"
            time.sleep(1.0)

    return StreamingResponse(gen(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache",
                                      "Connection": "keep-alive",
                                      "X-Accel-Buffering": "no"})


@app.get("/api/live/persisted")
def live_persisted(day: str | None = None, limit: int = 200,
                   since_ts: float = 0.0):
    """Durable tap log read from disk — works even with the tap stopped."""
    from iforensics import live as live_mod
    if day is not None and not re.fullmatch(r"\d{8}", day):
        raise HTTPException(400, "day must be YYYYMMDD")
    return {"events": live_mod.persisted_events(
        day=day, limit=max(1, min(5000, limit)), since_ts=max(0.0, since_ts))}


@app.get("/api/live/rates")
def live_rates(window_s: float = 300):
    from iforensics import live as live_mod
    return live_mod.rates(max(30.0, min(3600.0, window_s)))


@app.get("/api/stats/timeseries")
def stats_timeseries(bucket: str = "1m", window: str = "1h",
                     service: str | None = None, source: str = "auto"):
    """Bucketed traffic (req/tokens/errors) from the live tap or the log.

    source=auto prefers the live buffer, falling back to the durable log when
    the tap is stopped, so the chart is populated either way.
    """
    from iforensics import live as live_mod, timeseries as ts
    try:
        bucket_s = ts.parse_duration(bucket)
        window_s = ts.parse_duration(window)
    except ValueError as e:
        raise HTTPException(400, str(e))
    if not (1 <= bucket_s <= 86400) or not (bucket_s <= window_s <= 7 * 86400):
        raise HTTPException(400, "need 1s<=bucket<=24h and bucket<=window<=7d")
    now = time.time()
    services = {service} if service else None
    events: list[dict] = []
    used = source
    if source in ("live", "auto"):
        t = live_mod.tap()
        if t:
            events = t.snapshot(live_mod.MAX_EVENTS)
            used = "live"
    if not events and source in ("log", "auto"):
        events = live_mod.persisted_events(limit=50000, since_ts=now - window_s)
        used = "log"
    out = ts.bucketize(events, bucket_s=bucket_s, window_s=window_s,
                       now=now, services=services)
    out["source"] = used
    return out


@app.get("/api/live/reconstruction")
def live_reconstruction(service: str, n: int = 5, mode: str = "cumulative",
                        history: int = 200):
    """Progressive reconstruction over recent history + live rows.

    Sparse live traffic alone rarely fills a window, so the window is
    backfilled from recent fox history (oldest first) with tap-buffered
    live rows appended (deduped by id). Response reports the mix.
    """
    from iforensics import live as live_mod
    from iforensics import progression as prog, score as scoring
    if mode not in ("cumulative", "window"):
        raise HTTPException(400, "mode must be cumulative|window")
    hist = live_mod.history_rows(service, limit=max(0, min(2000, history)))
    live_rows: list[dict] = []
    t = live_mod.tap()
    if t:
        seen = {r.get("id") for r in hist}
        live_rows = [r for r in t.rows() if r.get("service") == service
                     and r.get("id") not in seen]
    rows = sorted(hist + live_rows, key=lambda r: r.get("ts", 0))
    if len(rows) < 2:
        raise HTTPException(409, f"only {len(rows)} rows for {service!r} — no history yet")
    res = scoring.attach_scores(prog.progression(service, rows, n=max(2, min(12, n)), mode=mode))
    res["history_rows"] = len(hist)
    res["live_rows"] = len(live_rows)
    res["tap_running"] = t is not None
    return res


@app.get("/api/design/docs")
def design_docs_index():
    """Every design document, in reading order, with diagram counts."""
    from iforensics import design_docs
    return design_docs.list_docs()


@app.get("/api/design/docs/{doc_id}")
def design_doc(doc_id: str):
    """One design document's Markdown. Fixed id index — traversal 404s."""
    from iforensics import design_docs
    try:
        return design_docs.get_doc(doc_id)
    except design_docs.UnknownDoc:
        raise HTTPException(404, "unknown doc")


@app.post("/api/runs")
def runs_create(req: RunReq):
    model = req.model or ollama_client.MODEL
    try:
        key = ag.launch_background(_service_rows, model=model,
                                   quick=req.quick, only=req.only, swarm=req.swarm)
    except RuntimeError as e:  # concurrency cap (P7.35)
        raise HTTPException(429, str(e))
    return {"launched": key, "model": model, "quick": req.quick,
            "swarm": req.swarm}


@app.get("/api/runs-pending/{key}")
def run_pending(key: str):
    return ag.background_status(key)


@app.get("/api/evidence")
def evidence():
    files = []
    if os.path.isdir(config.EVIDENCE_DIR):
        for root, _, fns in os.walk(config.EVIDENCE_DIR):
            for fn in fns:
                fp = os.path.join(root, fn)
                try:
                    sz = os.path.getsize(fp) / 1024 / 1024
                except OSError:
                    sz = 0
                files.append({"name": os.path.relpath(fp, config.EVIDENCE_DIR),
                              "size_mb": round(sz, 2)})
    return {"files": sorted(files, key=lambda f: f["name"], reverse=True)[:100]}


@app.get("/api/evidence/file")
def evidence_file(name: str, download: int = 0):
    """Preview (text, capped) or download one evidence file. Containment-checked."""
    if not name or os.path.isabs(name) or ".." in name.split("/"):
        raise HTTPException(404, "bad name")
    fp = os.path.realpath(os.path.join(config.EVIDENCE_DIR, name))
    if not _within(fp, config.EVIDENCE_DIR) or not os.path.isfile(fp):
        raise HTTPException(404, "not found")
    if download:
        return FileResponse(fp, filename=os.path.basename(fp),
                            media_type="application/octet-stream")
    cap = 262144
    with open(fp, "rb") as fh:
        raw = fh.read(cap + 1)
    truncated = len(raw) > cap
    raw = raw[:cap]
    binary = b"\x00" in raw
    return {"name": name, "size": os.path.getsize(fp), "truncated": truncated,
            "binary": binary, "text": "" if binary else raw.decode("utf-8", "replace")}


@app.get("/api/security")
def security_report(scope: str = "app"):
    """Deterministic leak/exposure scan + the last persisted advisor assessment."""
    if scope not in ("app", "workspace"):
        raise HTTPException(400, "scope must be app|workspace")
    report = security_agent.deterministic_report(
        app=app, scope=scope)
    stored = None
    suffix = "" if scope == "app" else "-workspace"
    p = os.path.join(config.EVIDENCE_DIR, f"security{suffix}.json")
    if os.path.isfile(p):
        try:
            with open(p) as fh:
                stored = json.load(fh)
        except (OSError, ValueError):
            stored = None
    return {"report": report, "stored": stored}


class ScanReq(BaseModel):
    model: str | None = None
    scope: str = "app"


@app.post("/api/security/scan")
def security_scan(req: ScanReq | None = None):
    """Run the deterministic scan plus the LLM security advisor; persist artifacts."""
    scope = (req.scope if req else "app") or "app"
    if scope not in ("app", "workspace"):
        raise HTTPException(400, "scope must be app|workspace")
    model = req.model if req else None
    return security_agent.run_security(app=app, model=model, use_llm=True,
                                       scope=scope)


@app.get("/api/trust")
def trust_audit():
    """Re-check the trust-boundary claims (T1-T6) against the current code."""
    from iforensics import trust
    return trust.audit()


@app.get("/api/risk")
def service_risk(limit: int = 5000):
    """Rank services by inflow risk (PII/injection/volume/cross-service reuse)."""
    from iforensics import risk as risk_mod
    from iforensics import live as live_mod
    rows = _service_rows(limit=max(1, min(20000, limit)))
    if not rows:
        t = live_mod.tap()
        rows = t.rows() if t else []
    return risk_mod.service_risk(rows)


@app.get("/api/ollama")
def ollama():
    return ollama_client.ping()


@app.get("/api/fox/live")
def fox_live():
    from iforensics import fox_client
    out: dict = {}
    calls = {
        "stats": fox_client.stats_summary,
        "mesh": fox_client.mesh_status,
        "queue": fox_client.llm_queue,
    }
    for k, fn in calls.items():
        try:
            out[k] = fn() if k != "stats" else fn(24)
        except Exception as e:  # noqa: BLE001
            out[k] = {"_error": str(e)}
    return out


@app.get("/api/topology")
def topology():
    """One service→container→peer→model graph from the collected sources.

    Mesh, docker and LLM traffic are read independently upstream; this joins
    them so the Mesh tab shows infrastructure, not just a peer list.
    Partial sources yield a smaller graph, never a 500.
    """
    from iforensics import fox_client, topology as topo
    sources: dict = {}
    calls = {
        "mesh_status": fox_client.mesh_status,
        "service_model": lambda: fox_client.service_model(720),
        "docker_projects": fox_client.docker_projects,
        "logs_overview": fox_client.logs_overview,
        "router_managed": fox_client.router_managed,
    }
    for k, fn in calls.items():
        try:
            sources[k] = fn()
        except Exception as e:  # noqa: BLE001
            sources[k] = {"_error": f"{type(e).__name__}: {e}"}
    return topo.build(sources)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.environ.get("IF_PORT", "8211")))
    ap.add_argument("--host", default="0.0.0.0")
    args = ap.parse_args()
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
