"""Active DLP for the simulation gateway (P8 extension).

A policy engine standing between queries and the embedding store: every
prompt and response is scanned for secret-shaped spans, and the configured
action applies — `audit` (log only), `redact` (substitute spans in the
stored text), or `block` (refuse + store only a blocked-attempt record).
`off` disables enforcement for baseline runs.

This is what turns the sim from an attack demo into a mitigation study:
same scenarios, DLP on, and the report curve shows exactly how much less
is recoverable. Every decision is logged to an interception journal the
report surfaces (counts by action/rule), so policy effect is measurable,
not asserted.
"""
from __future__ import annotations

import re

MODES = ("off", "audit", "redact", "block")

# Full-secret shapes (the unmasked values DLP must catch, not just * masks).
_PATTERNS = [
    ("ssn", re.compile(r"\b\d{3}-\d{2}-\d{4}\b")),
    ("pan", re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b")),
    ("api_key", re.compile(r"\bsk-(?:test-|proj-|live-)?[A-Za-z0-9]{8,}\b")),
    ("aws_key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("secret_assignment", re.compile(
        r"(?i)\b(?:password|passwd|secret|api[_-]?key|access[_-]?token)\b\s*[:=]\s*\S{4,}")),
    ("masked_span", re.compile(r"[A-Za-z0-9*/.!@#%-]*\*[A-Za-z0-9*/.!@#% *-]*[A-Za-z0-9*!@#%]")),
]


def scan(text: str) -> list[dict]:
    """Secret-shaped spans in a text: [{kind, span, start, end}]."""
    out, seen = [], set()
    for kind, rx in _PATTERNS:
        for m in rx.finditer(text or ""):
            key = (m.start(), m.end(), kind)
            if key in seen:
                continue
            seen.add(key)
            out.append({"kind": kind, "span": m.group(0),
                        "start": m.start(), "end": m.end()})
    out.sort(key=lambda f: (f["start"], f["end"]))
    return out


class Policy:
    """Enforcement policy: mode + per-kind actions (default per mode)."""

    def __init__(self, mode: str = "off", actions: dict | None = None):
        if mode not in MODES:
            raise ValueError(f"unknown DLP mode: {mode!r}")
        self.mode = mode
        self.actions = dict(actions or {})
        self.journal: list[dict] = []

    def action_for(self, kind: str) -> str:
        if self.mode == "off":
            return "allow"
        if kind in self.actions:
            return self.actions[kind]
        return {"audit": "audit", "redact": "redact",
                "block": "block"}[self.mode]

    def inspect(self, text: str, where: str) -> dict:
        """Scan one text; returns {text, blocked, findings} with policy applied."""
        if self.mode == "off":
            return {"text": text, "blocked": False, "findings": []}
        findings = scan(text)
        if not findings:
            return {"text": text, "blocked": False, "findings": []}
        for f in findings:
            f["action"] = self.action_for(f["kind"])
            self.journal.append({"where": where, **f})
        if any(f["action"] == "block" for f in findings):
            return {"text": "", "blocked": True, "findings": findings}
        if any(f["action"] == "redact" for f in findings):
            return {"text": self._redact(text, findings),
                    "blocked": False, "findings": findings}
        return {"text": text, "blocked": False, "findings": findings}

    @staticmethod
    def _redact(text: str, findings: list[dict]) -> str:
        spans = sorted({(f["start"], f["end"], f["kind"]) for f in findings
                        if f["action"] == "redact"}, reverse=True)
        for start, end, kind in spans:
            text = text[:start] + f"[REDACTED:{kind}]" + text[end:]
        return text

    def summary(self) -> dict:
        by_action: dict[str, int] = {}
        for f in self.journal:
            by_action[f["action"]] = by_action.get(f["action"], 0) + 1
        return {"mode": self.mode, "interceptions": len(self.journal),
                "by_action": by_action}
