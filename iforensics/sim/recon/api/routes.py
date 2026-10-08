"""Route catalogue: every framework operation → its live `/api/recon/*` route.

The dashboard is the server; this module is the map, not a second server.
`call()` is a thin stdlib transport helper used by the framework CLI.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

ROUTES = {
    "surfaces": ("GET", "/api/recon/surfaces"),
    "begin": ("POST", "/api/recon/begin"),
    "ingest": ("POST", "/api/recon/ingest"),
    "reconstruct": ("POST", "/api/recon/reconstruct"),
    "report": ("GET", "/api/recon/report"),
    "run": ("POST", "/api/recon/run"),
    "residuals": ("GET", "/api/recon/residuals"),
    "runs": ("GET", "/api/recon/runs"),
    "run_file": ("GET", "/api/recon/run"),
    "reset": ("POST", "/api/recon/reset"),
    "collection": ("GET", "/api/recon/collection"),
    "consume": ("POST", "/api/recon/consume"),
    "harvest_live": ("POST", "/api/recon/harvest-live"),
    "coserve": ("POST", "/api/recon/coserve"),
    "live_users": ("GET", "/api/recon/live-users"),
}


def call(server: str, name: str, payload: dict | None = None,
         params: dict | None = None, timeout: int = 60) -> dict:
    """One stdlib HTTP call against the dashboard (transport only)."""
    method, path = ROUTES[name]
    url = server.rstrip("/") + path
    if params:
        url += "?" + urllib.parse.urlencode(
            {k: v for k, v in params.items() if v is not None})
    data = json.dumps(payload or {}).encode() if method == "POST" else None
    req = urllib.request.Request(
        url, data=data, method=method,
        headers={"content-type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        try:
            return {"http_error": e.code, **json.loads(e.read().decode())}
        except Exception:  # noqa: BLE001
            return {"http_error": e.code, "detail": str(e)}
