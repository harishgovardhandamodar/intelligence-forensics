"""Markdown investigation report."""
import datetime
import os


def _ts(t: float) -> str:
    try:
        return datetime.datetime.fromtimestamp(t).isoformat(timespec="seconds")
    except Exception:
        return "?"


def render(investigation: dict, mesh: dict | None = None, api_errors: list[str] | None = None) -> str:
    L: list[str] = ["# Intelligence Forensics — what the mesh is building", ""]
    L.append(f"Requests analyzed: **{investigation.get('n_requests')}** "
             f"across **{investigation.get('n_services')}** services.")
    L.append("")
    if mesh:
        peers = mesh.get("peers", []) if isinstance(mesh, dict) else []
        L.append(f"Mesh peers visible: **{len(peers)}**.")
        for p in peers:
            h = (p.get("health") or {})
            svcs = ", ".join(s.get("name", "?") for s in h.get("services", [])[:12])
            L.append(f"- `{p.get('machine')}` online={p.get('online')} "
                     f"hw={(p.get('hardware') or {}).get('kind')} "
                     f"llm_1h={h.get('llm_requests_1h')} services:[{svcs}]")
        L.append("")
    for svc, p in investigation.get("services", {}).items():
        L.append(f"## {svc}")
        L.append(f"Inferred build: **{p.get('project')}**")
        L.append(f"{p.get('pipeline_summary')}")
        L.append(f"- requests: {p['requests']}, tokens: {p['total_tokens']} "
                 f"(avg {p['avg_tokens']}/req), cadence ~{p['cadence_median_s']}s")
        tr = p.get("time_range") or []
        if len(tr) == 2:
            L.append(f"- window: {_ts(tr[0])} -> {_ts(tr[1])}")
        L.append(f"- models: `{p.get('models')}`")
        L.append(f"- query types: `{p.get('query_types')}` / requestors: `{p.get('requestors')}`")
        L.append(f"- pipeline: `{' -> '.join(p.get('pipeline', []))}`")
        L.append(f"- schema hints: {p.get('schema_hints')}")
        L.append("- recovered instructions:")
        for ins in (p.get("instructions") or [])[:6]:
            L.append(f"  - {ins[:220]}")
        L.append("- prompt templates observed:")
        for t in (p.get("fingerprint", {}).get("templates") or [])[:4]:
            L.append(f"  - (x{t['count']}) {t['template'][:220].replace(chr(10), ' | ')}")
        L.append("")
    if api_errors:
        L.append("## Collector gaps")
        for e in api_errors:
            L.append(f"- {e}")
    L.append("_Caveat: fox DB stores truncated, secret-redacted, PII-masked prompt heads; "
             "completions are not logged. Reconstruction recovers templates + pipeline, "
             "not exact source._")
    return "\n".join(L)


def write(report: str, path: str) -> str:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(report)
    return path
