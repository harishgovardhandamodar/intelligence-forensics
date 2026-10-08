"""Mitigations: pure record transforms + curve-flattening measurement.

Each mitigation takes residual records (engine dicts or framework
`Residual`s) and returns redacted copies — inputs are never mutated. `sweep`
reports the with-text fraction before/after, which is the honest,
truth-free proxy for "how much less the insider can read". Accuracy
flattening follows from the same reports the metrics module already
produces; nothing here scores.
"""
from __future__ import annotations

import copy
import re

SSN_RE = re.compile(r"\b9\d{2}-\d{2}-\d{4}\b")
PAN_RE = re.compile(r"\b4242(?: \d{4}){3}\b")
TOKEN_RE = re.compile(r"\b(?:sk-test-[A-Za-z0-9]{24}|ghp_test_[A-Za-z0-9_]{24})\b")
SHAPES = (("ssn", SSN_RE, "[REDACTED-SSN]"),
          ("pan", PAN_RE, "[REDACTED-PAN]"),
          ("token", TOKEN_RE, "[REDACTED-TOKEN]"))


def _text(r) -> str:
    return r["text"] if isinstance(r, dict) else r.text


def _with(r, text=None, meta_extra=None, drop=False):
    if drop:
        return None
    if isinstance(r, dict):
        c = copy.deepcopy(r)
        if text is not None:
            c["text"] = text
        if meta_extra:
            c["meta"] = {**c.get("meta", {}), **meta_extra}
        return c
    from .core.surfaces.base import Residual
    return Residual(surface=r.surface, turn_id=r.turn_id, kind=r.kind,
                    text=r.text if text is None else text,
                    vector=r.vector, linkage_key=r.linkage_key,
                    meta={**r.meta, **(meta_extra or {})})


def with_text_fraction(records: list) -> float:
    """Share of records still carrying text (the flattening yardstick)."""
    rs = list(records or [])
    if not rs:
        return 0.0
    return sum(1 for r in rs if _text(r)) / len(rs)


def cap_turns(records: list, keep_last: int) -> list:
    """Per-user retention cap: keep only the newest `keep_last` turns."""
    rs = list(records or [])
    turns = sorted({(r["turn"] if isinstance(r, dict) else r.turn_id)
                    for r in rs})
    keep = set(turns[-max(0, keep_last):]) if keep_last > 0 else set()
    return [r for r in rs if ((r["turn"] if isinstance(r, dict) else r.turn_id)
                              in keep)]


def never_log_full(records: list, head: int = 180) -> list:
    """Full-prompt keepers degrade to head prefixes (metadata preserved)."""
    out = []
    for r in records or []:
        t = _text(r)
        out.append(r if len(t) <= head else
                   _with(r, text=t[:head],
                         meta_extra={"mitigation": "never-log-full"}))
    return out


def dlp(records: list, mode: str = "audit") -> list:
    """DLP over retained text. off/audit/redact/block.

    audit flags shapes in meta; redact replaces them with same-shape masks;
    block drops the record. `off` returns records unchanged.
    """
    if mode == "off":
        return list(records or [])
    if mode not in ("audit", "redact", "block"):
        raise ValueError(f"dlp mode must be off|audit|redact|block: {mode!r}")
    out = []
    for r in records or []:
        t = _text(r)
        found = sorted({name for name, rx, _ in SHAPES if rx.search(t)})
        if not found:
            out.append(r)
            continue
        if mode == "audit":
            out.append(_with(r, meta_extra={"dlp": "flagged:" + ",".join(found)}))
        elif mode == "redact":
            for name, rx, mask in SHAPES:
                t = rx.sub(mask, t)
            out.append(_with(r, text=t,
                             meta_extra={"dlp": "redacted:" + ",".join(found)}))
        else:
            continue  # block: the insider never sees this row
    return out


def cache_ttl(records: list, ttl_turns: int, current_turn: int) -> list:
    """Drop cache-surface rows older than `ttl_turns` behind `current_turn`."""
    out = []
    for r in records or []:
        surf = r["surface"] if isinstance(r, dict) else r.surface
        turn = r["turn"] if isinstance(r, dict) else r.turn_id
        if surf == "cache" and (current_turn - turn) > ttl_turns:
            continue
        out.append(r)
    return out


def encrypt_embeddings(records: list) -> list:
    """Encryption-at-rest for vectors: vectors withheld (linkage goes dark)."""
    out = []
    for r in records or []:
        surf = r["surface"] if isinstance(r, dict) else r.surface
        if surf != "embeddings":
            out.append(r)
            continue
        if isinstance(r, dict):
            c = copy.deepcopy(r)
            c["meta"] = {k: v for k, v in c.get("meta", {}).items()
                         if k != "vector"}
            out.append(c)
        else:
            from .core.surfaces.base import Residual
            out.append(Residual(surface=r.surface, turn_id=r.turn_id,
                                kind=r.kind, text=r.text, vector=None,
                                linkage_key="", meta=dict(r.meta)))
    return out


def shape_fraction(records: list) -> float:
    """Share of records still carrying a reserved secret shape.

    Redaction keeps text but kills shapes, so the with-text fraction alone
    would call it a no-op — this is the yardstick that actually moves.
    """
    rs = list(records or [])
    if not rs:
        return 0.0
    return sum(1 for r in rs
               if any(rx.search(_text(r)) for _, rx, _ in SHAPES)) / len(rs)


def sweep(records: list, current_turn: int = 0) -> dict:
    """With-text / with-shape fractions under each mitigation (deterministic)."""
    modes = {"baseline": lambda rs: rs,
             "cap_10_turns": lambda rs: cap_turns(rs, 10),
             "never_log_full": never_log_full,
             "dlp_audit": lambda rs: dlp(rs, "audit"),
             "dlp_redact": lambda rs: dlp(rs, "redact"),
             "dlp_block": lambda rs: dlp(rs, "block"),
             "cache_ttl_5": lambda rs: cache_ttl(rs, 5, current_turn),
             "embeddings_encrypted": encrypt_embeddings}
    return {name: {"with_text": with_text_fraction(fn(records)),
                   "with_shapes": shape_fraction(fn(records))}
            for name, fn in modes.items()}
