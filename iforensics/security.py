"""Deterministic leak + exposure scanning (D2/D3).

Pure stdlib, no LLM: surface secrets, PII-shaped survivors, over-permissive
files and unauthenticated/ side-effecting routes in the collected evidence.
The agentic layer interprets these findings (D6); this module only *detects*,
so it works with Ollama down and is unit-testable.
"""
import math
import os
import re
import stat
import subprocess
import time

SEVERITIES = ("info", "low", "medium", "high", "critical")

# Text-file extensions worth scanning; binaries (.db/.pcap) are skipped.
TEXT_EXTS = {".json", ".jsonl", ".md", ".txt", ".log", ".csv", ".yaml",
             ".yml", ".env", ".ini", ".toml", ".py", ".js"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "pcaps"}
MAX_BYTES = 512 * 1024

_SECRET_PATTERNS = [
    ("private_key", "critical", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("aws_access_key", "critical", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("jwt", "high", re.compile(r"\beyJ[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\.[A-Za-z0-9_\-]{8,}\b")),
    ("bearer_token", "high", re.compile(r"(?i)\bauthorization\b\s*[:=]\s*['\"]?bearer\s+[A-Za-z0-9._\-]{12,}")),
    ("api_key_assignment", "high", re.compile(r"(?i)\b(?:api[_-]?key|secret|password|passwd|access[_-]?token)\b\s*[:=]\s*['\"]?[A-Za-z0-9._\-]{8,}")),
    ("health_phi", "high", re.compile(r"(?i)\b(?:diagnosis|prescription|patient[_ ]?(?:id|name|record)|medical record|social security|ssn)\b")),
    ("email", "medium", re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b")),
    ("private_ip", "low", re.compile(r"\b(?:10\.\d{1,3}|192\.168|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b")),
]
_ENTROPY_TOKEN = re.compile(r"[A-Za-z0-9+/=_\-]{32,}")
_ENTROPY_MIN = 3.6

# Prompt-injection / jailbreak phrasing, checked against untrusted prompt text
# before it is fed to the reconstruction LLM (D1).
_INJECTION_PATTERNS = [
    ("override_instructions", "high", re.compile(
        r"(?i)\b(?:ignore|disregard|forget|override)\b[^.\n]{0,24}\b(?:previous|prior|above|earlier|all|any)\b[^.\n]{0,16}\b(?:instruction|prompt|rule|direction)s?\b")),
    ("new_instructions", "high", re.compile(
        r"(?i)\b(?:new|updated|revised|real)\b\s+(?:instruction|system prompt|rules)s?\b")),
    ("reveal_prompt", "high", re.compile(
        r"(?i)\b(?:reveal|print|show|repeat|leak|output)\b[^.\n]{0,24}\b(?:system prompt|your (?:instructions|prompt|rules)|the prompt)\b")),
    ("role_hijack", "medium", re.compile(
        r"(?i)\b(?:you are now|from now on|act as|pretend to be|behave as)\b")),
    ("chat_role_marker", "medium", re.compile(
        r"(?i)(?:<\|(?:im_start|im_end|system|assistant|user)\|>|\[/?(?:INST|SYS)\]|<\|system\|>|^\s*#{2,}\s*(?:system|assistant)\b)")),
    ("jailbreak", "high", re.compile(
        r"(?i)\b(?:jailbreak|do anything now|DAN mode|developer mode enabled)\b")),
]
_HAS_LOWER = re.compile(r"[a-z]")
_HAS_UPPER = re.compile(r"[A-Z]")
_HAS_DIGIT = re.compile(r"\d")


def _looks_random(tok: str) -> bool:
    """Random-looking: long, entropy-rich, mixed classes and NOT prose.

    Hyphenated lowercase phrases ("the-quick-brown-fox…") score high entropy
    but have <2 uppercase letters; requiring two uppercase letters keeps real
    base64-ish secrets while dropping English words.
    """
    up = len(_HAS_UPPER.findall(tok))
    return (len(tok) >= 32 and up >= 2 and _HAS_LOWER.search(tok)
            and _HAS_DIGIT.search(tok) and shannon_entropy(tok) >= _ENTROPY_MIN)


def shannon_entropy(s: str) -> float:
    if not s:
        return 0.0
    counts: dict[str, int] = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def redact(value: str) -> str:
    """Keep a few leading/trailing chars; never echo a full secret."""
    value = value.strip()
    if len(value) <= 8:
        return value[:2] + "***"
    return f"{value[:4]}…{value[-2:]}"


def _finding(kind, severity, source, line, match):
    return {"kind": kind, "severity": severity, "source": source,
            "line": line, "match": redact(match)}


def scan_text(text: str, source: str = "") -> list[dict]:
    """Scan one text blob. Returns de-duplicated findings."""
    out: list[dict] = []
    seen: set[tuple] = set()
    for i, line in enumerate(text.splitlines(), 1):
        for kind, sev, rx in _SECRET_PATTERNS:
            for m in rx.finditer(line):
                key = (kind, m.group(0), i)
                if key in seen:
                    continue
                seen.add(key)
                out.append(_finding(kind, sev, source, i, m.group(0)))
                break
        for m in _ENTROPY_TOKEN.finditer(line):
            tok = m.group(0)
            if _looks_random(tok):
                key = ("high_entropy", tok, i)
                if key in seen:
                    continue
                seen.add(key)
                out.append(_finding("high_entropy", "high", source, i, tok))
        for kind, sev, rx in _INJECTION_PATTERNS:
            m = rx.search(line)
            if m:
                key = (kind, m.group(0), i)
                if key in seen:
                    continue
                seen.add(key)
                # injection text is attack evidence (not a secret) — keep it
                out.append({"kind": "prompt_injection:" + kind, "severity": sev,
                            "source": source, "line": i, "match": m.group(0)})
    return out


def scan_injection(text: str, source: str = "") -> list[dict]:
    """Prompt-injection findings (match kept verbatim — it is attack evidence)."""
    out: list[dict] = []
    for i, line in enumerate(str(text).splitlines(), start=1):
        for kind, sev, rx in _INJECTION_PATTERNS:
            m = rx.search(line)
            if m:
                out.append({"kind": "prompt_injection:" + kind, "severity": sev,
                            "source": source, "line": i, "match": m.group(0)})
    return out


def injection_risk(text: str) -> int:
    """0=clean, else max severity rank (1 medium, 2 high) — for a quick flag."""
    rank = {"low": 1, "medium": 1, "high": 2, "critical": 3}
    return max((rank.get(f["severity"], 0) for f in scan_injection(text)), default=0)


def scan_path(path: str, source: str | None = None) -> list[dict]:
    """Scan a single file if it is a small-ish text file, else []."""
    ext = os.path.splitext(path)[1].lower()
    if ext not in TEXT_EXTS:
        return []
    try:
        if os.path.getsize(path) > MAX_BYTES:
            return []
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            raw = fh.read()
    except OSError:
        return []
    if "\x00" in raw[:4096]:
        return []
    return scan_text(raw, source if source is not None else path)


def scan_tree(root: str, subpaths: list[str] | None = None) -> list[dict]:
    """Scan text files under `root` (optionally only the given subpaths)."""
    findings: list[dict] = []
    targets = [os.path.join(root, s) for s in subpaths] if subpaths else [root]
    for target in targets:
        for dirpath, dirnames, filenames in os.walk(target):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in sorted(filenames):
                fp = os.path.join(dirpath, fn)
                rel = os.path.relpath(fp, root)
                findings.extend(scan_path(fp, rel))
    return findings


def permission_findings(root: str, subpaths: list[str] | None = None) -> list[dict]:
    """Flag evidence files that are group/other readable (want 0600/0640)."""
    out: list[dict] = []
    targets = [os.path.join(root, s) for s in subpaths] if subpaths else [root]
    for target in targets:
        for dirpath, dirnames, filenames in os.walk(target):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fn in sorted(filenames):
                fp = os.path.join(dirpath, fn)
                try:
                    mode = stat.S_IMODE(os.stat(fp).st_mode)
                except OSError:
                    continue
                if mode & 0o077:
                    sev = "high" if mode & 0o022 else "medium"
                    out.append({"kind": "world_readable", "severity": sev,
                                "source": os.path.relpath(fp, root),
                                "mode": format(mode, "04o")})
    return out


def git_tracked_under(root: str, subpath: str) -> list[str]:
    """Return repo-relative paths git tracks under `subpath` ([] if no git)."""
    try:
        r = subprocess.run(["git", "-C", root, "ls-files", "--", subpath],
                           capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.SubprocessError):
        return []
    if r.returncode != 0:
        return []
    return [ln for ln in r.stdout.splitlines() if ln.strip()]


_SIDE_EFFECTING = {"/api/investigate", "/api/live/start", "/api/live/stop",
                   "/api/runs", "/api/security/scan", "/api/reports/run"}


def audit_exposure(app) -> list[dict]:
    """Route-level D3 audit: auth, side-effecting verbs, enumeration."""
    out: list[dict] = []
    paths: dict[str, set] = {}
    for r in getattr(app, "routes", []):
        methods = getattr(r, "methods", None)
        if methods:
            paths.setdefault(getattr(r, "path", ""), set()).update(methods)

    for p in sorted(_SIDE_EFFECTING & set(paths)):
        if "GET" in paths[p]:
            out.append({"kind": "side_effecting_get", "severity": "high",
                        "source": p, "detail": "mutating route also served over GET"})

    sensitive = [p for p in paths if p.startswith("/api/")
                 and p not in ("/api/overview", "/api/health")]
    if sensitive:
        out.append({"kind": "no_auth", "severity": "high", "source": "dashboard",
                    "detail": f"{len(sensitive)} /api routes served without authentication",
                    "paths": sorted(sensitive)[:12]})
    if "/api/evidence" in paths or "/api/evidence/file" in paths:
        out.append({"kind": "evidence_enumeration", "severity": "medium",
                    "source": "/api/evidence",
                    "detail": "evidence can be listed/downloaded without auth"})
    return out


def summarize(findings: list[dict]) -> dict:
    counts = {s: 0 for s in SEVERITIES}
    for f in findings:
        counts[f.get("severity", "info")] = counts.get(f.get("severity", "info"), 0) + 1
    worst = next((s for s in reversed(SEVERITIES) if counts[s]), "info")
    return {"counts": counts, "total": len(findings), "worst": worst}


def run(root: str, subpaths: list[str] | None = None, app=None) -> dict:
    """Full deterministic scan. `root` is the repo/evidence base dir."""
    findings = scan_tree(root, subpaths=subpaths)
    secrets = [f for f in findings if not f["kind"].startswith("prompt_injection:")]
    injections = [f for f in findings if f["kind"].startswith("prompt_injection:")]
    perms = permission_findings(root, subpaths=subpaths)
    tracked = git_tracked_under(root, "evidence")
    exposure = audit_exposure(app) if app is not None else []
    total = secrets + injections + perms + exposure
    counts = {s: sum(1 for f in total if f["severity"] == s) for s in SEVERITIES}
    return {"generated_at": time.time(), "root": root,
            "secrets": secrets, "injections": injections,
            "permissions": perms, "exposure": exposure,
            "tracked_evidence": {"count": len(tracked), "sample": tracked[:20]},
            "summary": summarize(total),
            "totals": {k: v for k, v in counts.items() if v},
            "n_findings": len(total)}