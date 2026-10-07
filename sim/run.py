#!/usr/bin/env python3
"""Simulation client: drives scenarios against the in-app Sim API (P8.3).

Flow per scenario: begin (register truth) -> ingest turns -> progressive
attack -> report -> membership probes (true value vs fresh randomness).
Stdlib only (urllib); the server does all embedding/attack math.

Usage:
  python sim/run.py --scenario chatbot_health [--n 60 --seed 42]
  python sim/run.py --all [--server http://localhost:8211 --out sim/results]
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

DEF_SERVER = "http://localhost:8211"


def _req(server: str, method: str, path: str, body: dict | None = None):
    data = json.dumps(body or {}).encode() if body is not None or method != "GET" else None
    url = server.rstrip("/") + path
    if method == "GET" and body:
        url += "?" + urllib.parse.urlencode(body)
        data = None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def _post(server: str, path: str, body: dict):
    return _req(server, "POST", path, body)


def run_scenario(server: str, name: str, n: int, seed: int, threshold: float,
                 out_dir: str) -> dict:
    from sim.scenarios import chatbot_financial, chatbot_health, coding_api_keys, coding_secrets
    builders = {"chatbot_health": chatbot_health.build,
                "chatbot_financial": chatbot_financial.build,
                "coding_api_keys": coding_api_keys.build,
                "coding_secrets": coding_secrets.build}
    if name not in builders:
        raise ValueError(f"unknown scenario: {name!r}")
    sc = builders[name](seed=seed, n=n)
    user_id, truth = sc["user_id"], sc["truth"]
    print(f"[*] {name}: {len(sc['turns'])} turns, user={user_id}")
    _post(server, "/api/sim/begin", {"user_id": user_id, "truth": truth,
                                     "scenario": name})
    for i, t in enumerate(sc["turns"]):
        _post(server, "/api/sim/ingest",
              {"prompt": t["prompt"], "mask": t["mask"], "step": t["step"],
               "metadata": t["metadata"]})
        if (i + 1) % 20 == 0:
            print(f"    ingested {i + 1}/{len(sc['turns'])}")
    attack = _post(server, "/api/sim/attack",
                   {"kind": "progressive", "user_id": user_id,
                    "threshold": threshold})
    report = _req(server, "GET", "/api/sim/report", {"user_id": user_id})
    probes = {}
    for field, value in truth.items():
        hit = _post(server, "/api/sim/attack",
                    {"kind": "membership", "user_id": user_id, "value": value})
        miss = _post(server, "/api/sim/attack",
                     {"kind": "membership", "user_id": user_id,
                      "value": "never-logged-random-value-zzz-999"})
        probes[field] = {"true_score": hit["max_score"],
                         "fresh_score": miss["max_score"],
                         "likely_member": hit["likely_member"]}
    result = {"scenario": name, "user_id": user_id, "n_turns": len(sc["turns"]),
              "attack": {"n_clusters": attack["n_clusters"],
                         "mean_cohesion": attack["mean_cohesion"]},
              "report": report, "membership": probes}
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, f"{name}.json"), "w") as f:
        json.dump(result, f, indent=1)
    r = report
    print(f"[+] {name}: {r['recovered']}/{r['n_fields']} fields recovered, "
          f"mean accuracy {r['mean_accuracy']}")
    for field, fr in r["fields"].items():
        print(f"    {field}: {fr['accuracy']} "
              f"({'RECOVERED' if fr['recovered'] else 'partial'})")
    return result


def main() -> int:
    pre = argparse.ArgumentParser(add_help=False)
    pre.add_argument("--settings", default="")
    known, _ = pre.parse_known_args()
    cfg: dict = {}
    if known.settings:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
        from sim.config import load_settings
        cfg = load_settings(known.settings)
    ap = argparse.ArgumentParser(prog="sim-client")
    ap.add_argument("--server", default=cfg.get("server", DEF_SERVER))
    ap.add_argument("--scenario", default="")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--n", type=int, default=cfg.get("n_queries", 60))
    ap.add_argument("--seed", type=int, default=cfg.get("seed", 42))
    ap.add_argument("--threshold", type=float, default=cfg.get("threshold", 0.6))
    ap.add_argument("--out", default="sim/results")
    ap.add_argument("--settings", default=known.settings)
    args = ap.parse_args()
    names = list(cfg.get("scenarios") or []) if args.all else []
    if not names:
        names = ["chatbot_health", "chatbot_financial", "coding_api_keys",
                 "coding_secrets"] if args.all else [args.scenario or "chatbot_health"]
    try:
        for name in names:
            run_scenario(args.server, name, args.n, args.seed,
                         args.threshold, args.out)
    except Exception as e:  # noqa: BLE001 — client reports, never tracebacks
        print(f"[!] {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
