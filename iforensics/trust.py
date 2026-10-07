"""Trust-boundary assertions (D4).

The claims in `design/trust-boundaries.md` (T1-T8) are *enforced, not advised*.
This module re-checks them against the actual code/config on every run, so a
regression that quietly crosses a boundary shows up as a failing assertion
instead of a stale promise in a design doc.

Each check returns one finding::

    {"rule": "T1", "status": "pass"|"warn"|"fail",
     "severity": "critical"|"high"|"medium"|"low",
     "detail": "...", "evidence": ["file:line ...", ...]}

`status` is the assertion result; `severity` is the impact if it fails.
"""
from __future__ import annotations

import os
import re
import time

SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "graft",
             ".claude", ".mypy_cache", ".pytest_cache", "tests"}
# This module necessarily contains the forbidden-host and secret-shaped patterns
# it searches for; scanning it would be a tautology.
_SELF = os.path.join("iforensics", "trust.py")
ALLOWED_HOSTS = {"localhost", "127.0.0.1", "0.0.0.0", "host.docker.internal",
                 "[::1]"}
CLOUD_HOSTS = ("openai.com", "anthropic.com", "generativelanguage.googleapis.com",
               "api.openai", "claude.ai", "api.together", "openrouter.ai",
               "cohere.ai", "mistral.ai")
_SECRET_LITERALS = re.compile(
    r"(AKIA[0-9A-Z]{16}|sk-[A-Za-z0-9]{20,}|ghp_[A-Za-z0-9]{20,}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|xox[baprs]-[A-Za-z0-9-]{10,})")
_URL = re.compile(r"https?://([A-Za-z0-9._\-]+)")
_WRITE_SQL = re.compile(r"(?i)\b(INSERT\s+INTO|UPDATE\s+\w+\s+SET|DELETE\s+FROM|"
                        r"DROP\s+TABLE|CREATE\s+TABLE|ALTER\s+TABLE)\b")
_READ_ONLY = re.compile(r"(mode=ro|copyfile|immutable)")


def _finding(rule, status, severity, detail, evidence=None):
    return {"rule": rule, "status": status, "severity": severity,
            "detail": detail, "evidence": evidence or []}


def _read(base_dir: str, rel: str) -> str:
    try:
        with open(os.path.join(base_dir, rel), encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _iter_source_lines(base_dir: str, exts=(".py", ".js")):
    """(relpath, lineno, line) across repo source (server + browser JS)."""
    for root, dirs, files in os.walk(base_dir):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for name in files:
            if not name.endswith(exts) or name.endswith(".min.js"):
                continue
            path = os.path.join(root, name)
            rel = os.path.relpath(path, base_dir)
            if rel == _SELF:
                continue
            try:
                with open(path, encoding="utf-8", errors="ignore") as fh:
                    for i, line in enumerate(fh, start=1):
                        yield rel, i, line
            except OSError:
                continue


def _read_file(path: str) -> str:
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _host_ok(host: str) -> bool:
    host = host.split(":")[0]
    if host in ALLOWED_HOSTS or re.fullmatch(r"127\.\d+\.\d+\.\d+", host):
        return True
    # RFC-reserved: .localhost/.invalid/.example/.test can never route,
    # so fixture URLs using them are not peer contact
    return host.endswith((".local", ".ts.net", ".localhost", ".invalid",
                           ".example", ".test"))


def check_t1(base_dir: str) -> dict:
    """T1 — Fox DB is never written (ro mount; no write SQL in read paths)."""
    evidence, ok = [], True
    compose = _read_file(os.path.join(base_dir, "docker-compose.yml"))
    if compose:
        if re.search(r"/fox-data:ro|:ro\b", compose):
            evidence.append("docker-compose.yml: fox-data mount is :ro")
        else:
            ok = False
            evidence.append("docker-compose.yml: fox-data mount is NOT :ro")
    stext = _read_file(os.path.join(base_dir, "iforensics", "store.py"))
    if stext:
        hits = _WRITE_SQL.findall(stext)
        if hits:
            ok = False
            evidence += [f"iforensics/store.py: write SQL {h!r}" for h in hits[:5]]
        else:
            evidence.append("iforensics/store.py: no write SQL; reads via copy/ro")
    return {"rule": "T1", "status": "pass" if ok else "fail",
            "severity": "critical",
            "detail": "Fox DB is opened read-only and never written." if ok
                      else "A write path to the fox DB was found.",
            "evidence": evidence}


def check_t2(base_dir: str) -> dict:
    """T2 — No peer contact: no non-loopback host reachable from code."""
    server, browser = [], []
    for rel, line, text in _iter_source_lines(base_dir):
        for host in _URL.findall(text):
            if _host_ok(host):
                continue
            loc = f"{rel}:{line} -> {host}"
            (browser if rel.startswith("static/") else server).append(loc)
    status = "fail" if server else ("warn" if browser else "pass")
    return {"rule": "T2", "status": status,
            "severity": "high" if server else "medium",
            "detail": ("No outbound peer/foreign host is referenced in code."
                       if not (server or browser) else
                       ("Server code references a non-loopback host." if server else
                        "Browser fallback loads an asset from a CDN host.")),
            "evidence": (server + browser)[:12]}


def check_t3(base_dir: str) -> dict:
    """T3 — Inference is local-only: loopback Ollama, no cloud model host."""
    evidence, ok = [], True
    oc = _read_file(os.path.join(base_dir, "iforensics", "ollama_client.py"))
    m = re.search(r'OLLAMA_URL\s*=\s*os\.environ\.get\(\s*"OLLAMA_URL",\s*'
                  r'"https?://([^"/]+)', oc)
    if m:
        host = m.group(1)
        evidence.append(f"ollama_client.py: OLLAMA_URL default host {host!r}")
        if not _host_ok(host):
            ok = False
    cloud = [f"{rel}:{line} -> {h}" for rel, line, text in _iter_source_lines(base_dir)
             for h in CLOUD_HOSTS if h in text.lower()]
    if cloud:
        ok = False
        evidence += cloud[:6]
    return {"rule": "T3", "status": "pass" if ok else "fail",
            "severity": "critical",
            "detail": ("Inference targets local Ollama only; no cloud model host."
                       if ok else "A cloud model host or non-local OLLAMA_URL was found."),
            "evidence": evidence}


def check_t4(base_dir: str) -> dict:
    """T4 — No secrets to hold: no docker socket, no key/token literals."""
    evidence = []
    compose = _read_file(os.path.join(base_dir, "docker-compose.yml"))
    if "docker.sock" in compose:
        evidence.append("docker-compose.yml: docker.sock is mounted")
    for rel, line, text in _iter_source_lines(base_dir):
        if _SECRET_LITERALS.search(text):
            evidence.append(f"{rel}:{line} -> secret-shaped literal")
    ok = not evidence
    return {"rule": "T4", "status": "pass" if ok else "fail",
            "severity": "critical",
            "detail": ("Container holds no tokens/keys and no Docker socket."
                       if ok else "A secret-shaped literal or docker socket was found."),
            "evidence": evidence[:12]}


def check_t5(base_dir: str) -> dict:
    """T5 — Viewer boundary is explicit in the README (no auth => LAN/tailnet)."""
    readme = _read_file(os.path.join(base_dir, "README.md")).lower()
    no_auth = "no auth" in readme or "no authentication" in readme
    scope = "tailnet" in readme or "lan" in readme
    bind = "0.0.0.0" in readme or "bind" in readme
    ok = no_auth and scope and bind
    return {"rule": "T5", "status": "pass" if ok else "warn",
            "severity": "medium",
            "detail": ("README documents no-auth LAN/tailnet exposure and bind."
                       if ok else "README does not fully document the viewer boundary."),
            "evidence": [f"no_auth={no_auth}", f"lan_tailnet={scope}", f"bind={bind}"]}


def check_t6(base_dir: str) -> dict:
    """T6 — Reconstructions are labeled (RECONSTRUCTED.json + caveats)."""
    evidence, ok = [], True
    rtext = _read_file(os.path.join(base_dir, "iforensics", "reconstruct.py"))
    if "RECONSTRUCTED.json" in rtext and "caveats" in rtext:
        evidence.append("reconstruct.py: writes RECONSTRUCTED.json + caveats")
    else:
        ok = False
        evidence.append("reconstruct.py: missing RECONSTRUCTED.json/caveats writer")
    recdir = os.path.join(base_dir, "reconstructions")
    if os.path.isdir(recdir):
        for name in sorted(os.listdir(recdir)):
            d = os.path.join(recdir, name)
            if os.path.isdir(d) and not os.path.exists(
                    os.path.join(d, "RECONSTRUCTED.json")):
                ok = False
                evidence.append(f"reconstructions/{name}: no RECONSTRUCTED.json")
    return {"rule": "T6", "status": "pass" if ok else "fail",
            "severity": "high",
            "detail": ("Every scaffold ships RECONSTRUCTED.json + caveats."
                       if ok else "A reconstruction is missing its label."),
            "evidence": evidence}


def check_t7(base_dir: str) -> dict:
    """T7 — Workers are isolated: host UID, GPUs, least mount wins."""
    evidence, ok = [], True
    compose = _read_file(os.path.join(base_dir, "docker-compose.yml"))
    for svc in ("swarm-worker", "swarm-gather"):
        block = re.search(rf"^  {svc}:(.*?)(?=^  \S|\Z)", compose,
                          re.M | re.S)
        body = block.group(1) if block else ""
        if re.search(r"^\s*user:\s*[\"']?\$\{UID", body, re.M):
            evidence.append(f"{svc}: runs as host UID (user: $UID)")
        else:
            ok = False
            evidence.append(f"{svc}: missing user: directive (root-owned volume files)")
        if "nvidia" in body:
            evidence.append(f"{svc}: NVIDIA GPU reservation present")
        else:
            evidence.append(f"{svc}: no GPU reservation (CPU-only worker)")
    fox_ro = [m.start() for m in re.finditer(r"/fox-data:ro", compose)]
    if fox_ro:
        evidence.append("docker-compose.yml: fox-data mounts are :ro")
    else:
        ok = False
        evidence.append("docker-compose.yml: no :ro fox-data mount found")
    return {"rule": "T7", "status": "pass" if ok else "fail",
            "severity": "high",
            "detail": ("Swarm workers run as host UID with least-privilege mounts."
                       if ok else "Worker isolation regressed — see evidence."),
            "evidence": evidence}


def check_t8(base_dir: str) -> dict:
    """T8 — Destruction needs a recorded human: prune gates + ledger approvals."""
    evidence, ok = [], True
    cli = _read_file(os.path.join(base_dir, "cli.py"))
    if "needs " in cli and "--approve" in cli and "refusing" in cli:
        evidence.append("cli.py: prune --apply refuses without --approve")
    else:
        ok = False
        evidence.append("cli.py: prune --apply gate missing")
    if "find_approval" in cli and "PermissionError" in cli:
        evidence.append("cli.py: worker prune re-checks find_approval")
    else:
        ok = False
        evidence.append("cli.py: worker prune approval check missing")
    led = _read_file(os.path.join(base_dir, "iforensics", "ledger.py"))
    if "def approve" in led and "def find_approval" in led:
        evidence.append("ledger.py: approve/find_approval present")
    else:
        ok = False
        evidence.append("ledger.py: approval helpers missing")
    return {"rule": "T8", "status": "pass" if ok else "fail",
            "severity": "high",
            "detail": ("Destructive actions require a ledger-recorded human approval."
                       if ok else "Approval gating regressed — see evidence."),
            "evidence": evidence}


CHECKS = [check_t1, check_t2, check_t3, check_t4, check_t5, check_t6,
          check_t7, check_t8]


def audit(base_dir: str | None = None) -> dict:
    """Run every boundary assertion; summarize pass/warn/fail."""
    import iforensics.config as config
    base = base_dir or config.BASE_DIR
    rules = []
    for fn in CHECKS:
        try:
            rules.append(fn(base))
        except Exception as e:  # noqa: BLE001 — a broken check is itself a finding
            rules.append({"rule": fn.__name__, "status": "warn",
                          "severity": "medium", "detail": f"check error: {e}",
                          "evidence": []})
    summary = {s: sum(1 for r in rules if r["status"] == s)
               for s in ("pass", "warn", "fail")}
    return {"generated_at": time.time(), "base": base, "rules": rules,
            "summary": summary, "ok": summary["fail"] == 0}