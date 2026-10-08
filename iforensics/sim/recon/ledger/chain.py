"""Framework ledger: append + verify over `iforensics/ledger.py`."""
from __future__ import annotations

from .... import ledger as _ledger


def append(run_id: str, actor: str, action: str, task_id: str = "",
           artifact: str = "", detail: str = "") -> dict:
    """Hash-chained append (artifact hashed when the file exists)."""
    return _ledger.append(run_id, actor=actor, action=action, task_id=task_id,
                          artifact=artifact, detail=detail)


def verify(run_id: str) -> dict:
    """Recompute the chain; tampering is reported at the exact seq."""
    return _ledger.verify(run_id)
