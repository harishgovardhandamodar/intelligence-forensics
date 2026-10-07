"""Knowledge graph (P6.25): forensic entities and how they connect.

The topology tab shows infrastructure (machines, containers). This graph
shows *evidence*: services, the prompt templates they use, the models they
call, the findings attached to them, and the reconstructions already built.
A template node with edges into two services IS cross-service prompt leakage
made visible; a finding node hangs off exactly the service it condemns.

Built from traffic rows (+ optional precomputed risk), capped so the SVG
stays readable. Pure function — no fox, no LLM.
"""
from __future__ import annotations

import hashlib
import os

LAYERS = ("service", "template", "model", "finding", "evidence")

MAX_ROWS = 2000
MAX_TEMPLATES_PER_SERVICE = 5
MAX_TEMPLATES_TOTAL = 60
MAX_SERVICES = 40


def _tid(text: str) -> str:
    norm = " ".join(str(text or "").lower().split())
    return "template:" + hashlib.sha1(norm.encode()).hexdigest()[:12]


def build(rows: list[dict] | None = None, risk: dict | None = None,
          recon_dir: str | None = None) -> dict:
    """Assemble the entity graph. `risk` is a precomputed service_risk() dict."""
    from . import config, infer as infer_mod
    from . import risk as risk_mod

    rows = list(rows or [])[-MAX_ROWS:]
    inv = infer_mod.investigate_all(rows) if rows else {"services": {}}
    if risk is None:
        try:
            risk = risk_mod.service_risk(rows)
        except Exception:  # noqa: BLE001
            risk = {"services": []}
    risk_by_svc = {s["service"]: s for s in (risk or {}).get("services", [])}

    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def add(nid: str, layer: str, label: str, **attr):
        if nid not in nodes:
            nodes[nid] = {"id": nid, "layer": layer, "label": label, **attr}

    def link(frm: str, to: str, kind: str, **attr):
        if frm in nodes and to in nodes:
            e = {"from": frm, "to": to, "kind": kind}
            e.update(attr)
            edges.append(e)

    base = recon_dir or config.RECON_DIR
    profs = inv.get("services", {})
    for svc in sorted(profs, key=lambda s: -profs[s].get("requests", 0))[:MAX_SERVICES]:
        p = profs[svc]
        sid = f"service:{svc}"
        add(sid, "service", svc, requests=p.get("requests", 0),
            project=p.get("project") or "")
        for t in (p.get("fingerprint", {}).get("templates") or [])[:MAX_TEMPLATES_PER_SERVICE]:
            if len([n for n in nodes if n.startswith("template:")]) >= MAX_TEMPLATES_TOTAL:
                break
            text = t.get("template") or ""
            if not text.strip():
                continue
            tid = _tid(text)
            add(tid, "template", text[:60].replace("\n", " "),
                count=t.get("count") or 0)
            link(sid, tid, "uses", count=t.get("count") or 0)
        for model, n in (p.get("models") or {}).items():
            mid = f"model:{model}"
            add(mid, "model", model)
            link(sid, mid, "calls", count=n)
        rb = risk_by_svc.get(svc) or {}
        if rb.get("band") not in (None, "low", ""):
            fid = f"finding:risk:{svc}"
            add(fid, "finding", f"{svc}: {rb['band']} ({rb.get('score')})",
                severity=rb["band"], score=rb.get("score"))
            link(sid, fid, "flagged")
        if os.path.isfile(os.path.join(base, svc, "RECONSTRUCTED.json")):
            eid = f"evidence:recon:{svc}"
            add(eid, "evidence", f"{svc} reconstruction")
            link(sid, eid, "reconstructed_as")

    shared = sum(1 for n in nodes
                 if n.startswith("template:")
                 and sum(1 for e in edges if e["to"] == n) > 1)
    by_layer: dict[str, int] = {}
    for n in nodes.values():
        by_layer[n["layer"]] = by_layer.get(n["layer"], 0) + 1
    kinds: dict[str, int] = {}
    for e in edges:
        kinds[e["kind"]] = kinds.get(e["kind"], 0) + 1
    return {"nodes": list(nodes.values()), "edges": edges,
            "layers": [L for L in LAYERS if any(n["layer"] == L for n in nodes.values())],
            "summary": {"nodes": len(nodes), "edges": len(edges),
                        "by_layer": by_layer, "by_kind": kinds,
                        "shared_templates": shared}}
