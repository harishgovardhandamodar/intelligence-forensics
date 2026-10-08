"""HTTP client for the axiom reconstruction API — stdlib only (urllib).

Every call is one request/response; the server does all the residual-store
and reconstruction math, exactly like `sim/run.py` does for the embedding
simulation. Nothing here parses a prompt or scores an assembly.

The peer address is *configuration*, not code: it lives in `settings.yaml`
next to this file so a copy of the folder points at its own server without
any edit — and so no server-side source file names a non-loopback host
(see trust rule T2).
"""
from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request

# Loopback default; `settings.yaml` supplies the real peer address.
DEFAULT_SERVER = "http://127.0.0.1:8211"
FALLBACK_SERVER = "http://localhost:8211"


class ServerError(RuntimeError):
    """Non-2xx from the server, or the server is unreachable."""


def _url(server: str, path: str) -> str:
    return server.rstrip("/") + path


def _request(server: str, method: str, path: str, body=None, timeout=60):
    data = None
    url = _url(server, path)
    if body is not None:
        data = json.dumps(body).encode()
    elif method == "GET":
        pass
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read().decode()
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")[:300]
        raise ServerError(f"{e.code} {path}: {detail}") from e
    except (urllib.error.URLError, OSError) as e:
        raise ServerError(f"unreachable {server}: {e}") from e
    try:
        return json.loads(raw) if raw else {}
    except json.JSONDecodeError as e:
        raise ServerError(f"bad JSON from {path}: {raw[:200]}") from e


class ReconAPI:
    """Thin typed wrapper over /api/recon/*."""

    def __init__(self, server: str = DEFAULT_SERVER, timeout: int = 60):
        self.server = server.rstrip("/")
        self.timeout = timeout

    # -- catalogue -------------------------------------------------------- #

    def health(self) -> dict:
        return _request(self.server, "GET", "/health", timeout=8)

    def surfaces(self) -> dict:
        return _request(self.server, "GET", "/api/recon/surfaces",
                        timeout=self.timeout)

    # -- session ---------------------------------------------------------- #

    def begin(self, user_id: str, truth: dict, scenario: str = "") -> dict:
        return _request(self.server, "POST", "/api/recon/begin",
                        {"user_id": user_id, "truth": truth,
                         "scenario": scenario}, timeout=self.timeout)

    def ingest(self, prompt: str, metadata: dict, mask: str = "",
               step: int = 0, response: str = "") -> dict:
        return _request(self.server, "POST", "/api/recon/ingest",
                        {"prompt": prompt, "metadata": metadata, "mask": mask,
                         "step": step, "response": response},
                        timeout=self.timeout)

    def run(self, scenario: str, n: int = 48, seed: int = 42) -> dict:
        """Server-side session: ingest every turn, report, persist."""
        return _request(self.server, "POST", "/api/recon/run",
                        {"scenario": scenario, "n": n, "seed": seed},
                        timeout=max(self.timeout, 120))

    def report(self, user_id: str) -> dict:
        q = urllib.parse.urlencode({"user_id": user_id})
        return _request(self.server, "GET", f"/api/recon/report?{q}",
                        timeout=self.timeout)

    def reconstruct(self, user_id: str, surfaces: list[str] | None = None,
                    amplify: bool = True) -> dict:
        return _request(self.server, "POST", "/api/recon/reconstruct",
                        {"user_id": user_id, "surfaces": surfaces or [],
                         "amplify": amplify}, timeout=self.timeout)

    def residuals(self, user_id: str, surface: str = "", limit: int = 100) -> dict:
        q = urllib.parse.urlencode({"user_id": user_id, "surface": surface,
                                    "limit": limit})
        return _request(self.server, "GET", f"/api/recon/residuals?{q}",
                        timeout=self.timeout)

    def runs(self) -> dict:
        return _request(self.server, "GET", "/api/recon/runs",
                        timeout=self.timeout)

    def load_run(self, run_id: str) -> dict:
        q = urllib.parse.urlencode({"run_id": run_id})
        return _request(self.server, "GET", f"/api/recon/run?{q}",
                        timeout=self.timeout)

    def reset(self) -> dict:
        return _request(self.server, "POST", "/api/recon/reset", {},
                        timeout=self.timeout)
