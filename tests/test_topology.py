"""Unit tests for the topology join (P5.19)."""
from iforensics import topology as topo


def _sources():
    return {
        "mesh_status": {
            "self": {"machine": "axiom",
                     "hardware": {"kind": "cpu"},
                     "health": {"llm_requests_1h": 54}},
            "peers": [
                {"machine": "dgx", "online": True,
                 "hardware": {"kind": "cuda"},
                 "health": {"llm_requests_1h": 7,
                            "services": [{"name": "KG", "status": "running",
                                          "running": 1, "total": 1}]}},
                {"machine": "mac", "online": False,
                 "hardware": {"kind": "mlx"},
                 "health": {"llm_requests_1h": 0, "services": []}},
            ],
        },
        "service_model": {"matrix": [
            {"service": "quai-radar", "model": "qwen3.8:latest",
             "count": 10, "tokens": 100, "avg_ms": 5.0},
            {"service": "quai-radar", "model": "qwen3.8:27b",
             "count": 2, "tokens": 20, "avg_ms": 9.0},
        ]},
        "docker_projects": {"projects": [
            {"name": "KG", "status": "running",
             "containers": [{"name": "kg-1", "status": "Up",
                             "image": "kg:latest"}]},
        ]},
        "logs_overview": {"logs": [
            {"name": "aux-1", "status": "Up", "image": "aux"},
        ]},
        "router_managed": {"pool": ["qwen3.8:latest", "gemma4:31b"]},
    }


def test_layers_and_join_edges():
    g = topo.build(_sources())
    by_id = {n["id"]: n for n in g["nodes"]}
    assert set(g["layers"]) == {"machine", "project", "service", "container", "model"}
    # peer project hosted on dgx, not on axiom
    assert ("machine:dgx", "project:KG", "hosts") in \
        {(e["from"], e["to"], e["kind"]) for e in g["edges"]}
    # service calls both models with weights
    calls = {(e["from"], e["to"]): e for e in g["edges"] if e["kind"] == "calls"}
    assert calls[("service:quai-radar", "model:qwen3.8:latest")]["count"] == 10
    # service observed at the gateway
    assert ("service:quai-radar", "machine:axiom", "observed_via") in \
        {(e["from"], e["to"], e["kind"]) for e in g["edges"]}
    # docker project + container wiring
    assert by_id["container:kg-1"]["image"] == "kg:latest"
    assert ("project:KG", "container:kg-1", "runs") in \
        {(e["from"], e["to"], e["kind"]) for e in g["edges"]}
    # idle pool model present but unconnected
    assert by_id["model:gemma4:31b"]["idle"] is True
    assert not [e for e in g["edges"] if e["to"] == "model:gemma4:31b"]
    assert g["summary"]["nodes"] == len(g["nodes"])


def test_empty_and_error_sources_yield_small_graph_not_exception():
    g = topo.build({})
    assert g["nodes"] == [] or any(n["layer"] == "machine" for n in g["nodes"])
    g2 = topo.build({"mesh_status": {"_error": "URLError"},
                     "service_model": {"matrix": [{"service": "", "model": "x"}]},
                     "docker_projects": {"projects": [{"name": ""}]}})
    assert g2["summary"]["errors"] == ["mesh_status"]
    assert all(n["id"].split(":", 1)[1] for n in g2["nodes"])


def test_self_peer_not_linked_to_itself():
    g = topo.build({"mesh_status": {
        "self": {"machine": "axiom"},
        "peers": [{"machine": "axiom", "online": True}]}})
    assert not [e for e in g["edges"]
                if e["from"] == e["to"] == "machine:axiom"]
