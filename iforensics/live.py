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
import datetime
import json
import os
import threading
import time
from collections import deque, Counter

from . import config, fox_client

MAX_EVENTS = 2000
# ids only matter for a few polls (req_limit each); keeping every id ever seen
# is an unbounded leak on a daemon that runs for weeks.
MAX_SEEN = 20000
MAX_INFLIGHT_SEEN = 5000
MAX_INFLIGHT = 2000
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


def _day(ts: float) -> str:
    return datetime.datetime.utcfromtimestamp(ts).strftime("%Y%m%d")


class EventLog:
    """Append-only JSONL of tap events (one file per UTC day) + a cursor file.

    The rolling deque makes the live window ephemeral; this makes it durable.
    On restart the cursor resumes continuity, and the reporter can replay
    exactly what the tap observed — including the overflow gaps fox's DB
    cannot tell us about. Appends are line-flushed so a hard kill loses at
    most the in-flight poll.
    """

    def __init__(self, base_dir: str | None = None):
        self.dir = base_dir or os.path.join(config.EVIDENCE_DIR, "live")
        self.cursor_path = os.path.join(self.dir, "cursor.json")
        self._lock = threading.Lock()
        self._fh = None
        self._fh_day: str | None = None
        self.appended = 0
        self.errors = 0
        try:
            os.makedirs(self.dir, exist_ok=True)
        except Exception:  # noqa: BLE001
            pass

    def _open(self, day: str):
        if self._fh and self._fh_day == day:
            return self._fh
        if self._fh:
            try:
                self._fh.close()
            except Exception:  # noqa: BLE001
                pass
        self._fh = open(os.path.join(self.dir, f"events-{day}.jsonl"),
                        "a", encoding="utf-8")
        self._fh_day = day
        return self._fh

    def append(self, ev: dict) -> bool:
        try:
            line = json.dumps(ev, ensure_ascii=False, separators=(",", ":"))
            with self._lock:
                fh = self._open(_day(ev.get("t") or time.time()))
                fh.write(line + "\n")
                fh.flush()
                self.appended += 1
            return True
        except Exception:  # noqa: BLE001
            self.errors += 1
            return False

    def write_cursor(self, **kw) -> None:
        try:
            tmp = self.cursor_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump({"updated_at": time.time(), **kw}, f)
            os.replace(tmp, self.cursor_path)  # atomic: no torn cursor
        except Exception:  # noqa: BLE001
            pass

    def read_cursor(self) -> dict:
        try:
            with open(self.cursor_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception:  # noqa: BLE001
            return {}

    def files(self) -> list[str]:
        try:
            return sorted(f for f in os.listdir(self.dir)
                          if f.startswith("events-") and f.endswith(".jsonl"))
        except Exception:  # noqa: BLE001
            return []

    def stats(self) -> dict:
        files = self.files()
        nbytes = 0
        for f in files:
            try:
                nbytes += os.path.getsize(os.path.join(self.dir, f))
            except OSError:
                continue
        return {"dir": self.dir, "files": len(files), "bytes": nbytes,
                "appended": self.appended, "errors": self.errors,
                "cursor": self.read_cursor()}

    def read_events(self, day: str | None = None, limit: int = 10000,
                    since_ts: float = 0.0) -> list[dict]:
        names = [f"events-{day}.jsonl"] if day else self.files()
        out: list[dict] = []
        for name in names:
            try:
                with open(os.path.join(self.dir, name), encoding="utf-8") as f:
                    for line in f:
                        try:
                            ev = json.loads(line)
                        except Exception:  # noqa: BLE001
                            continue
                        if (ev.get("t") or 0) >= since_ts:
                            out.append(ev)
            except Exception:  # noqa: BLE001
                continue
        return out[-limit:] if not since_ts else out

    def close(self) -> None:
        with self._lock:
            if self._fh:
                try:
                    self._fh.close()
                except Exception:  # noqa: BLE001
                    pass
                self._fh = None


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

    def __init__(self, interval_s: float = 5.0, req_limit: int = 100,
                 persist: bool = True, log_dir: str | None = None):
        super().__init__(name="live-tap")
        self.interval_s = interval_s
        self.req_limit = req_limit
        self.events: deque = deque(maxlen=MAX_EVENTS)
        self.log = EventLog(log_dir) if persist else None
        self.resumed_cursor: dict = {}
        self.seen_ids = _BoundedIdSet(MAX_SEEN)
        self.seen_inflight = _BoundedIdSet(MAX_INFLIGHT_SEEN)
        # qid -> IN event, to join a later OUT completion back to its arrival
        # and measure queue time (fox does not record it).
        self.inflight: dict = {}
        self._inflight_order: deque = deque()
        self._seq = 0
        self.queue_ms_seen = 0
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
        self.resumed_from: dict | None = None
        self.errors: list[str] = []
        self._stop_event = threading.Event()
        self._lock = threading.Lock()

    def stop(self):
        self._stop_event.set()
        if getattr(self, "log", None):
            self.log.close()

    def _push(self, ev: dict):
        with self._lock:
            self._seq += 1
            ev["seq"] = self._seq
            self.events.append(ev)
        if self.log:
            self.log.append(ev)

    def _remember_inflight(self, ev: dict):
        qid = ev.get("qid")
        if not qid:
            return
        self.inflight[qid] = ev
        self._inflight_order.append(qid)
        while len(self._inflight_order) > MAX_INFLIGHT:
            old = self._inflight_order.popleft()
            self.inflight.pop(old, None)

    def _join_out(self, ev: dict):
        """Attach queue_ms to an OUT event when its IN arrival was seen."""
        qid = ev.get("qid")
        in_ev = self.inflight.pop(qid, None) if qid else None
        if not in_ev:
            return
        q = (ev["t"] or 0) - (in_ev["t"] or 0)
        if q >= 0:
            ev["queue_ms"] = round(q * 1000.0, 1)
            ev["queued"] = True
            in_ev["resolved"] = True
            in_ev["queue_ms"] = ev["queue_ms"]
            self.queue_ms_seen += 1

    def snapshot(self, limit: int = 100, since_seq: int = 0) -> list[dict]:
        with self._lock:
            if since_seq:
                evs = [e for e in self.events if e.get("seq", 0) > since_seq]
                return evs[-limit:]
            return list(self.events)[-limit:][::-1]

    def last_seq(self) -> int:
        with self._lock:
            return self._seq

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
                         "requestor": "user", "queue_ms": e.get("queue_ms")})
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
                ev = _row_to_event(r, "out")
                self._join_out(ev)
                self._push(ev)
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
                ev = _row_to_event(r, "in")
                self._remember_inflight(ev)
                self._push(ev)
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
        if self.log:
            self.log.write_cursor(last_poll_at=self.last_poll_at, polls=self.polls,
                                  last_newest_id=self.last_newest_id,
                                  events_buffered=len(self.events),
                                  out_seen=self.out_seen, out_lost=self.out_lost,
                                  started_at=self.started_at)
        return got

    def run(self):
        self.started_at = time.time()
        # resume continuity from the durable cursor before the live baseline,
        # so a restart does not look like an id discontinuity.
        if self.log:
            self.resumed_from = self.log.read_cursor() or None
            if isinstance((self.resumed_from or {}).get("last_newest_id"), int):
                self.last_newest_id = self.resumed_from["last_newest_id"]
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
                "last_seq": self._seq, "queue_joined": self.queue_ms_seen,
                "inflight_pending": len(self.inflight),
                "resumed_from": self.resumed_from,
                "persisted": self.log.stats() if self.log else None,
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


def start(interval_s: float = 5.0, persist: bool = True,
          log_dir: str | None = None) -> dict:
    global _TAP
    with _TAP_LOCK:
        if _TAP and _TAP.is_alive():
            return {"started": False, "reason": "already running", **_TAP.status()}
        _TAP = LiveTap(interval_s=interval_s, persist=persist, log_dir=log_dir)
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


def persisted_events(day: str | None = None, limit: int = 5000,
                     since_ts: float = 0.0) -> list[dict]:
    """Read the durable tap log from disk (works with the tap stopped)."""
    return EventLog().read_events(day=day, limit=limit, since_ts=since_ts)


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
