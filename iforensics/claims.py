"""Reporter claims-vs-evidence validation (P5.21).

The agentic reporter returns raw LLM prose. Nothing ever checked whether that
prose is backed by the run: services with failed profilers still get briefed,
evidence quotes are never grounded, critic gaps vanish, and the mandated
Security-posture section can go missing (it did — see the 20261007_162423
brief) without anyone noticing.

`validate_run` replays deterministic checks over a run manifest and reports
proven vs unproven per service plus brief-level issues. Quote grounding is a
normalized substring match against the evidence persisted in
`manifest["heuristic_investigation"][svc]["evidence"]`; manifests predating
that field yield `quotes_unverified` instead of false failures.
"""
from __future__ import annotations

import re

from .run_viz import _gaps, agreement

_WS = re.compile(r"\s+")


def _norm(text: str) -> str:
    return _WS.sub(" ", str(text or "").strip().lower())


def _quote_grounded(quote: str, evidence: dict) -> bool:
    q = _norm(quote)
    if len(q) < 12:
        return False
    haystacks = []
    for key in ("templates", "instructions", "sample_heads"):
        for h in (evidence or {}).get(key) or []:
            if h:
                haystacks.append(_norm(h))
    # a quote may be trimmed with ... — check the longest solid fragment
    frags = sorted((f for f in re.split(r"\.{2,}|…", q) if len(f.strip()) >= 12),
                   key=len, reverse=True)
    probes = frags[:1] if frags else [q]
    return any(p in h for p in probes for h in haystacks)


def _agree(heuristic_project: str, llm_project: str) -> str:
    a = agreement(heuristic_project or "", llm_project or "")
    return {"match": "match", "partial": "match", "disagree": "contested",
            "unknown": "unknown"}.get(a, "unknown")


def validate_run(manifest: dict | None) -> dict:
    """Check a deep-investigation manifest's reporter output against its evidence."""
    manifest = manifest or {}
    agents = manifest.get("agents") or {}
    profs = agents.get("profilers") or {}
    critics = agents.get("critics") or {}
    heur = manifest.get("heuristic_investigation") or {}
    reporter_text = (agents.get("reporter") or {}).get("content") or ""
    sec = manifest.get("security") or {}

    services: dict[str, dict] = {}
    for svc in manifest.get("services") or []:
        issues: list[str] = []
        prof = profs.get(svc) or {}
        parsed = prof.get("parsed") or {} if "error" not in prof else {}
        if "error" in prof or not prof:
            issues.append("profiler failed or missing")
        if not (parsed.get("project") or parsed.get("what_building")):
            issues.append("no usable profiler result")
        quotes = parsed.get("evidence_quotes") or []
        ev = (heur.get(svc) or {}).get("evidence")
        verified, unverified, bad = 0, 0, []
        if quotes and ev is None:
            unverified = len(quotes)
        elif quotes:
            for q in quotes:
                if _quote_grounded(q, ev or {}):
                    verified += 1
                else:
                    bad.append((q or "")[:80])
            if not verified:
                issues.append(f"{len(quotes)} evidence quotes, none grounded")
        elif not issues:
            issues.append("no evidence quotes")
        agr = _agree((heur.get(svc) or {}).get("project", ""),
                         parsed.get("project", ""))
        gaps = _gaps((critics.get(svc) or {}).get("content", ""))
        services[svc] = {"proven": not issues, "agreement": agr,
                         "quotes": len(quotes), "quotes_verified": verified,
                         "quotes_unverified": unverified,
                         "unverified_quotes": bad[:3],
                         "critic_gaps": len(gaps), "issues": issues}

    brief_issues: list[str] = []
    if not sec:
        brief_issues.append("no security scan recorded for this run")
    elif reporter_text and sec.get("n_findings") and "security" not in reporter_text.lower():
        brief_issues.append("security findings present but no Security section in brief")
    if reporter_text and critics and not any(
            s["critic_gaps"] for s in services.values()):
        pass  # critics ran clean — nothing to demand from the brief
    elif reporter_text and any(s["critic_gaps"] for s in services.values()) \
            and "gap" not in reporter_text.lower():
        brief_issues.append("critic gaps exist but the brief never mentions gaps")
    if not reporter_text:
        brief_issues.append("reporter produced no text")

    proven = sum(1 for s in services.values() if s["proven"])
    return {"run_id": manifest.get("run_id") or "",
            "services": services,
            "brief_issues": brief_issues,
            "summary": {"n_services": len(services), "proven": proven,
                        "unproven": len(services) - proven,
                        "contested": sum(1 for s in services.values()
                                        if s["agreement"] == "contested"),
                        "brief_issues": len(brief_issues)}}
