"""Live wiring: tap auto-co-serve + unscored live reconstruction.

Thin framework layer over the engine (`coserve_events`, `live_users`,
`live_report`) and the tap flag (`set_coserve`, `coserve_status`).
Live users are retention-only by construction: truth registration for
`u-live-*` is refused, and `report()` carries no accuracy keys.
"""
from __future__ import annotations


def enable() -> dict:
    """Turn on tap-driven co-serving."""
    from ... import live as _live
    return _live.set_coserve(True)


def disable() -> dict:
    """Turn off tap-driven co-serving."""
    from ... import live as _live
    return _live.set_coserve(False)


def status() -> dict:
    """Co-serve flag + lifetime counters."""
    from ... import live as _live
    return _live.coserve_status()


def users() -> list[dict]:
    """Co-served live services with retention counts."""
    from .. import reconstruction as _eng
    return _eng.live_users(_eng.STATE)


def report(service: str = "", user_id: str = "") -> dict:
    """Unscored live reconstruction for one service (retention + linkage)."""
    from .. import reconstruction as _eng
    uid = (user_id or "").strip()
    if not uid and (service or "").strip():
        uid = _eng.live_user_for(service.strip())
    if not uid:
        raise ValueError("service or user_id required")
    return _eng.live_report(_eng.STATE, uid)
