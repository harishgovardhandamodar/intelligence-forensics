"""Findings hub (P6.23): one ranked list across every analysis surface.

Security findings, risk bands, trust assertions, claims validation, fidelity
verdicts and live alerts each have their own endpoint and tab — but an
investigation starts with "what needs attention", not six tabs. `collect`
folds them into one severity-ranked list with a stable shape:

    {severity, area, title, detail, ref}

Areas: security, risk, trust, claims, fidelity, alert. Severities use the
house bands (critical/high/medium/low); informational notes are "low".
"""
from __future__ import annotations

import time

SEV_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
MAX_FINDINGS = 200


def _item(severity: str, area: str, title: str, detail: str = "",
          ref: str = "") -> dict:
    return {"severity": severity if severity in SEV_RANK else "low",
            "area": area, "title": title, "detail": detail, "ref": ref}


def collect(rows: list[dict] | None = None, app=None,
            tap_status: dict | None = None,
            run_validation: dict | None = None) -> dict:
    """Aggregate every finding source. Each source is optional — a failure in
    one must never hide the others (same house rule as fox_client.collect_all)."""
    rows = rows or []
    out: list[dict] = []

    try:
        from . import security_agent
        rep = security_agent.deterministic_report(app=app)
        for group in ("secrets", "injections", "permissions", "exposure"):
            for f in (rep.get(group) or [])[:100]:
                loc = f.get("source", "")
                if f.get("line"):
                    loc += f":{f['line']}"
                out.append(_item(f.get("severity") or "medium", "security",
                                 f"{f.get('kind')} — {loc}",
                                 f.get("remediation") or "", ref="security"))
    except Exception:  # noqa: BLE001
        pass

    try:
        from . import risk as risk_mod
        rk = risk_mod.service_risk(rows)
        for s in rk.get("services") or []:
            if s.get("band") in (None, "low"):
                continue
            g = s.get("signals") or {}
            out.append(_item(s["band"], "risk",
                             f"{s['service']} inflow risk: {s['band']} ({s['score']})",
                             f"PII {g.get('pii', 0)} · injections {g.get('injection', 0)} · "
                             f"vol-z {g.get('volume_z', 0)} · reuse "
                             f"{g.get('cross_service_reuse', 0)}", ref="security"))
    except Exception:  # noqa: BLE001
        pass

    try:
        from . import trust as trust_mod
        tr = trust_mod.audit()
        for r in tr.get("rules") or []:
            if r.get("status") == "pass":
                continue
            sev = r.get("severity") if r.get("status") == "fail" else "low"
            out.append(_item(sev, "trust",
                             f"boundary {r.get('rule')}: {r.get('status')}",
                             r.get("detail") or "", ref="security"))
    except Exception:  # noqa: BLE001
        pass

    if run_validation:
        rid = run_validation.get("run_id") or ""
        ref = f"ledger:{rid}" if rid else "agents"
        for svc, s in (run_validation.get("services") or {}).items():
            if not s.get("proven"):
                out.append(_item("high", "claims",
                                 f"{svc}: brief claims unproven",
                                 "; ".join(s.get("issues") or []), ref=ref))
        for issue in run_validation.get("brief_issues") or []:
            out.append(_item("medium", "claims", issue, ref=ref))

    try:
        from . import fidelity as fid_mod
        if rows:
            fi = fid_mod.score_all(rows)
            for s in fi.get("services") or []:
                if s.get("verdict") == "stale":
                    out.append(_item("high", "fidelity",
                                     f"{s['service']}: reconstruction stale "
                                     f"({s['match_rate']} recall)",
                                     f"drifted: {', '.join(s.get('drifted') or [])}",
                                     ref="recon"))
                elif s.get("verdict") == "drifting":
                    out.append(_item("medium", "fidelity",
                                     f"{s['service']}: reconstruction drifting "
                                     f"({s['match_rate']} recall)", ref="recon"))
    except Exception:  # noqa: BLE001
        pass

    for a in (tap_status or {}).get("alerts") or []:
        out.append(_item(a.get("severity") or "medium", "alert",
                         f"{a.get('kind')}"
                         f"{' ' + a['service'] if a.get('service') else ''}: "
                         f"{a.get('detail')}", ref="live"))

    out.sort(key=lambda f: (SEV_RANK[f["severity"]], f["area"], f["title"]))
    out = out[:MAX_FINDINGS]
    by_sev: dict[str, int] = {}
    by_area: dict[str, int] = {}
    for f in out:
        by_sev[f["severity"]] = by_sev.get(f["severity"], 0) + 1
        by_area[f["area"]] = by_area.get(f["area"], 0) + 1
    return {"findings": out, "generated_at": time.time(),
            "summary": {"total": len(out), "by_severity": by_sev,
                        "by_area": by_area}}
