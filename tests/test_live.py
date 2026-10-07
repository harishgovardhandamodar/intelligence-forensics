"""Unit tests for the live tap: bounded seen-cache, page-overflow loss
detection, and the status() snapshot used by the dashboard."""
import time

from iforensics import live as live_mod
from iforensics.live import _BoundedIdSet, LiveTap


def _row(i, ts=None):
    return {"id": i, "service": "svc", "model": "m", "prompt": f"p{i}",
            "prompt_tokens": 10, "completion_tokens": 5,
            "created_at": ts or time.time()}


class _FakeFox:
    """Return canned pages, newest-first, like fox_client.llm_requests."""

    def __init__(self, pages):
        self.pages = list(pages)
        self.calls = 0

    def __call__(self, **kw):
        self.calls += 1
        return {"requests": self.pages.pop(0)} if self.pages else {"requests": []}


def _tap(after=None, req_limit=5):
    t = LiveTap(interval_s=60, req_limit=req_limit, persist=False)
    t.started_at = time.time()
    # keep tests hermetic: no real HTTP to fox for the SYS model-load poll
    live_mod.fox_client._get = lambda *a, **k: {"models": []}
    if after:
        live_mod.fox_client.llm_requests = after
    return t


def test_bounded_id_set_evicts_oldest():
    b = _BoundedIdSet(3)
    for i in range(10):
        b.add(i)
    assert len(b) == 3
    assert 0 not in b and 7 in b and 9 in b
    assert b.evicted == 7
    # re-adding an existing member must not bump it to the back
    b.add(9)
    assert len(b) == 3 and b.evicted == 7


def test_seen_cache_stays_bounded_across_polls():
    t = LiveTap(interval_s=60, req_limit=3, persist=False)
    t.started_at = time.time()
    live_mod.fox_client._get = lambda *a, **k: {"models": []}
    t._fake = _FakeFox([[{"id": 10 + i, "service": "s", "prompt": "x",
                          "created_at": time.time()} for i in range(6)]])
    live_mod.fox_client.llm_requests = t._fake
    t.poll_once()
    assert len(t.seen_ids) == 6
    assert t.seen_ids.cap == live_mod.MAX_SEEN
    assert t.seen_ids.evicted == 0


def test_poll_emits_new_events_oldest_first():
    t = _tap(after=_FakeFox([[{"id": 10, "service": "a+b", "prompt": "q",
                              "prompt_tokens": 1, "completion_tokens": 2,
                              "created_at": time.time()},
                             {"id": 9, "service": "a+b", "prompt": "q",
                              "prompt_tokens": 1, "completion_tokens": 2,
                              "created_at": time.time()}]]))
    got = t.poll_once()
    assert got == {"in": 0, "out": 2, "sys": 0}
    evs = [e for e in t.events if e["dir"] == "out"]
    assert [e["qid"] for e in evs] == [9, 10]


def test_saturating_overflow_counts_lost_and_flags():
    def make(ids):
        return [{"id": i, "service": "s", "prompt": "q",
                 "created_at": time.time()} for i in ids]

    t = _tap(after=_FakeFox([make([10, 9, 8, 7, 6]),   # poll 1: baseline
                             make([20, 19, 18, 17, 16]),  # poll 2: roll-off
                             make([25, 24, 23, 22, 21]),  # poll 3: no gap
                             make([40, 39, 38, 37, 25]),  # poll 4: continuity
                             ]), req_limit=5)
    t.poll_once(); t.poll_once(); t.poll_once(); t.poll_once()
    st = t.status()
    # poll 2: prev 10 dropped off a full page of 20..16 -> est lost 20-10-5=5
    assert st["out_lost"] == 5
    assert st["out_lost_pages"] == 2
    assert st["possible_loss"] is True
    # poll 4 re-sees id 25 from poll 3, so only +4 unique out events -> 19
    assert st["out_seen"] == 19
    assert st["events_buffered"] == 19
    assert st["recent_errors"]


def test_continuity_no_false_positive():
    def make(ids):
        return [{"id": i, "service": "s", "prompt": "q",
                 "created_at": time.time()} for i in ids]

    t = _tap(after=_FakeFox([make([10, 9, 8, 7, 6]),     # baseline newest=10
                             make([15, 14, 13, 12, 10]),  # 10 still in page
                             ]), req_limit=5)
    t.poll_once(); t.poll_once()
    assert t.status()["out_lost"] == 0
    assert t.status()["out_lost_pages"] == 0
    assert t.status()["possible_loss"] is False


def test_status_snapshot_schema():
    t = _tap()
    st = t.status()
    for k in ("running", "interval_s", "polls", "events_buffered",
              "seen_ids", "seen_ids_evicted", "out_seen", "out_lost",
              "out_lost_pages", "out_saturated_polls", "possible_loss",
              "recent_errors", "stale", "poll_age_s"):
        assert k in st, k


def test_stale_flag_after_missed_polls():
    t = _tap()
    t.last_poll_at = time.time() - 10 * t.interval_s * live_mod.STALE_INTERVALS
    assert t.status()["stale"] is True


def test_in_out_join_sets_queue_ms():
    t = LiveTap(interval_s=60, req_limit=5, persist=False)
    t.started_at = time.time()
    now = time.time()
    live_mod.fox_client._get = lambda *a, **k: {"models": []}
    live_mod.fox_client.llm_requests = _FakeFox([[]])
    live_mod.fox_client.llm_queue = lambda *a, **k: {
        "fox_queue": {"pending": [{"id": 10, "service": "s",
                                   "prompt": "q", "created_at": now}], "active": []}}
    t.poll_once()
    assert 10 in t.inflight
    live_mod.fox_client.llm_requests = _FakeFox([
        [{"id": 10, "service": "s", "prompt": "q", "created_at": now + 2.0}]])
    live_mod.fox_client.llm_queue = lambda *a, **k: {
        "fox_queue": {"pending": [], "active": []}}
    t.poll_once()
    out = [e for e in t.events if e["dir"] == "out"][0]
    assert out["queued"] is True
    assert 1900 <= out["queue_ms"] <= 2100
    assert t.status()["queue_joined"] == 1
    assert t.rows()[0]["queue_ms"] == out["queue_ms"]


def test_snapshot_delta_by_seq():
    t = LiveTap(interval_s=60, persist=False)
    t.started_at = time.time()
    t._push({"t": 1.0, "dir": "out", "service": "s"})
    t._push({"t": 2.0, "dir": "out", "service": "s"})
    first, second = [e["seq"] for e in t.events]
    assert first < second
    assert [e["seq"] for e in t.snapshot(since_seq=first)] == [second]
    assert [e["seq"] for e in t.snapshot(since_seq=second)] == []
    assert t.last_seq() == second


def test_poll_persists_events_and_cursor(tmp_path):
    t = LiveTap(interval_s=60, req_limit=5, persist=True, log_dir=str(tmp_path))
    t.started_at = time.time()
    live_mod.fox_client.llm_requests = _FakeFox([[
        {"id": 10, "service": "s", "prompt": "q", "created_at": time.time()},
        {"id": 9, "service": "s", "prompt": "q", "created_at": time.time()},
    ]])
    live_mod.fox_client._get = lambda *a, **k: {"models": []}
    t.poll_once()
    on_disk = t.log.read_events()
    assert [e["qid"] for e in on_disk] == [9, 10]
    cur = t.log.read_cursor()
    assert cur["last_newest_id"] == 10
    assert t.status()["persisted"]["files"] == 1
    # objects would fail json.dumps for the real log — none here
    assert t.log.errors == 0