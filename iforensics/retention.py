"""Evidence retention (P5.22): prune what the collectors accumulate.

Snapshots (`fox_services_*.db`), versioned reports and live JSONL logs grow
without bound; only "newest wins" was ever read. Each pruner keeps the N
newest entries (and never touches today's live log), returns what it removed,
and supports dry runs. Wired to `cli.py prune`.
"""
from __future__ import annotations

import glob
import os
import time

from . import config

KEEP_DB = 5
KEEP_REPORTS = 10
KEEP_DAYS = 30


def _prune(paths: list[str], keep: int, dry_run: bool = False) -> list[str]:
    victims = sorted(paths)[:-max(0, keep)] if len(paths) > keep else []
    removed = []
    for p in victims:
        try:
            if not dry_run:
                os.remove(p)
            removed.append(p)
        except OSError:
            continue
    return removed


def prune_snapshots(keep: int = KEEP_DB, dry_run: bool = False,
                    evidence_dir: str | None = None) -> list[str]:
    ev = evidence_dir or config.EVIDENCE_DIR
    return _prune(glob.glob(os.path.join(ev, "fox_services_*.db")), keep, dry_run)


def prune_reports(keep: int = KEEP_REPORTS, dry_run: bool = False,
                  reports_dir: str | None = None) -> dict:
    """Drop oldest versioned reports (whole <id>/ dirs); rebuild the index."""
    from . import unified_report
    out = reports_dir or unified_report.REPORT_DIR
    entries = unified_report.load_index(out)
    victims = entries[:-max(0, keep)] if len(entries) > keep else []
    removed = []
    import shutil
    for e in victims:
        d = os.path.join(out, e.get("id", ""))
        if os.path.isdir(d) and os.path.abspath(d).startswith(os.path.abspath(out) + os.sep):
            try:
                if not dry_run:
                    shutil.rmtree(d)
                removed.append(e["id"])
            except OSError:
                continue
    if removed and not dry_run:
        kept = [e for e in entries if e.get("id") not in set(removed)]
        with open(os.path.join(out, unified_report.INDEX), "w",
                  encoding="utf-8") as f:
            import json
            json.dump(kept, f, indent=1, default=str)
    return {"removed": removed, "kept": max(0, len(entries) - len(removed))}


def prune_live_logs(keep_days: int = KEEP_DAYS, dry_run: bool = False,
                    live_dir: str | None = None) -> list[str]:
    """Drop live JSONL logs older than keep_days (never today's)."""
    ev = live_dir or os.path.join(config.EVIDENCE_DIR, "live")
    cutoff = time.time() - keep_days * 86400
    today = time.strftime("%Y%m%d")
    removed = []
    try:
        names = os.listdir(ev)
    except OSError:
        return removed
    for name in names:
        if not (name.startswith("events-") and name.endswith(".jsonl")):
            continue
        if today in name:
            continue
        p = os.path.join(ev, name)
        try:
            if os.path.getmtime(p) < cutoff:
                if not dry_run:
                    os.remove(p)
                removed.append(p)
        except OSError:
            continue
    return removed
