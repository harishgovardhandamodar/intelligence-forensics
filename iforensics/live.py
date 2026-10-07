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
        self.seen_ids: set = set()
        self.seen_inflight: set = set()
        self.loaded_models: set = set()
        self.started_at: float | None = None
        self.last_poll_at: float | None = None
        self.polls = 0
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
            rows.append({"ts": e["t"], "service": e["service"], "model": e["model"],
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
            for r in (res.get("requests") or [])[::-1]:  # oldest first
                rid = r.get("id")
                if rid is None or rid in self.seen_ids:
                    continue
                self.seen_ids.add(rid)
                if self.started_at and (r.get("created_at") or r.get("ts") or 0) < self.started_at - 5:
                    continue  # history predating the tap, not live traffic
                self._push(_row_to_event(r, "out"))
                got["out"] += 1
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
            for r in res.get("requests") or []:
                if r.get("id") is not None:
                    self.seen_ids.add(r["id"])
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
        with self._lock:
            n = len(self.events)
        by_svc = Counter(e["service"] for e in list(self.events)[-500:])
        return {"running": self.is_alive(), "interval_s": self.interval_s,
                "started_at": self.started_at, "uptime_s": round(time.time() - self.started_at, 1) if self.started_at else 0,
                "polls": self.polls, "last_poll_at": self.last_poll_at,
                "events_buffered": n, "recent_by_service": dict(by_svc.most_common(10)),
                "recent_errors": self.errors[-5:]}


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
