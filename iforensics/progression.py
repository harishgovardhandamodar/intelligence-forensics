"""Progressive / partial reconstructions from Fox-server query logs.

A full reconstruction uses every observed query at once. This module instead
slices ONE service's queries (ordered by time, equal-count chunks) and
re-profiles each slice:

- mode=cumulative — step k sees queries [0..k]: "what could we reconstruct
  after seeing the first 20%? 40%? ..." (progressive confidence growth)
- mode=window — step k sees only its own slice: "what did this period alone
  reveal?" (partial views, drift detection)

Deltas between consecutive steps (label flips, new pipeline stages, template
growth) show whether the inferred codebase is converging or still shifting.
"""
import datetime

from . import infer as infer_mod


def _ts(t: float) -> str:
    try:
        return datetime.datetime.fromtimestamp(t).strftime("%m-%d %H:%M")
    except Exception:  # noqa: BLE001
        return "?"


def chunk_rows(rows: list[dict], n: int) -> list[list[dict]]:
    """Oldest-first, equal-count chunks (robust to bursty traffic)."""
    ordered = sorted((r for r in rows if r.get("ts")), key=lambda r: r["ts"])
    n = max(2, min(12, n))
    if len(ordered) < n * 2:  # too few rows — fewer, bigger chunks
        n = max(2, len(ordered) // 2)
    if n < 2 or not ordered:
        return [ordered] if ordered else []
    size = len(ordered) / n
    return [ordered[int(i * size):int((i + 1) * size)] for i in range(n)]


def progression(service: str, rows: list[dict], n: int = 5,
                mode: str = "cumulative") -> dict:
    svc_rows = [r for r in rows if (r.get("service") or "") == service]
    if not svc_rows:
        return {"service": service, "mode": mode, "steps": [], "error": "no rows"}
    chunks = chunk_rows(svc_rows, n)
    steps: list[dict] = []
    prev: dict | None = None
    for i, ch in enumerate(chunks):
        subset = ([r for s in chunks[:i + 1] for r in s] if mode == "cumulative"
                  else ch)
        if not subset:
            continue
        p = infer_mod.profile_service(service, subset)
        ts = sorted(r["ts"] for r in subset if r.get("ts"))
        tpls = (p.get("fingerprint", {}).get("templates") or [])
        step = {
            "step": i + 1,
            "mode": mode,
            "window": f"{_ts(ch[0]['ts'])} → {_ts(ch[-1]['ts'])}" if ch else "?",
            "requests": len(subset),
            "tokens": p.get("total_tokens", 0),
            "project": p.get("project"),
            "pipeline": p.get("pipeline", []),
            "models": p.get("models", {}),
            "n_templates": len(tpls),
            "n_instructions": len(p.get("instructions") or []),
            "schema_hints": p.get("schema_hints", []),
            "top_templates": [(t.get("template") or "")[:180].replace("\n", " | ")
                              for t in tpls[:3]],
            "sample_instructions": (p.get("instructions") or [])[:3],
        }
        if prev is None:
            step["delta"] = {"project_changed": False, "new_stages": p.get("pipeline", []),
                             "template_growth": len(tpls)}
        else:
            new_stages = [s for s in step["pipeline"] if s not in prev["pipeline"]]
            step["delta"] = {"project_changed": step["project"] != prev["project"],
                             "new_stages": new_stages,
                             "template_growth": step["n_templates"] - prev["n_templates"]}
        steps.append(step)
        prev = step
    converged = (len(steps) >= 2 and steps[-1]["project"] == steps[-2]["project"]
                 and not steps[-1]["delta"]["new_stages"])
    return {"service": service, "mode": mode, "total_rows": len(svc_rows),
            "n_chunks": len(chunks), "converged": converged, "steps": steps}
