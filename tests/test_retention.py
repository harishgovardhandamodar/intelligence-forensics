"""Unit tests for evidence retention pruning (P5.22)."""
import json
import os
import time

from iforensics import retention as ret


def _touch(path, mtime=None):
    with open(path, "w", encoding="utf-8") as f:
        f.write("x")
    if mtime:
        os.utime(path, (mtime, mtime))


def test_prune_snapshots_keeps_newest(tmp_path):
    for i in range(7):
        _touch(os.path.join(str(tmp_path), f"fox_services_2026100{i}.db"))
    _touch(os.path.join(str(tmp_path), "other.txt"))
    removed = ret.prune_snapshots(keep=5, evidence_dir=str(tmp_path))
    assert sorted(os.path.basename(p) for p in removed) == [
        "fox_services_20261000.db", "fox_services_20261001.db"]
    left = sorted(os.listdir(str(tmp_path)))
    assert left == ["fox_services_20261002.db", "fox_services_20261003.db",
                    "fox_services_20261004.db", "fox_services_20261005.db",
                    "fox_services_20261006.db", "other.txt"]


def test_prune_snapshots_dry_run(tmp_path):
    _touch(os.path.join(str(tmp_path), "fox_services_a.db"))
    _touch(os.path.join(str(tmp_path), "fox_services_b.db"))
    removed = ret.prune_snapshots(keep=1, dry_run=True, evidence_dir=str(tmp_path))
    assert len(removed) == 1
    assert len(os.listdir(str(tmp_path))) == 2


def test_prune_reports_rebuilds_index(tmp_path):
    out = str(tmp_path)
    for rid in ("r1", "r2", "r3"):
        os.makedirs(os.path.join(out, rid))
        with open(os.path.join(out, rid, "report.json"), "w") as f:
            f.write("{}")
    with open(os.path.join(out, "index.json"), "w") as f:
        json.dump([{"id": rid, "json": os.path.join(out, rid, "report.json")}
                   for rid in ("r1", "r2", "r3")], f)
    res = ret.prune_reports(keep=2, reports_dir=out)
    assert res == {"removed": ["r1"], "kept": 2}
    assert sorted(os.listdir(out)) == ["index.json", "r2", "r3"]
    idx = json.load(open(os.path.join(out, "index.json")))
    assert [e["id"] for e in idx] == ["r2", "r3"]


def test_prune_live_logs_never_today(tmp_path):
    today = time.strftime("%Y%m%d")
    _touch(os.path.join(str(tmp_path), f"events-{today}.jsonl"))
    old = os.path.join(str(tmp_path), "events-20000101.jsonl")
    _touch(old, mtime=time.time() - 400 * 86400)
    _touch(os.path.join(str(tmp_path), "cursor.json"))
    removed = ret.prune_live_logs(keep_days=30, live_dir=str(tmp_path))
    assert removed == [old]
    assert os.path.exists(os.path.join(str(tmp_path), f"events-{today}.jsonl"))
