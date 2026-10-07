#!/usr/bin/env python3
"""CLI: investigate + build + agentic runs + dashboard.

Usage:
  python cli.py investigate [--hours 168] [--limit 5000] [--report evidence/INVESTIGATION.md]
  python cli.py build [--only quai-radar] [--limit 5000]
  python cli.py fingerprint --service quai-radar [--limit 500]
  python cli.py agent-run [--quick] [--model qwen3.8:27b] [--only quai-radar] [--limit 5000]
  python cli.py dashboard [--port 8211]
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from iforensics import config, fox_client, store, infer, reconstruct, report as report_mod


def cmd_investigate(args) -> int:
    print(f"[*] fox -> {config.FOX_URL}  db={config.find_fox_db()}")
    api_path, api = store.snapshot_api(hours=args.hours, req_limit=args.req_limit)
    print(f"[*] api dump -> {api_path}")
    src, db_path = store.snapshot_db()
    print(f"[*] db copy {src} -> {db_path}")
    errors = [f"{k}: {v.get('_error')}" for k, v in api.items() if isinstance(v, dict) and "_error" in v]

    rows: list[dict] = []
    if db_path:
        rows = store.load_requests(db_path, limit=args.limit)
        print(f"[*] loaded {len(rows)} rows from DB copy")
    if not rows and isinstance(api.get("llm_requests"), dict):
        rows = api["llm_requests"].get("requests", []) or []
        print(f"[*] using {len(rows)} rows from API fallback")
    if not rows:
        print("[!] no rows available (DB missing and API failed)", file=sys.stderr)
        return 2
    inv = infer.investigate_all(rows)
    mesh = api.get("mesh_status") if isinstance(api.get("mesh_status"), dict) else None
    md = report_mod.render(inv, mesh=mesh, api_errors=errors)
    rpath = args.report or os.path.join(config.EVIDENCE_DIR, "INVESTIGATION.md")
    report_mod.write(md, rpath)
    print(f"[*] {inv['n_requests']} reqs / {inv['n_services']} services")
    for svc, p in inv["services"].items():
        print(f"  - {svc}: {p['requests']} reqs | {p['project']}")
    print(f"[*] report -> {rpath}")
    return 0


def cmd_build(args) -> int:
    src = config.find_fox_db()
    db_path = None
    if src:
        _, db_path = store.snapshot_db()
    # reuse newest evidence DB if fresh snapshot impossible
    if not db_path:
        cands = sorted((f for f in os.listdir(config.EVIDENCE_DIR) if f.endswith(".db")) if os.path.exists(config.EVIDENCE_DIR) else [])
        if cands:
            db_path = os.path.join(config.EVIDENCE_DIR, cands[-1])
    if not db_path:
        print("[!] no DB available", file=sys.stderr)
        return 2
    rows = store.load_requests(db_path, limit=args.limit)
    inv = infer.investigate_all(rows)
    only = args.only.split(",") if args.only else None
    made = reconstruct.build_all(inv, only=only)
    for m in made:
        print(f"[+] reconstructed -> {m}")
    return 0


def cmd_fingerprint(args) -> int:
    _, db_path = store.snapshot_db()
    rows = store.load_requests(db_path, limit=args.limit)
    rows = [r for r in rows if r.get("service") == args.service] if args.service else rows
    from iforensics import fingerprints as fp
    prompts = [r.get("prompt") or "" for r in rows]
    print(json.dumps(fp.fingerprint_service(prompts), indent=1)[:4000])
    return 0


def _latest_db_path() -> str | None:
    import glob as _glob
    src = config.find_fox_db()
    if src:
        _, db_path = store.snapshot_db()
        if db_path:
            return db_path
    cands = sorted(_glob.glob(os.path.join(config.EVIDENCE_DIR, "fox_services_*.db")))
    return cands[-1] if cands else None


def cmd_agent_run(args) -> int:
    from iforensics import agents as ag, ollama_client
    model = args.model or ollama_client.MODEL
    print(f"[*] ollama -> {ollama_client.OLLAMA_URL} model={model}")
    ping = ollama_client.ping(model)
    print(f"[*] ping: {ping}")
    if not ping.get("ok"):
        print("[!] model not reachable, aborting", file=sys.stderr)
        return 2
    db_path = _latest_db_path()
    if not db_path:
        print("[!] no DB available", file=sys.stderr)
        return 2
    rows = store.load_requests(db_path, limit=args.limit)
    only = args.only.split(",") if args.only else None
    res = ag.run_deep_investigation(rows, model=model, quick=args.quick, only=only)
    print(f"[+] run {res['run_id']} in {res['elapsed_s']}s -> {res['run_dir']}")
    for s in res.get("services", []):
        parsed = ((res.get("agents", {}).get("profilers", {}).get(s) or {}).get("parsed") or {})
        print(f"  - {s}: {parsed.get('project') or parsed.get('what_building') or '?'}")
    if res.get("errors"):
        print("[!] errors:", *res["errors"], sep="\n    ", file=sys.stderr)
    return 0


def cmd_dashboard(args) -> int:
    import sys as _sys
    _sys.argv = ["dashboard", "--port", str(args.port)]
    from dashboard import main as dash_main
    return dash_main()


def cmd_live_tail(args) -> int:
    import datetime
    import time as _time
    from iforensics import live as live_mod
    tap = live_mod.LiveTap(interval_s=args.interval)
    tap.start()
    from iforensics import config as _cfg
    print(f"[*] tap attached to {_cfg.FOX_URL} "
          f"(interval {args.interval}s, Ctrl-C to stop)", flush=True)
    shown = 0
    try:
        while True:
            _time.sleep(1.0)
            evs = list(tap.events)[shown:]
            shown += len(evs)
            for e in evs:
                if args.service and e["service"] != args.service:
                    continue
                ts = datetime.datetime.fromtimestamp(e["t"]).strftime("%H:%M:%S")
                print(f"{ts} {e['dir'].upper():3s} {e['service'][:24]:24s} "
                      f"{(e['model'] or '')[:18]:18s} "
                      f"{e['prompt_tokens'] + e['completion_tokens']:>5d}tok "
                      f"{(e['prompt_head'] or '')[:100]}", flush=True)
    except KeyboardInterrupt:
        print("\n[*] stopped")
    finally:
        tap.stop()
    return 0


def cmd_progression(args) -> int:
    from iforensics import progression as prog, score as scoring
    db_path = _latest_db_path()
    if not db_path:
        print("[!] no DB available", file=sys.stderr)
        return 2
    rows = store.load_requests(db_path, limit=args.limit)
    res = prog.progression(args.service, rows, n=args.n, mode=args.mode)
    if not res.get("steps"):
        print(f"[!] no queries for service {args.service!r}", file=sys.stderr)
        return 2
    res = scoring.attach_scores(res)
    print(f"{args.service} [{args.mode}] converged={res['converged']}")
    for st in res["steps"]:
        d = st.get("delta", {})
        flag = "FLIP" if d.get("project_changed") else "stable"
        print(f"  step {st['step']}: {st['requests']:>5} queries | score "
              f"{st['score']['score']} ({st['score']['grade']}) | vibe "
              f"{st['vibe']['vibe']} {st['vibe']['label']} | {st['project']} [{flag}]")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(prog="iforensics")
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("investigate")
    a.add_argument("--hours", type=int, default=720)
    a.add_argument("--limit", type=int, default=5000)
    a.add_argument("--req-limit", type=int, default=2000)
    a.add_argument("--report", default="")
    a.set_defaults(fn=cmd_investigate)
    b = sub.add_parser("build")
    b.add_argument("--only", default="")
    b.add_argument("--limit", type=int, default=5000)
    b.set_defaults(fn=cmd_build)
    c = sub.add_parser("fingerprint")
    c.add_argument("--service", default="")
    c.add_argument("--limit", type=int, default=500)
    c.set_defaults(fn=cmd_fingerprint)
    d = sub.add_parser("agent-run",
                       help="LLM agentic deep-investigation via local Ollama (qwen3.8:27b)")
    d.add_argument("--quick", action="store_true", default=False,
                   help="top-3 services only, skip critic stage (faster)")
    d.add_argument("--model", default="",
                   help="ollama model (default $IF_MODEL or qwen3.8:27b)")
    d.add_argument("--only", default="")
    d.add_argument("--limit", type=int, default=5000)
    d.set_defaults(fn=cmd_agent_run)
    e = sub.add_parser("dashboard", help="serve the investigation dashboard")
    e.add_argument("--port", type=int, default=int(os.environ.get("IF_PORT", "8211")))
    e.set_defaults(fn=cmd_dashboard)
    f = sub.add_parser("progression",
                       help="partial/progressive reconstruction of one service over time")
    f.add_argument("--service", required=True)
    f.add_argument("--n", type=int, default=5)
    f.add_argument("--mode", default="cumulative", choices=["cumulative", "window"])
    f.add_argument("--limit", type=int, default=5000)
    f.set_defaults(fn=cmd_progression)
    g = sub.add_parser("live-tail",
                       help="sniff fox :8210 live (queue IN, completed OUT, model SYS) to stdout")
    g.add_argument("--interval", type=float, default=5.0)
    g.add_argument("--service", default="")
    g.set_defaults(fn=cmd_live_tail)
    args = ap.parse_args()
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
