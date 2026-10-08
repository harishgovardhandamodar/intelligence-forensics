#!/usr/bin/env python3
"""recon_client — the reconstruction-simulation client app (P14).

Standard library only. Runs on `axiom-dgx`; it drives the reconstruction
API on `axiom` (the server this repo's FastAPI dashboard serves).

    python -m recon_client serve          # local web UI  (default)
    python -m recon_client run            # terminal session + report
    python -m recon_client report         # full report for the last run
    python -m recon_client surfaces       # the eight surfaces + scenarios
    python -m recon_client inspect training
    python -m recon_client reset

Nothing here computes anything: every number it shows was produced by the
server's residual store. This app is transport + presentation.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from .api import DEFAULT_SERVER, FALLBACK_SERVER, ReconAPI, ServerError

HERE = Path(__file__).resolve().parent
SETTINGS_FILE = HERE / "settings.yaml"

# --------------------------------------------------------------------------- #
# settings: a tiny fixed-subset YAML reader (string/int/bool only)
# --------------------------------------------------------------------------- #

DEFAULTS = {"server": DEFAULT_SERVER, "port": 8311,
            "scenario": "stateless_coding", "n_turns": 48, "seed": 42}


def load_settings(path: Path = SETTINGS_FILE) -> dict:
    out = dict(DEFAULTS)
    if not path.exists():
        return out
    for raw in path.read_text().splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line or ":" not in line:
            continue
        key, val = (p.strip() for p in line.split(":", 1))
        val = val.strip('"\'')
        if key in ("n_turns", "seed", "port"):
            try:
                out[key] = int(val)
            except ValueError:
                pass
        elif key in out:
            out[key] = val
    return out


SETTINGS = load_settings()


def api_for(server: str | None = None) -> ReconAPI:
    return ReconAPI(server or SETTINGS.get("server") or DEFAULT_SERVER)


def best_server() -> str:
    """Prefer the tailnet address; fall back to localhost if it's dead."""
    a = api_for(SETTINGS.get("server"))
    try:
        a.health()
        return a.server
    except ServerError:
        pass
    if a.server != FALLBACK_SERVER:
        try:
            api_for(FALLBACK_SERVER).health()
            return FALLBACK_SERVER
        except ServerError:
            pass
    return a.server


# --------------------------------------------------------------------------- #
# terminal rendering
# --------------------------------------------------------------------------- #

def _bar(pct: float, width: int = 24) -> str:
    filled = int(round(pct * width))
    return "[" + "#" * filled + "." * (width - filled) + "]"


def _unwrap(data: dict, run_id: str | None = None) -> dict:
    """`load_run` returns {scenario: payload}; collapse to one payload."""
    if not isinstance(data, dict):
        return {}
    if "report" in data:
        return data
    if run_id and run_id in data:
        inner = data[run_id]
        if isinstance(inner, dict) and "report" in inner:
            return inner
    # load_run orders scenarios newest-first by file mtime
    for key in data:
        inner = data.get(key)
        if isinstance(inner, dict) and "report" in inner:
            return inner
    return data


def print_report(report: dict) -> None:
    nf = report.get("n_fields", 0)
    print(f"\nuser {report.get('user_id')}  ·  {report.get('n_turns')} turns  "
          f"·  {report.get('n_records')} residual records")
    print(report.get("bottom_line", ""))
    print("\n  surface          acc      recovered   text records")
    print("  " + "-" * 62)
    for s in report.get("surfaces", []):
        acc = s.get("accuracy", 0.0)
        link = ""
        if s.get("linkage"):
            l = s["linkage"]
            link = f"   linkage {l.get('linked_ratio', 0)} / {l.get('n_families', 0)}f"
        print(f"  {s.get('id',''):<16} {acc:<8.3f} "
              f"{s.get('recovered_fields',0)}/{nf}         "
              f"{s.get('text_records',0):<6}{link}")
    print("\n  cumulative: " + " · ".join(
        f"{c.get('added')} → {c.get('accuracy')}"
        for c in report.get("cumulative", [])))
    amp = report.get("amplification", {})
    print(f"\n  amplification: single {amp.get('single_query_accuracy')} "
          f"→ pooled {amp.get('pooled_accuracy')} "
          f"(Δ {amp.get('delta')}, {amp.get('turns_pooled')} requests)")
    print("  " + str(amp.get("verdict", "")))
    print("\n  fields:")
    for name, v in sorted((report.get("fields") or {}).items()):
        mark = "*" if v.get("recovered") else " "
        extra = "  (bare value present in a residual)" if v.get("direct_exposure") else ""
        print(f"   {mark} {name:<20} acc {v.get('accuracy')}{extra}")


def cmd_surfaces(api: ReconAPI) -> int:
    d = api.surfaces()
    print("surfaces:")
    for s in d.get("surfaces", []):
        tag = s.get("role", "")
        print(f"  {s.get('id',''):<16} [{tag}]  {s.get('title','')}")
        if s.get("retains"):
            print(f"      retains: {s['retains']}")
    print("\nscenarios:")
    for s in d.get("scenarios", []):
        print(f"  {s.get('id',''):<20} {s.get('title','')}")
        if s.get("description"):
            print(f"      {s['description']}")
    return 0


def cmd_run(api: ReconAPI, scenario: str, n: int, seed: int) -> int:
    res = api.run(scenario, n=n, seed=seed)
    print_report(res.get("report", {}))
    print(f"\nrun_id: {res.get('run_id')}   user: {res.get('user_id')}")
    return 0


def cmd_report(api: ReconAPI, run_id: str | None) -> int:
    if run_id:
        data = api.load_run(run_id)
    else:
        runs = api.runs().get("runs", [])
        if not runs:
            print("no persisted runs (recon_client run)", file=sys.stderr)
            return 1
        data = api.load_run(runs[0])
    payload = _unwrap(data, run_id)
    print_report(payload.get("report", payload))
    if payload.get("run_id"):
        print(f"\nrun_id: {payload['run_id']}   scenario: {payload.get('scenario')}")
    return 0


def cmd_inspect(api: ReconAPI, surface: str, user_id: str) -> int:
    if not user_id:
        runs = api.runs().get("runs", [])
        if not runs:
            print("no persisted runs", file=sys.stderr)
            return 1
        payload = _unwrap(api.load_run(runs[0]))
        user_id = payload.get("user_id", "")
    if not user_id:
        print("no user_id on the persisted run", file=sys.stderr)
        return 1
    d = api.residuals(user_id, surface=surface, limit=40)
    print(f"{d.get('total')} records · {d.get('with_text')} carry text "
          f"[{d.get('surface')}]")
    for r in d.get("records", []):
        text = r.get("text") or ""
        meta = {k: v for k, v in (r.get("meta") or {}).items()}
        print(f"  #{r.get('id')} turn {r.get('turn')} "
              f"[{r.get('surface')}/{r.get('kind')}] {text or json.dumps(meta)}")
    return 0


# --------------------------------------------------------------------------- #
# local web UI
# --------------------------------------------------------------------------- #

INDEX = """<!doctype html>
<html lang=en data-theme="dark"><meta charset=utf-8>
<meta name=viewport content="width=device-width,initial-scale=1">
<title>reconstruction · stateless insider</title>
<style>
:root{--bg:#0d1117;--bg2:#161b22;--bg3:#21262d;--fg:#e6edf3;--mut:#8b949e;
--acc:#58a6ff;--line:#30363d;--ok:#3fb950;--warn:#d29922;--red:#f85149}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
font:14px/1.5 ui-monospace,SFMono-Regular,Menlo,monospace}
header{padding:14px 18px;border-bottom:1px solid var(--line);display:flex;
gap:12px;align-items:center;flex-wrap:wrap}
header h1{font-size:15px;margin:0;font-weight:600}
main{padding:16px 18px;max-width:1100px}
.card{background:var(--bg2);border:1px solid var(--line);border-radius:8px;
padding:14px;margin-bottom:14px}
.row{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:6px 0}
h3{margin:0 0 6px;font-size:14px}h4{margin:12px 0 4px;font-size:11px;
text-transform:uppercase;letter-spacing:.06em;color:var(--mut)}
.mut{color:var(--mut)}code{background:var(--bg3);padding:1px 5px;border-radius:4px}
button,select,input{background:var(--bg3);color:var(--fg);
border:1px solid var(--line);border-radius:6px;padding:5px 10px;
font:inherit;cursor:pointer}
button:hover{border-color:var(--acc)}
input{width:64px}
.recon-row{display:flex;align-items:center;gap:8px;margin:3px 0}
.recon-id{min-width:132px}
.recon-bar{width:170px;height:9px;border-radius:5px;background:var(--bg3);
overflow:hidden;flex:none}
.recon-bar i{display:block;height:100%;
background:linear-gradient(90deg,var(--acc),#2ea8a0)}
pre{background:var(--bg);border:1px solid var(--line);border-radius:6px;
padding:10px;max-height:300px;overflow:auto;font-size:12px;white-space:pre-wrap}
.pill{display:inline-block;min-width:52px;text-align:center;padding:1px 8px;
border:1px solid currentColor;border-radius:999px;font-size:11px}
.pill.high{color:var(--ok)}.pill.low{color:var(--red)}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%}
.dot.ok{background:var(--ok)}.dot.warn{background:var(--warn)}
.dot.err{background:var(--red)}
#status{font-size:12px;color:var(--mut)}
</style>
<h1>reconstruction · stateless insider</h1>
<span id=status>connecting…</span></header>
<main>
<div class=card>
  <div class=row><span class=mut>server</span>
    <input id=server style="width:230px"><button id=b-connect>connect</button>
    <span id=health class=mut></span></div>
  <div class=row><span class=mut>scenario</span><select id=scenario></select>
    <span class=mut>turns</span><input id=n value=48>
    <button id=b-run>run session</button>
    <button id=b-reset>reset residuals</button>
    <span id=msg class=mut></span></div>
</div>
<div class=card id=report-card hidden>
  <h3 id=rep-title>report</h3>
  <div class=mut id=bottom></div>
  <h4>each surface alone</h4><div id=bars></div>
  <h4>cumulative (growing set of surfaces)</h4><div class=mut id=cum></div>
  <h4>repeated near-query amplification</h4><div class=mut id=amp></div>
  <h4>recovered fields</h4><div id=fields></div>
</div>
<div class=card>
  <div class=row><span class=mut>residual inspector</span>
    <select id=surface></select><button id=b-inspect>inspect</button>
    <span id=isum class=mut></span></div>
  <pre id=ivals>run a session first…</pre>
</div>
</main>
<script>
const $=id=>document.getElementById(id);
const esc=s=>String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
let SERVER=localStorage.getItem('recon_server')||'';
async function call(path,opts){
  const r=await fetch(SERVER+path,opts);
  if(!r.ok){let t='';try{t=await r.text()}catch(e){}
    throw new Error(r.status+' '+path+' '+t.slice(0,200));}
  return r.json();
}
async function connect(){
  SERVER=($('server').value||'').trim().replace(/\\/$/,'');
  localStorage.setItem('recon_server',SERVER);
  try{
    const h=await call('/health');$('health').textContent='ok · '+JSON.stringify(h).slice(0,80);
    const d=await call('/api/recon/surfaces');
    $('scenario').innerHTML=(d.scenarios||[]).map(s=>`<option value="${esc(s.id)}">${esc(s.title)}</option>`).join('');
    $('surface').innerHTML='<option value=all>all surfaces</option>'+
      (d.all_ids||[]).map(i=>`<option value="${esc(i)}">${esc(i)}</option>`).join('');
    $('status').textContent='connected to '+(SERVER||location.origin);
    $('status').innerHTML='<span class="dot ok"></span> connected to '+(SERVER||location.origin);
    const r=await call('/api/recon/runs').catch(()=>({runs:[]}));
    $('msg').textContent=r.runs&&r.runs.length?('latest run: '+r.runs[0]):'';
  }catch(e){$('status').innerHTML='<span class="dot err"></span> '+esc(e.message);}
}
async function run(){
  $('msg').textContent='running…';
  try{
    const d=await call('/api/recon/run',{method:'POST',
      headers:{'Content-Type':'application/json'},
      body:JSON.stringify({scenario:$('scenario').value,
        n:parseInt($('n').value,10)||48,seed:42})});
    render(d.report);$('msg').textContent=d.run_id+' · '+d.n_turns+' turns';
    await inspect(d.report&&d.report.user_id);
  }catch(e){$('msg').textContent='failed: '+e.message;}
}
function render(r){
  if(!r)return;
  $('report-card').hidden=false;
  $('rep-title').textContent='report · '+r.user_id;
  $('bottom').textContent=r.bottom_line||'';
  const nf=r.n_fields||0;
  $('bars').innerHTML=(r.surfaces||[]).map(s=>{
    const pct=Math.round((s.accuracy||0)*100);
    const l=s.linkage?` · linkage ${s.linkage.linked_ratio} (${s.linkage.n_families} families)`:'';
    return `<div class=recon-row><span class=recon-id>${esc(s.id)}</span>
      <span class=recon-bar><i style="width:${pct}%"></i></span><b>${esc(s.accuracy)}</b>
      <span class=mut>${esc(s.recovered_fields)}/${nf} fields · ${esc(s.text_records)} text records${l}</span></div>`;
  }).join('');
  $('cum').innerHTML=(r.cumulative||[]).map(c=>esc(c.added)+' → '+esc(c.accuracy)).join(' · ');
  const a=r.amplification||{};
  $('amp').textContent=`single request ${a.single_query_accuracy} → pooled over ${a.turns_pooled} requests ${a.pooled_accuracy} (Δ ${a.delta}) — ${a.verdict||''}`;
  $('fields').innerHTML=Object.entries(r.fields||{}).map(([f,v])=>
    `<div><span class="pill ${v.recovered?'high':'low'}">${v.recovered?'high':'low'}</span>
     <code>${esc(f)}</code> <span class=mut>${esc(v.accuracy)}${v.direct_exposure?' · bare value present in a residual':''}</span></div>`).join('');
}
async function inspect(user_id){
  try{
    let uid=user_id;
    if(!uid){
      const r=await call('/api/recon/runs');
      if(!r.runs||!r.runs.length)return;
      const d=await call('/api/recon/run?run_id='+encodeURIComponent(r.runs[0]));
      const k=Object.keys(d)[0];uid=(d[k]&&d[k].report&&d[k].report.user_id)||'';
    }
    const d=await call('/api/recon/residuals?user_id='+encodeURIComponent(uid)+
      '&surface='+encodeURIComponent($('surface').value)+'&limit=60');
    $('isum').textContent=d.total+' records · '+d.with_text+' carry text';
    $('ivals').textContent=(d.records||[]).map(r=>
      `#${r.id} turn ${r.turn} [${r.surface}/${r.kind}] ${r.text||JSON.stringify(r.meta)}`).join('\\n')||'nothing retained';
  }catch(e){$('ivals').textContent='inspect failed: '+e.message;}
}
async function reset(){
  try{await call('/api/recon/reset',{method:'POST',body:'{}'});
    $('report-card').hidden=true;
    $('ivals').textContent='pick a surface…';$('msg').textContent='residual stores cleared';
  }catch(e){$('msg').textContent='reset failed: '+e.message;}
}
$('b-connect').onclick=connect;
$('b-run').onclick=run;
$('b-inspect').onclick=()=>inspect();
$('b-reset').onclick=reset;
(async()=>{
  try{const c=await fetch('/config').then(r=>r.json());
    if(!SERVER)SERVER=(c.settings&&c.settings.server)||'';
  }catch(e){}
  $('server').value=SERVER;
  connect();
})();
</script></html>"""


class Handler(BaseHTTPRequestHandler):
    server_version = "recon-client/1.0"

    def log_message(self, fmt, *args):  # keep the terminal quiet
        pass

    # -- helpers ---------------------------------------------------------- #

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, code: int, obj) -> None:
        self._send(code, json.dumps(obj).encode(), "application/json")

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n) or b"{}") if n else {}
        except (ValueError, json.JSONDecodeError):
            return {}

    def _q(self):
        return parse_qs(urlparse(self.path).query)

    def _first(self, key: str, default: str = "") -> str:
        v = self._q().get(key)
        return v[0] if v else default

    def _api(self) -> ReconAPI:
        return api_for(SETTINGS.get("server"))

    # -- GET -------------------------------------------------------------- #

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            self._send(200, INDEX.encode(), "text/html; charset=utf-8")
            return
        if path == "/config":
            return self._json(200, {"settings": SETTINGS})
        if path == "/health":
            try:
                return self._json(200, self._api().health())
            except ServerError as e:
                return self._json(502, {"error": str(e)})
        if path == "/api/state":
            api = self._api()
            try:
                health = api.health(); err = None
            except ServerError as e:
                health, err = None, str(e)
            try:
                cat = api.surfaces()
            except ServerError as e:
                cat, err = {}, str(e)
            try:
                runs = api.runs().get("runs", [])
            except ServerError:
                runs = []
            self._json(200, {"settings": SETTINGS, "server": api.server,
                             "health": health, "error": err,
                             "surfaces": cat.get("surfaces", []),
                             "scenarios": cat.get("scenarios", []),
                             "all_ids": cat.get("all_ids", []),
                             "runs": runs})
            return
        api = self._api()
        try:
            if path == "/api/recon/surfaces":
                return self._json(200, api.surfaces())
            if path == "/api/recon/runs":
                return self._json(200, api.runs())
            if path == "/api/recon/run":
                return self._json(200, api.load_run(self._first("run_id")))
            if path == "/api/recon/report":
                return self._json(200, api.report(self._first("user_id")))
            if path == "/api/recon/residuals":
                return self._json(200, api.residuals(
                    self._first("user_id"), surface=self._first("surface"),
                    limit=int(self._first("limit", "100") or 100)))
        except ServerError as e:
            return self._json(502, {"error": str(e)})
        self._json(404, {"error": "no such route"})

    # -- POST ------------------------------------------------------------- #

    def do_POST(self):
        path = urlparse(self.path).path
        body = self._body()
        if path == "/api/settings":
            if body.get("server"):
                SETTINGS["server"] = str(body["server"]).rstrip("/")
            return self._json(200, {"settings": SETTINGS})
        api = self._api()
        try:
            if path == "/api/recon/run":
                return self._json(200, api.run(
                    body.get("scenario", SETTINGS["scenario"]),
                    n=int(body.get("n") or SETTINGS["n_turns"]),
                    seed=int(body.get("seed") or SETTINGS["seed"])))
            if path == "/api/recon/begin":
                return self._json(200, api.begin(
                    body.get("user_id", ""), body.get("truth", {}),
                    body.get("scenario", "")))
            if path == "/api/recon/ingest":
                return self._json(200, api.ingest(
                    body.get("prompt", ""), body.get("metadata", {}),
                    mask=body.get("mask", ""), step=int(body.get("step") or 0),
                    response=body.get("response", "")))
            if path == "/api/recon/reconstruct":
                return self._json(200, api.reconstruct(
                    body.get("user_id", ""), body.get("surfaces"),
                    amplify=bool(body.get("amplify", True))))
            if path == "/api/recon/reset":
                return self._json(200, api.reset())
        except ServerError as e:
            return self._json(502, {"error": str(e)})
        self._json(404, {"error": "no such route"})


def serve(host: str = "127.0.0.1", port: int | None = None) -> int:
    port = int(port or SETTINGS.get("port") or 8311)
    SETTINGS["server"] = best_server()
    httpd = ThreadingHTTPServer((host, port), Handler)
    worker = threading.Thread(target=httpd.serve_forever, daemon=True)
    worker.start()
    print(f"reconstruction client UI  →  http://{host}:{port}")
    print(f"driving server            →  {SETTINGS['server']}")
    print("ctrl-c to stop")
    stop = threading.Event()
    try:
        while worker.is_alive():
            stop.wait(1.0)
    except KeyboardInterrupt:
        print("\nstopping")
    finally:
        httpd.shutdown()
        httpd.server_close()
    return 0


# --------------------------------------------------------------------------- #
# entry point
# --------------------------------------------------------------------------- #

def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="recon_client",
                                description="stateless-inference reconstruction "
                                            "client (P14)")
    p.add_argument("--server", help="override the axiom server base URL")
    sub = p.add_subparsers(dest="cmd")
    s = sub.add_parser("serve", help="local web UI (default)")
    s.add_argument("--host", default="127.0.0.1")
    s.add_argument("--port", type=int, default=None)
    r = sub.add_parser("run", help="execute a scenario server-side")
    r.add_argument("--scenario", default=None)
    r.add_argument("--n", type=int, default=None)
    r.add_argument("--seed", type=int, default=None)
    rp = sub.add_parser("report", help="print the latest persisted report")
    rp.add_argument("--run-id", default=None)
    sub.add_parser("surfaces", help="print the eight surfaces + scenarios")
    i = sub.add_parser("inspect", help="dump raw residual records")
    i.add_argument("surface", nargs="?", default="all")
    i.add_argument("--user", default="")
    sub.add_parser("reset", help="clear every residual store")
    sub.add_parser("health", help="ping the server")
    args = p.parse_args(argv)

    if args.server:
        SETTINGS["server"] = args.server.rstrip("/")
    api = api_for()
    cmd = args.cmd or "serve"
    try:
        if cmd == "serve":
            return serve(getattr(args, "host", "127.0.0.1"),
                         getattr(args, "port", None))
        if cmd == "health":
            print(json.dumps(api.health(), indent=2))
            return 0
        if cmd == "surfaces":
            return cmd_surfaces(api)
        if cmd == "run":
            return cmd_run(api,
                           args.scenario or SETTINGS["scenario"],
                           args.n or SETTINGS["n_turns"],
                           args.seed or SETTINGS["seed"])
        if cmd == "report":
            return cmd_report(api, getattr(args, "run_id", None))
        if cmd == "inspect":
            return cmd_inspect(api, args.surface, args.user)
        if cmd == "reset":
            print(json.dumps(api.reset()))
            return 0
    except ServerError as e:
        print(f"error: {e}", file=sys.stderr)
        print("is the axiom dashboard up? (server: "
              f"{SETTINGS.get('server')})", file=sys.stderr)
        return 1
    p.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
