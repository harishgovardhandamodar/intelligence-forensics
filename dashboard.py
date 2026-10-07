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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from iforensics import config, store, infer, agents as ag, ollama_client

app = FastAPI(title="Intelligence Forensics Dashboard", version="0.2.0")
app.mount("/static", StaticFiles(directory=os.path.join(config.BASE_DIR, "static")), name="static")

# Bump on every deploy — shown in the header so cached pages are detectable.
APP_VERSION = "0.5.0-live"

PAGE = """<!doctype html><html><head><meta charset=utf-8><meta name=viewport content="width=device-width,initial-scale=1">
<title>Intelligence Forensics</title>
<link rel="stylesheet" href="/static/app.css"></head><body>
<header><h1>&#x1f575; Intelligence Forensics</h1><span class=sub id=hdr>loading&hellip;</span></header>
<nav id=tabs>
<button data-t=overview class=on>Overview</button><button data-t=live>Live tap</button><button data-t=services>Services</button><button data-t=recon>Reconstructions</button><button data-t=agents>Agentic runs</button><button data-t=mesh>Mesh</button><button data-t=evidence>Evidence</button><button data-t=design>Design</button>
</nav><main>
<section id=s-overview class=on><div class=grid id=stats></div><div class=card><h3>Latest brief</h3><pre id=brief>loading&hellip;</pre></div>
<div class=card><h3>Run investigation</h3><div class=row>
<button class=act id=b-inv>Re-run heuristic investigation</button>
<button class=act id=b-agent>Launch agentic run (Qwen 3.8-27B)</button>
<label class=mut><input type=checkbox id=opt-quick checked> quick (top-3, no critic)</label>
<span class=mut id=runmsg></span></div></div></section>
<section id=s-services><div class=card><table id=t-svc><thead><tr><th>service</th><th>reqs</th><th>tokens</th><th>models</th><th>inferred build</th><th>score / vibe</th></tr></thead><tbody></tbody></table></div></section>
<section id=s-live><div class=card><h3>Tap <span class=mut id=live-state style="font-weight:normal"></span></h3>
<div class=row><button class=act id=b-live-start>Start tap</button><button class=act id=b-live-stop>Stop</button>
<label class=mut>every <input id=inp-live-int type=number value=5 min=1 max=60 style="width:56px">s</label>
<span class=mut>API-level sniff of fox :8210 — queue IN, completed OUT, model load SYS. Raw pcap needs the <code>pcap</code> compose profile (see README).</span></div></div>
<div class=card><h3>Rates <span class=mut style="font-weight:normal">— live window</span></h3><table id=t-rates><thead><tr><th>service</th><th>req</th><th>tokens</th><th>req/min</th><th>tok/min</th></tr></thead><tbody><tr><td class=mut colspan=5>tap not running</td></tr></tbody></table></div>
<div class=card><h3>Live reconstruction <span class=mut style="font-weight:normal">— recent history + live rows since tap started</span></h3>
<div class=row><select id=sel-live></select><select id=sel-lmode><option value=cumulative>cumulative</option><option value=window>window</option></select>
<button class=act id=b-live-recon>Reconstruct live</button><span class=mut id=live-recon-msg></span></div>
<table id=t-liveprog><thead><tr><th>step</th><th>score</th><th>queries</th><th>inferred build</th><th>Δ vs prev</th></tr></thead><tbody></tbody></table></div>
<div class=card><h3>Feed <span class=mut style="font-weight:normal">— newest first, auto-refresh</span></h3><table id=t-feed><thead><tr><th>time</th><th>dir</th><th>service</th><th>model</th><th>detail</th></tr></thead><tbody><tr><td class=mut colspan=5>tap not running</td></tr></tbody></table></div></section>
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
<div class=card><h3>Brief</h3><pre id=run-brief>click a run&hellip;</pre></div></section>
<section id=s-mesh><div class=card><table id=t-mesh><thead><tr><th>node</th><th>online</th><th>hw</th><th>llm/1h</th><th>services</th></tr></thead><tbody></tbody></table></div></section>
<section id=s-evidence><div class=card><table id=t-ev><thead><tr><th>file</th><th>size</th></tr></thead><tbody></tbody></table></div></section>
<section id=s-design><div class=row><div class=card style="min-width:230px"><h3>Documents</h3><div id=design-rail class=mut>loading&hellip;</div></div>
<div class=card style="flex:1"><h3 id=design-title>Design &amp; architecture</h3><div class=mut id=design-meta></div><div id=design-doc class=mut>pick a document&hellip;</div></div></div></section>
</main>
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


@app.get("/api/runs")
def runs():
    return ag.list_runs()


@app.get("/api/runs/{run_id}")
def run_detail(run_id: str):
    m = ag.load_run(run_id)
    if not m:
        raise HTTPException(404, "unknown run")
    return m


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
    key = ag.launch_background(_service_rows, model=model,
                               quick=req.quick, only=req.only)
    return {"launched": key, "model": model, "quick": req.quick}


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
