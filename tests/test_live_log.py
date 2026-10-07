"""Unit tests for the durable tap log (append-only JSONL + cursor)."""
import json
import os
import re

from iforensics.live import EventLog, _day


def _row(i, ts=1.0, direction="out"):
    return {"t": ts, "dir": direction, "service": "svc", "model": "m",
            "prompt_head": f"p{i}", "qid": i}


def test_append_creates_day_file(tmp_path):
    log = EventLog(str(tmp_path))
    assert log.append(_row(1))
    assert log.appended == 1
    files = log.files()
    assert len(files) == 1
    assert re.fullmatch(r"events-\d{8}\.jsonl", files[0])
    with open(os.path.join(str(tmp_path), files[0])) as f:
        ev = json.loads(f.readline())
    assert ev["qid"] == 1 and ev["dir"] == "out"


def test_append_roundtrip_and_order(tmp_path):
    log = EventLog(str(tmp_path))
    for i in range(5):
        assert log.append(_row(i, ts=100.0 + i))
    got = log.read_events()
    assert [e["qid"] for e in got] == [0, 1, 2, 3, 4]


def test_read_events_since_ts(tmp_path):
    log = EventLog(str(tmp_path))
    for i in range(5):
        log.append(_row(i, ts=100.0 + i))
    got = log.read_events(since_ts=102.0)
    assert [e["qid"] for e in got] == [2, 3, 4]


def test_append_never_raises_on_nonserialisable(tmp_path):
    log = EventLog(str(tmp_path))
    assert log.append(_row(1, ts=1.0))
    assert log.append({"t": 2.0, "bad": object()}) is False
    assert log.errors == 1
    # a bad append must not corrupt the good stream
    assert [e["qid"] for e in log.read_events()] == [1]


def test_cursor_roundtrip_atomic(tmp_path):
    log = EventLog(str(tmp_path))
    assert log.read_cursor() == {}
    log.write_cursor(last_newest_id=42, polls=7, out_lost=3)
    cur = log.read_cursor()
    assert cur["last_newest_id"] == 42 and cur["polls"] == 7
    assert "updated_at" in cur
    assert not os.path.exists(os.path.join(str(tmp_path), "cursor.json.tmp"))


def test_stats_reports_files_and_bytes(tmp_path):
    log = EventLog(str(tmp_path))
    log.append(_row(1, ts=1.0))
    log.append(_row(2, ts=2.0))
    st = log.stats()
    assert st["files"] == 1 and st["bytes"] > 0 and st["appended"] == 2
    assert st["dir"] == str(tmp_path)


def test_day_buckets_by_utc(tmp_path):
    log = EventLog(str(tmp_path))
    log.append(_row(1, ts=0.0))          # 1970-01-01
    log.append(_row(2, ts=86400.0))      # 1970-01-02
    assert len(log.files()) == 2
    assert _day(0.0) == "19700101"