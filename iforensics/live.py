"""Live tap: sniff what goes in/out of fox-services and reconstruct live.

API-level tap (no root needed): polls the fox gateway's own surfaces —
in-flight queue (IN), completed requests by id delta (OUT), Ollama /api/ps
model load/unload (SYS) — into a rolling event buffer. Anything stacked on
top (rates, progression, scores) reads the buffer, so reconstruction follows
traffic with seconds of lag.

What this is NOT: packet capture. True port-level pcap needs a privileged
sidecar (see docker-compose `pcap` profile). The tap sees what fox chooses
to expose: prompt heads (truncated/masked upstream), tokens, timings —
which is exactly the reconstruction surface, and it works unprivileged
from LAN, tailnet, or inside the container.
"""
import threading
import time
from collections import deque, Counter

from . import fox_client

MAX_EVENTS = 2000
# ids only matter for a few polls (req_limit each); keeping every id ever seen
# is an unbounded leak on a daemon that runs for weeks.
MAX_SEEN = 20000
MAX_INFLIGHT_SEEN = 5000
# a poll is "unhealthy" when fox has not produced a result for this many
# intervals — surfaced in status() so the UI can stop showing a frozen "live".
STALE_INTERVALS = 3


class _BoundedIdSet:
    """A set that evicts oldest-inserted members past *cap*."""

    __slots__ = ("_set", "_order", "cap", "evicted")

    def __init__(self, cap: int):
        self.cap = cap
        self._set: set = set()
        self._order: deque = deque()
        self.evicted = 0

    def __contains__(self, item) -> bool:
        return item in self._set

    def add(self, item) -> None:
        if item in self._set:
            return
        self._set.add(item)
        self._order.append(item)
        while len(self._order) > self.cap:
            self._set.discard(self._order.popleft())
            self.evicted += 1

    def __len__(self) -> int:
        return len(self._set)


def _row_to_event(r: dict, direction: str) -> dict:
    return {
        "t": r.get("completed_at") or r.get("created_at") or r.get("ts") or time.time(),
        "dir": direction,
        "service": r.get("service") or "unknown",
        "model": r.get("chosen_model") or r.get("model") or "?",
        "original_model": r.get("original_model") or "",
        "prompt_head": ((r.get("prompt") or r.get("query") or "")[:220]).replace("\n", " | "),
        "query_type": r.get("query_type") or "",
        "status": r.get("status") or "",
        "prompt_tokens": r.get("prompt_tokens", 0) or 0,
        "completion_tokens": r.get("completion_tokens", 0) or 0,
        "duration_ms": round(r.get("duration_ms", 0) or 0, 1),
        "qid": r.get("id") or r.get("request_id") or "",
    }


class LiveTap(threading.Thread):
    daemon = True

    def __init__(self, interval_s: float = 5.0, req_limit: int = 100):
        super().__init__(name="live-tap")
        self.interval_s = interval_s
        self.req_limit = req_limit
        self.events: deque = deque(maxlen=MAX_EVENTS)
        self.seen_ids = _BoundedIdSet(MAX_SEEN)
        self.seen_inflight = _BoundedIdSet(MAX_INFLIGHT_SEEN)
        self.loaded_models: set = set()
        self.started_at: float | None = None
        self.last_poll_at: float | None = None
        self.polls = 0
        # loss accounting: a full page with no continuity means older
        # completions were never fetched and never counted.
        self.out_seen = 0
        self.out_lost = 0          # lower bound of unseen completions (id gaps)
        self.out_lost_pages = 0    # number of overflow events
        self.out_saturated_polls = 0
        self.last_newest_id = None
        self.errors: list[str] = []
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def stop(self):
        self._stop_event.set()

    def _push(self, ev: dict):
        with self._lock:
            self.events.append(ev)

    def snapshot(self, limit: int = 100) -> list[dict]:
        with self._lock:
            return list(self.events)[-limit:][::-1]

    def rows(self, limit: int = 5000) -> list[dict]:
        """Buffered OUT events reshaped as infer-compatible rows (live window)."""
        with self._lock:
            evs = [e for e in self.events if e["dir"] == "out"]
        rows = []
        for e in evs[-limit:]:
            rows.append({"id": e.get("qid"), "ts": e["t"], "service": e["service"], "model": e["model"],
                         "prompt_tokens": e["prompt_tokens"],
                         "completion_tokens": e["completion_tokens"],
                         "total_tokens": e["prompt_tokens"] + e["completion_tokens"],
                         "duration_ms": e["duration_ms"], "status": e["status"] or "complete",
                         "prompt": e["prompt_head"], "query_type": e["query_type"],
                         "requestor": "user"})
        return rows



    def poll_once(self) -> dict:
        """One tap cycle. Returns counts; never raises."""
        got = {"in": 0, "out": 0, "sys": 0}
        # OUT: completed requests by id delta
        try:
            res = fox_client.llm_requests(limit=self.req_limit)
            batch = res.get("requests") or []
            ids = [r.get("id") for r in batch]
            idset = set(ids)
            prev_newest = self.last_newest_id
            if batch:
                self.last_newest_id = ids[0]
            # --- loss detection -------------------------------------------
            # fox returns newest-first, capped at req_limit. If that page
            # fills up and the id we last saw is no longer in it, every
            # completion that rolled off the page between polls was never
            # fetched — nothing else would ever have noticed. Estimate the
            # roll-off as (id gap since last poll) - (new ids we did catch).
            if len(batch) >= self.req_limit:
                self.out_saturated_polls += 1
                if prev_newest is not None and prev_newest not in idset:
                    newest = ids[0] if ids else None
                    if isinstance(prev_newest, int) and isinstance(newest, int):
                        self.out_lost += max(0, newest - prev_newest - len(batch))
                    self.out_lost_pages += 1
                    self.errors.append(
                        f"out: page overflow (limit={self.req_limit}) — "
                        "older completions missed")
            # ----------------------------------------------------------------
            for r in batch[::-1]:  # oldest first
                rid = r.get("id")
                if rid is None or rid in self.seen_ids:
                    continue
                self.seen_ids.add(rid)
                if self.started_at and (r.get("created_at") or r.get("ts") or 0) < self.started_at - 5:
                    continue  # history predating the tap, not live traffic
                self._push(_row_to_event(r, "out"))
                got["out"] += 1
                self.out_seen += 1
        except Exception as e:  # noqa: BLE001
            self.errors.append(f"requests: {type(e).__name__}")
        # IN: in-flight queue first-seen
        try:
            q = fox_client.llm_queue()
            fq = q.get("fox_queue", q)
            for r in list(fq.get("pending") or []) + list(fq.get("active") or []):
                qid = r.get("id") or r.get("request_id")
                if not qid or qid in self.seen_inflight:
                    continue
                self.seen_inflight.add(qid)
                self._push(_row_to_event(r, "in"))
                got["in"] += 1
        except Exception as e:  # noqa: BLE001
            self.errors.append(f"queue: {type(e).__name__}")
        # SYS: model load/unload diffs
        try:
            ps = fox_client._get("/api/ollama/running")
            models = {m.get("name") or m.get("model") for m in (ps.get("models") or [])}
            for m in models - self.loaded_models:
                self._push({"t": time.time(), "dir": "sys", "service": "ollama",
                            "model": m, "original_model": "", "prompt_head": "loaded into VRAM",
                            "query_type": "", "status": "loaded", "prompt_tokens": 0,
                            "completion_tokens": 0, "duration_ms": 0, "qid": ""})
                got["sys"] += 1
            for m in self.loaded_models - models:
                self._push({"t": time.time(), "dir": "sys", "service": "ollama",
                            "model": m, "original_model": "", "prompt_head": "evicted from VRAM",
                            "query_type": "", "status": "unloaded", "prompt_tokens": 0,
                            "completion_tokens": 0, "duration_ms": 0, "qid": ""})
                got["sys"] += 1
            self.loaded_models = models
        except Exception as e:  # noqa: BLE001
            self.errors.append(f"ps: {type(e).__name__}")
        self.errors = self.errors[-20:]
        self.polls += 1
        self.last_poll_at = time.time()
        return got

    def run(self):
        self.started_at = time.time()
        # baseline: mark current history seen without emitting
        try:
            res = fox_client.llm_requests(limit=self.req_limit)
            batch = res.get("requests") or []
            for r in batch:
                if r.get("id") is not None:
                    self.seen_ids.add(r["id"])
            if batch:
                # anchor continuity so the first live poll can detect loss
                self.last_newest_id = batch[0].get("id")
        except Exception:  # noqa: BLE001
            pass
        try:
            ps = fox_client._get("/api/ollama/running")
            self.loaded_models = {m.get("name") or m.get("model")
                                  for m in (ps.get("models") or [])}
        except Exception:  # noqa: BLE001
            pass
        while not self._stop_event.wait(self.interval_s):
            try:
                self.poll_once()
            except Exception:  # noqa: BLE001 - tap never dies loudly
                pass

    def status(self) -> dict:
        # one lock for the whole snapshot: iterating the deque while the tap
        # thread appends to it can raise "deque mutated during iteration".
        now = time.time()
        with self._lock:
            n = len(self.events)
            recent = list(self.events)[-500:]
        by_svc = Counter(e["service"] for e in recent)
        since = (now - self.last_poll_at) if self.last_poll_at else None
        stale_after = self.interval_s * STALE_INTERVALS
        return {"running": self.is_alive(), "interval_s": self.interval_s,
                "started_at": self.started_at,
                "uptime_s": round(now - self.started_at, 1) if self.started_at else 0,
                "polls": self.polls, "last_poll_at": self.last_poll_at,
                "poll_age_s": round(since, 1) if since is not None else None,
                "stale": bool(since is not None and since > stale_after),
                "events_buffered": n, "recent_by_service": dict(by_svc.most_common(10)),
                "seen_ids": len(self.seen_ids), "seen_ids_evicted": self.seen_ids.evicted,
                "out_seen": self.out_seen, "out_lost": self.out_lost,
                "out_lost_pages": self.out_lost_pages,
                "out_saturated_polls": self.out_saturated_polls,
                "possible_loss": self.out_lost > 0 or self.out_lost_pages > 0,
                "recent_errors": self.errors[-5:]}



def history_rows(service: str, limit: int = 200) -> list[dict]:
    """Recent fox history for one service, same row shape (oldest first)."""
    try:
        res = fox_client.llm_requests(limit=max(limit * 2, 100))
    except Exception:  # noqa: BLE001
        return []
    rows = []
    for r in res.get("requests") or []:
        if (r.get("service") or "") != service:
            continue
        rows.append({"id": r.get("id"), "ts": r.get("ts", 0),
                     "service": r.get("service"), "model": r.get("model"),
                     "prompt_tokens": r.get("prompt_tokens", 0) or 0,
                     "completion_tokens": r.get("completion_tokens", 0) or 0,
                     "total_tokens": r.get("total_tokens", 0) or 0,
                     "duration_ms": r.get("duration_ms", 0) or 0,
                     "status": r.get("status") or "complete",
                     "prompt": r.get("prompt") or "",
                     "query_type": r.get("query_type") or "",
                     "requestor": r.get("requestor") or "user"})
        if len(rows) >= limit:
            break
    return sorted(rows, key=lambda r: r["ts"])

_TAP: LiveTap | None = None
_TAP_LOCK = threading.Lock()


def start(interval_s: float = 5.0) -> dict:
    global _TAP
    with _TAP_LOCK:
        if _TAP and _TAP.is_alive():
            return {"started": False, "reason": "already running", **_TAP.status()}
        _TAP = LiveTap(interval_s=interval_s)
        _TAP.start()
        return {"started": True, **_TAP.status()}


def stop() -> dict:
    global _TAP
    with _TAP_LOCK:
        if _TAP and _TAP.is_alive():
            _TAP.stop()
            _TAP.join(timeout=5)
        _TAP = None
        return {"started": False, "running": False}


def tap() -> LiveTap | None:
    return _TAP if (_TAP and _TAP.is_alive()) else None


def rates(window_s: float = 300) -> dict:
    t = tap()
    if not t:
        return {"running": False, "services": []}
    now = time.time()
    win = [e for e in t.snapshot(MAX_EVENTS) if now - e["t"] <= window_s]
    agg: dict[str, dict] = {}
    for e in win:
        if e["dir"] != "out":
            continue
        a = agg.setdefault(e["service"], {"req": 0, "tok": 0})
        a["req"] += 1
        a["tok"] += e["prompt_tokens"] + e["completion_tokens"]
    mins = window_s / 60
    return {"running": True, "window_s": window_s,
            "services": sorted(
                [{"service": s, "req": v["req"], "tokens": v["tok"],
                  "req_per_min": round(v["req"] / mins, 2),
                  "tok_per_min": round(v["tok"] / mins, 1)} for s, v in agg.items()],
                key=lambda r: -r["req"])}
