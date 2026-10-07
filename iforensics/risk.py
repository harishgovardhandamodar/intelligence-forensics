"""Per-service data-exposure risk scoring (D5).

Everything above the boundary is inflow: prompts from every service. Some of
that inflow is more dangerous to hold than others — secrets/PII that should
have been masked, jailbreak phrasing from a compromised client, token volumes
that don't fit the service, and the same prompt arriving from two services
(a template that leaked across a trust boundary).

`service_risk(rows)` ranks services on four transparent signals and returns a
0-100 score. No LLM, no hiding: every signal is counted and exposed so a human
can disagree with the number.
"""
from __future__ import annotations

import math
import re
from collections import defaultdict

from . import security

_WS = re.compile(r"\s+")
_SAT = 25.0  # PII
_INJ = 25.0  # injection
_VOL = 20.0  # anomalous volume
_LEAK = 30.0  # cross-service template leakage

BANDS = ((75, "critical"), (50, "high"), (25, "medium"), (0, "low"))


def _band(score: float) -> str:
    for bound, name in BANDS:
        if score >= bound:
            return name
    return "low"


def _norm(prompt: str) -> str:
    return _WS.sub(" ", str(prompt or "").strip().lower())[:2000]


def _shingles(prompt: str, k: int = 6) -> frozenset:
    words = _norm(prompt).split()
    if len(words) < k:
        return frozenset([" ".join(words)]) if words else frozenset()
    return frozenset(" ".join(words[i:i + k]) for i in range(len(words) - k + 1))


def _sat(x: float, k: float) -> float:
    return 1.0 - math.exp(-max(0.0, x) / k)


def _jaccard(a: frozenset, b: frozenset) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    return inter / (len(a) + len(b) - inter)


def _volume_stats(rows: list[dict]) -> tuple[float, float]:
    """Corpus mean and std of prompt_tokens (for per-service z-scores)."""
    toks = [float(r.get("prompt_tokens") or 0) for r in rows]
    if len(toks) < 2:
        return 0.0, 0.0
    mean = sum(toks) / len(toks)
    var = sum((t - mean) ** 2 for t in toks) / len(toks)
    return mean, math.sqrt(var)


def _volume_z(rows: list[dict], mean: float, std: float) -> float:
    """Max |z| among a service's rows against the corpus distribution."""
    if std <= 0 or not rows:
        return 0.0
    return max(abs(float(r.get("prompt_tokens") or 0) - mean) / std for r in rows)


def _cross_leak(by_service: dict[str, list[dict]], thresh: float = 0.7,
                rep_cap: int = 80) -> dict[str, int]:
    """Count, per service, prompts also seen (exactly or near-dup) elsewhere."""
    norm = {svc: [_norm(r.get("prompt")) for r in rows] for svc, rows in by_service.items()}
    sigs = {svc: [_shingles(p) for p in prompts] for svc, prompts in norm.items()}
    leak: dict[str, int] = defaultdict(int)
    services = list(by_service)
    for svc in services:
        others = [p for other in services if other != svc for p in norm[other]]
        other_sigs = [s for other in services if other != svc for s in sigs[other]]
        other_exact = set(others)
        reps = other_sigs[:rep_cap] if len(other_sigs) > rep_cap else other_sigs
        for p, s in zip(norm[svc], sigs[svc]):
            if p and p in other_exact:
                leak[svc] += 1
                continue
            if s and any(_jaccard(s, o) >= thresh for o in reps):
                leak[svc] += 1
    return leak


def service_risk(rows: list[dict]) -> dict:
    """Rank services by inflow risk. Returns {services: [...], summary: {...}}."""
    by_service: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by_service[str(r.get("service") or "unknown")].append(r)

    leak = _cross_leak(by_service)
    mean, std = _volume_stats(rows)

    services = []
    for svc, srows in by_service.items():
        pii = inj = 0
        for r in srows:
            prompt = str(r.get("prompt") or "")
            for f in security.scan_text(prompt, source=f"{svc}:{r.get('id','')}"):
                if str(f.get("kind", "")).startswith("prompt_injection:"):
                    inj += 1
                else:
                    pii += 1
        n = len(srows)
        vol = _volume_z(srows, mean, std)
        score = round(min(100.0, _SAT * _sat(pii, 2) + _INJ * _sat(inj, 1.5)
                          + _VOL * _sat(vol, 3) + _LEAK * _sat(leak.get(svc, 0), 2)), 1)
        services.append({
            "service": svc, "n": n, "score": score, "band": _band(score),
            "signals": {"pii": pii, "injection": inj,
                        "volume_z": round(vol, 2), "cross_service_reuse": leak.get(svc, 0)},
        })
    services.sort(key=lambda s: (-s["score"], s["service"]))
    worst = services[0]["band"] if services else "low"
    return {"services": services,
            "summary": {"n_services": len(services),
                        "worst": worst,
                        "critical": sum(1 for s in services if s["band"] == "critical"),
                        "high": sum(1 for s in services if s["band"] == "high")}}