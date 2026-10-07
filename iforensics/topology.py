"""Topology join (P5.19): one service -> container -> peer -> model graph.

`fox_client.collect_all` reads mesh, docker and LLM traffic independently and
nothing ever joins them, so the Mesh tab shows a peer list while the Services
tab shows traffic and the two never meet. This module folds the already
collected sources into a single layered node/edge graph:

    machine --hosts--> project --runs--> container
    machine --gossip--> machine (self)
    service --calls--> model (weighted by the service_model matrix)
    service --observed-via--> self machine (all LLM rows are seen at the gateway)

Every input is defensive (missing keys, `_error` stubs, empty lists all yield
a smaller graph, never an exception) and sizes are capped so a large fleet
cannot blow up the dashboard SVG.
"""
from __future__ import annotations

LAYERS = ("machine", "project", "service", "container", "model")

MAX_MATRIX_ROWS = 500
MAX_CONTAINERS = 200
MAX_PROJECTS = 100


def _node(nid: str, layer: str, label: str, **attr) -> dict:
    d = {"id": nid, "layer": layer, "label": label}
    d.update(attr)
    return d


def build(sources: dict | None = None) -> dict:
    """Join mesh/docker/traffic sources into {nodes, edges, summary}."""
    sources = sources or {}
    nodes: dict[str, dict] = {}
    edges: list[dict] = []

    def add(nid: str, layer: str, label: str, **attr):
        if nid not in nodes:
            nodes[nid] = _node(nid, layer, label, **attr)
        else:
            nodes[nid].update(attr)

    def link(frm: str, to: str, kind: str, **attr):
        if frm in nodes and to in nodes:
            e = {"from": frm, "to": to, "kind": kind}
            e.update(attr)
            edges.append(e)

    # -- self machine + peers -------------------------------------------------
    mesh = sources.get("mesh_status") or {}
    me = mesh.get("self") or {}
    me_name = me.get("machine") or me.get("hostname") or "self"
    me_id = f"machine:{me_name}"
    me_health = me.get("health") or {}
    add(me_id, "machine", me_name, online=True,
        hw=(me.get("hardware") or {}).get("kind") or "?",
        llm_1h=(me_health.get("llm_requests_1h") or 0), is_self=True)

    for p in (mesh.get("peers") or []):
        if not isinstance(p, dict):
            continue
        name = p.get("machine") or p.get("hostname") or p.get("node_id") or "?"
        pid = f"machine:{name}"
        h = p.get("health") or {}
        add(pid, "machine", name, online=bool(p.get("online")),
            hw=(p.get("hardware") or {}).get("kind") or "?",
            llm_1h=(h.get("llm_requests_1h") or 0))
        if pid != me_id:
            link(pid, me_id, "gossip")
        for s in (h.get("services") or [])[:MAX_PROJECTS]:
            if not isinstance(s, dict) or not s.get("name"):
                continue
            sid = f"project:{s['name']}"
            add(sid, "project", s["name"], status=s.get("status") or "?",
                running=s.get("running") or 0, total=s.get("total") or 0)
            link(pid, sid, "hosts", status=s.get("status") or "?")

    # -- service -> model matrix (observed at the gateway) --------------------
    sm = sources.get("service_model") or {}
    for row in (sm.get("matrix") or [])[:MAX_MATRIX_ROWS]:
        if not isinstance(row, dict) or not row.get("service"):
            continue
        svc, model = row["service"], row.get("model") or "unknown"
        sid, mid = f"service:{svc}", f"model:{model}"
        add(sid, "service", svc)
        add(mid, "model", model)
        link(sid, mid, "calls", count=row.get("count") or 0,
             tokens=row.get("tokens") or 0, avg_ms=round(row.get("avg_ms") or 0, 1))
        link(sid, me_id, "observed_via")

    # -- docker projects + containers -----------------------------------------
    dp = sources.get("docker_projects") or {}
    for proj in (dp.get("projects") or [])[:MAX_PROJECTS]:
        if not isinstance(proj, dict) or not proj.get("name"):
            continue
        sid = f"project:{proj['name']}"
        add(sid, "project", proj["name"], status=proj.get("status") or "?")
        link(me_id, sid, "hosts")
        for c in (proj.get("containers") or [])[:MAX_CONTAINERS]:
            if not isinstance(c, dict) or not c.get("name"):
                continue
            cid = f"container:{c['name']}"
            add(cid, "container", c["name"], status=c.get("status") or "?",
                image=c.get("image") or "")
            link(sid, cid, "runs")

    # -- container logs fallback (host-local view when projects are empty) ----
    lo = sources.get("logs_overview") or {}
    seen_containers = sum(1 for n in nodes if n.startswith("container:"))
    for c in (lo.get("logs") or [])[:max(0, MAX_CONTAINERS - seen_containers)]:
        if not isinstance(c, dict) or not c.get("name"):
            continue
        cid = f"container:{c['name']}"
        add(cid, "container", c["name"], status=c.get("status") or "?",
            image=c.get("image") or "")
        link(me_id, cid, "runs")

    # -- router pool: models with capacity but no observed traffic -------------
    router = sources.get("router_managed") or {}
    for m in (router.get("pool") or []):
        if not m:
            continue
        mid = f"model:{m}"
        if mid not in nodes:
            add(mid, "model", m, idle=True)

    by_layer: dict[str, int] = {}
    for n in nodes.values():
        by_layer[n["layer"]] = by_layer.get(n["layer"], 0) + 1
    return {"nodes": list(nodes.values()), "edges": edges,
            "layers": [L for L in LAYERS if any(n["layer"] == L for n in nodes.values())],
            "summary": {"nodes": len(nodes), "edges": len(edges), "by_layer": by_layer,
                        "errors": sorted(k for k, v in sources.items()
                                         if isinstance(v, dict) and "_error" in v)}}
