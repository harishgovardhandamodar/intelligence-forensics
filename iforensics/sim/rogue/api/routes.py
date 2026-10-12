"""Route catalogue: every framework operation → its `/api/rogue/*` route.

The dashboard is the server; this module is the map, not a second server.
`call()` is the stdlib transport helper used by the framework CLI.
"""
from __future__ import annotations

import json
import urllib.parse
import urllib.request

ROUTES = {
    "catalogue": ("GET", "/api/rogue/catalogue"),
    "categories": ("GET", "/api/rogue/categories"),
    "policy": ("GET", "/api/rogue/policy"),
    "run": ("POST", "/api/rogue/run"),
    "runs": ("GET", "/api/rogue/runs"),
    "run_file": ("GET", "/api/rogue/run"),
    "reset": ("POST", "/api/rogue/reset"),
}


def call(server: str, name: str, payload: dict | None = None,
         params: dict | None = None, timeout: int = 120) -> dict:
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
