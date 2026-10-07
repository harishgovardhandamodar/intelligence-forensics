"""Time-series bucketing for tap events and history rows.

The dashboard shows instantaneous rates; reconstruction/traffic review needs
how volume and tokens moved over a window. This is pure and deterministic so
the live tap and the durable log share one aggregation, and charts/tests do
not reimplement floor-by-bucket arithmetic.
"""
import re
import time

_DUR = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(s|m|h|d|w)?\s*$", re.I)
_UNIT = {"": 1, "s": 1, "m": 60, "h": 3600, "d": 86400, "w": 604800}
# a "complete" status is not an error; anything else non-empty counts
_OK = {"", "complete", "completed", "ok", "success", "done"}


def parse_duration(text: str, default_unit: str = "s") -> float:
    """'30s' / '5m' / '2h' / '90' -> seconds. Raises ValueError."""
    m = _DUR.match(str(text or ""))
    if not m:
        raise ValueError(f"bad duration: {text!r}")
    unit = (m.group(2) or default_unit).lower()
    return float(m.group(1)) * _UNIT[unit]


def _t(e: dict) -> float:
    return e.get("t") or e.get("ts") or e.get("created_at") or 0 or 0


def bucketize(events: list[dict], bucket_s: float = 60, window_s: float | None = None,
              now: float | None = None, services: set | None = None,
              fill: bool | None = None) -> dict:
    """Aggregate OUT events into fixed buckets (ascending).

    Each bucket: {t, req, prompt_tokens, completion_tokens, total_tokens,
    errors, services: {name: {req, tokens}}}. `fill` (default: on when a
    window is given) inserts zero buckets so charts show real gaps, not a
    straight line between distant points.
    """
    now = now if now is not None else time.time()
    bucket_s = max(1.0, float(bucket_s))
    start = (now - window_s) if window_s else None
    if fill is None:
        fill = window_s is not None

    buckets: dict[int, dict] = {}
    for e in events:
        if (e.get("dir") or "out") != "out":
            continue
        t = _t(e)
        if not t or (start is not None and t < start):
            continue
        svc = e.get("service") or "unknown"
        if services and svc not in services:
            continue
        key = int(t // bucket_s) * int(bucket_s)
        b = buckets.get(key)
        if b is None:
            b = buckets[key] = {"t": key, "req": 0, "prompt_tokens": 0,
                                "completion_tokens": 0, "total_tokens": 0,
                                "errors": 0, "services": {}}
        pt = e.get("prompt_tokens", 0) or 0
        ct = e.get("completion_tokens", 0) or 0
        b["req"] += 1
        b["prompt_tokens"] += pt
        b["completion_tokens"] += ct
        b["total_tokens"] += pt + ct
        if (e.get("status") or "").lower() not in _OK:
            b["errors"] += 1
        sb = b["services"].setdefault(svc, {"req": 0, "tokens": 0})
        sb["req"] += 1
        sb["tokens"] += pt + ct

    if fill and start is not None:
        k = int(start // bucket_s) * int(bucket_s)
        end = int(now // bucket_s) * int(bucket_s)
        while k <= end:
            buckets.setdefault(k, {"t": k, "req": 0, "prompt_tokens": 0,
                                   "completion_tokens": 0, "total_tokens": 0,
                                   "errors": 0, "services": {}})
            k += int(bucket_s)

    rows = sorted(buckets.values(), key=lambda b: b["t"])
    totals = {"req": sum(b["req"] for b in rows),
              "total_tokens": sum(b["total_tokens"] for b in rows),
              "errors": sum(b["errors"] for b in rows)}
    return {"bucket_s": bucket_s, "window_s": window_s, "now": now,
            "n_buckets": len(rows), "totals": totals, "buckets": rows}