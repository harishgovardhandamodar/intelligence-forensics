"""Reconstruction fidelity (P5.20): do recovered templates still match traffic?

Completions are NOT logged upstream, so full I/O validation is impossible
without re-running prompts through a model. What IS measurable — pure and
deterministic, no LLM — is whether each recovered `prompts/template_N.txt`
still appears in recently observed prompts for that service, and which
templates have drifted away (matched nothing recently).

Metric is shingle *recall*: |tpl ∩ prompt| / |tpl|, so a short template
found inside a long prompt scores 1.0. A prompt counts as explained when its
best recall over templates clears `MATCH_RECALL`.
"""
from __future__ import annotations

import os
import re

from . import config

_WS = re.compile(r"\s+")
_SLOT = re.compile(r"\{\{[^}]*\}\}|\{[^}]*\}")
EXAMPLE_MARKER = "--- EXAMPLE HEAD ---"
MATCH_RECALL = 0.5
MIN_SHINGLES = 3


def _norm(text: str) -> str:
    text = _SLOT.sub(" ", str(text or ""))
    return _WS.sub(" ", text.strip().lower())


def _shingles(text: str, k: int = 6) -> frozenset:
    words = _norm(text).split()
    if len(words) < k:
        return frozenset([" ".join(words)]) if words else frozenset()
    return frozenset(" ".join(words[i:i + k]) for i in range(len(words) - k + 1))


def _recall(tpl: frozenset, prompt: frozenset) -> float:
    if not tpl or len(tpl) < MIN_SHINGLES:
        return 0.0
    return len(tpl & prompt) / len(tpl)


def load_templates(service: str, recon_dir: str | None = None) -> list[dict]:
    """Template texts for a service (text before the EXAMPLE HEAD marker)."""
    base = recon_dir or config.RECON_DIR
    pdir = os.path.join(base, service, "prompts")
    out = []
    try:
        names = sorted(os.listdir(pdir))
    except OSError:
        return out
    for name in names:
        if not name.endswith(".txt"):
            continue
        try:
            with open(os.path.join(pdir, name), encoding="utf-8",
                      errors="replace") as f:
                text = f.read()
        except OSError:
            continue
        if EXAMPLE_MARKER in text:
            text = text.split(EXAMPLE_MARKER, 1)[0]
        text = text.strip()
        if text:
            out.append({"name": name, "text": text,
                        "shingles": _shingles(text)})
    return out


def score_service(service: str, prompts: list[str],
                  templates: list[dict] | None = None,
                  recon_dir: str | None = None) -> dict:
    """Fidelity of one service's reconstruction against observed prompts."""
    templates = load_templates(service, recon_dir) if templates is None else templates
    prompts = [p for p in (prompts or []) if p and p.strip()]
    if not templates:
        return {"service": service, "templates": 0, "prompts": len(prompts),
                "matched": 0, "match_rate": 0.0, "verdict": "no-templates",
                "drifted": []}
    if not prompts:
        return {"service": service, "templates": len(templates), "prompts": 0,
                "matched": 0, "match_rate": 0.0, "verdict": "no-traffic",
                "drifted": [t["name"] for t in templates]}
    psh = [_shingles(p) for p in prompts]
    used = set()
    matched = 0
    for ps in psh:
        best, name = 0.0, ""
        for t in templates:
            r = _recall(t["shingles"], ps)
            if r > best:
                best, name = r, t["name"]
        if best >= MATCH_RECALL:
            matched += 1
            used.add(name)
    rate = round(matched / len(prompts), 3)
    verdict = "fresh" if rate >= 0.8 else ("drifting" if rate >= 0.4 else "stale")
    return {"service": service, "templates": len(templates),
            "prompts": len(prompts), "matched": matched,
            "match_rate": rate, "verdict": verdict,
            "drifted": sorted(t["name"] for t in templates if t["name"] not in used)}


def score_all(rows: list[dict], recon_dir: str | None = None) -> dict:
    """Fidelity for every reconstructed service present in the rows."""
    by_svc: dict[str, list[str]] = {}
    for r in rows or []:
        by_svc.setdefault(r.get("service") or "unknown", []).append(r.get("prompt") or "")
    services = [score_service(s, p, recon_dir=recon_dir) for s, p in by_svc.items()]
    services.sort(key=lambda s: (s["match_rate"], s["service"]))
    return {"services": services,
            "summary": {"n_services": len(services),
                        "fresh": sum(1 for s in services if s["verdict"] == "fresh"),
                        "drifting": sum(1 for s in services if s["verdict"] == "drifting"),
                        "stale": sum(1 for s in services if s["verdict"] == "stale")}}
