"""Thin fox-services API client (stdlib only, no deps)."""
import json
import urllib.request
import urllib.parse
from . import config


def _get(path: str, params: dict | None = None, timeout: float = 15.0):
    url = config.FOX_URL + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def health():
    return _get("/health")


def stats_summary(hours: int = 168):
    return _get("/api/stats/summary", {"hours": hours})


def distribution(hours: float = 168):
    return _get("/api/stats/distribution", {"hours": hours})


def analytics(hours: float = 168):
    return _get("/api/stats/analytics", {"hours": hours})


def llm_requests(limit: int = 500, service: str | None = None):
    p: dict = {"limit": limit}
    if service:
        p["service"] = service
    return _get("/api/llm/requests", p)


def service_model(hours: int = 168):
    return _get("/api/llm/service-model", {"hours": hours})


def llm_queue():
    return _get("/api/llm/queue")


def router_managed():
    return _get("/api/router/managed")


def mesh_status():
    return _get("/api/mesh/status")


def mesh_peers(offline: bool = True):
    return _get("/api/mesh/peers", {"offline": "true" if offline else "false"})


def hardware_status():
    return _get("/api/hardware/status")


def docker_projects():
    return _get("/api/docker/projects")


def logs_overview(tail: int = 60, max_containers: int = 6):
    return _get("/api/docker/logs/overview", {"tail": tail, "max_containers": max_containers})


def collect_all(hours: int = 168, req_limit: int = 2000) -> dict:
    """Best-effort dump of every observable surface. Failures -> {'_error': ...}."""
    out: dict = {}
    calls = {
        "health": lambda: health(),
        "stats_summary": lambda: stats_summary(hours),
        "distribution": lambda: distribution(hours),
        "analytics": lambda: analytics(hours),
        "llm_requests": lambda: llm_requests(req_limit),
        "service_model": lambda: service_model(hours),
        "llm_queue": lambda: llm_queue(),
        "router_managed": lambda: router_managed(),
        "mesh_status": lambda: mesh_status(),
        "mesh_peers": lambda: mesh_peers(),
        "hardware_status": lambda: hardware_status(),
        "docker_projects": lambda: docker_projects(),
        "logs_overview": lambda: logs_overview(),
    }
    for k, fn in calls.items():
        try:
            out[k] = fn()
        except Exception as e:  # noqa: BLE001 - forensic tool must not die on one endpoint
            out[k] = {"_error": f"{type(e).__name__}: {e}"}
    return out
