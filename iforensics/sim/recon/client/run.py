"""`python -m iforensics.sim.recon.client.run` — stdlib CLI over /api/recon/*.

Transport + presentation only: every number is computed server-side and
printed, never scored here. Subcommands: surfaces, run, report, inspect,
coserve, reset, ledger-verify.
"""
from __future__ import annotations

import argparse
import json
import sys

from ..api.routes import call

DEFAULT_SERVER = "http://localhost:8211"


def _brief(report: dict) -> str:
    amp = report.get("amplification", {})
    return (f"pooled={report.get('mean_accuracy')} "
            f"recovered={report.get('recovered')}/{report.get('n_fields')} "
            f"records={report.get('n_records')} turns={report.get('n_turns')} "
            f"ampΔ={amp.get('delta')}")


def cmd_surfaces(api, _args) -> int:
    d = api("surfaces")
    for s in d.get("surfaces", []):
        print(f"{s['id']:>16}  {s.get('title', '')}")
    print(f"{len(d.get('scenarios', []))} scenarios")
    return 0


def cmd_run(api, args) -> int:
    d = api("run", {"scenario": args.scenario, "n": args.n, "seed": args.seed})
    if d.get("http_error"):
        print(f"error: {d}", file=sys.stderr)
        return 1
    print(f"{d['run_id']} · {d['scenario']} · {d['user_id']}")
    print(_brief(d["report"]))
    print(json.dumps({"run_id": d["run_id"], "user_id": d["user_id"]}))
    return 0


def cmd_report(api, args) -> int:
    d = api("report", params={"user_id": args.user})
    if d.get("http_error"):
        print(f"error: {d}", file=sys.stderr)
        return 1
    print(_brief(d))
    return 0


def cmd_inspect(api, args) -> int:
    d = api("residuals", params={"user_id": args.user,
                                 "surface": args.surface or "",
                                 "limit": args.limit})
    if d.get("http_error"):
        print(f"error: {d}", file=sys.stderr)
        return 1
    print(f"{d['total']} records · {d['with_text']} carry text "
          f"· surface {d['surface']}")
    for r in d["records"][: args.limit]:
        print(f"  t{r['turn']:>3} {r['surface']:<14} {r['kind']:<14} "
              f"{(r['text'] or '')[:100]}")
    return 0


def cmd_coserve(api, args) -> int:
    d = api("coserve", {"limit": args.limit, "dry_run": args.dry_run})
    if d.get("http_error"):
        print(f"error: {d}", file=sys.stderr)
        return 1
    print(f"ingested={d.get('ingested')} skipped={d.get('skipped')} "
          f"services={d.get('services')} retained={d.get('retained')}")
    return 0


def cmd_reset(api, _args) -> int:
    print(json.dumps(api("reset", {})))
    return 0


def cmd_ledger_verify(args) -> int:
    from ..ledger.chain import verify
    print(json.dumps(verify(args.run_id), indent=1))
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="recon",
                                description="insider-recon framework CLI")
    p.add_argument("--server", default=DEFAULT_SERVER)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("surfaces")
    r = sub.add_parser("run")
    r.add_argument("--scenario", default="stateless_coding")
    r.add_argument("--n", type=int, default=48)
    r.add_argument("--seed", type=int, default=42)
    rp = sub.add_parser("report")
    rp.add_argument("--user", default="")
    i = sub.add_parser("inspect")
    i.add_argument("--user", default="")
    i.add_argument("--surface", default="")
    i.add_argument("--limit", type=int, default=20)
    c = sub.add_parser("coserve")
    c.add_argument("--limit", type=int, default=500)
    c.add_argument("--dry-run", action="store_true")
    sub.add_parser("reset")
    lv = sub.add_parser("ledger-verify")
    lv.add_argument("run_id")
    args = p.parse_args(argv)
    api = lambda name, payload=None, params=None: call(  # noqa: E731
        args.server, name, payload, params)
    return {"surfaces": cmd_surfaces, "run": cmd_run, "report": cmd_report,
            "inspect": cmd_inspect, "coserve": cmd_coserve,
            "reset": cmd_reset}[args.cmd](api, args) \
        if args.cmd != "ledger-verify" else cmd_ledger_verify(args)


if __name__ == "__main__":
    raise SystemExit(main())
