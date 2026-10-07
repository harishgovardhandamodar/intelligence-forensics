"""Chain of events (P6.24): one chronological lane per investigation thread.

The Live tab shows a rolling feed and history rows sit in the DB — neither
answers "what happened, in order, for this request". `build_chain` merges
live tap events (IN queue arrivals, OUT completions, SYS model changes) with
history rows (OUT only) into a single time-ordered lane, linking IN→OUT pairs
by qid so queue-wait is visible inline:

    IN  svc ... prompt head            (arrival, qid Q)
    OUT svc ... +queue_ms               (completion, same Q → same chain)

Events without a qid link (history rows) stand alone. Capped and sorted;
pure function over caller-supplied inputs, so the dashboard picks the source
(live buffer or durable log) and tests need no fox.
"""
from __future__ import annotations

MAX_CHAIN = 200


def _hist_event(r: dict) -> dict:
    return {
        "t": r.get("ts") or 0,
        "dir": "out",
        "service": r.get("service") or "unknown",
        "model": r.get("model") or "unknown",
        "prompt_head": str(r.get("prompt") or "")[:220].replace("\n", " | "),
        "query_type": r.get("query_type") or "",
        "status": r.get("status") or "complete",
        "prompt_tokens": r.get("prompt_tokens") or 0,
        "completion_tokens": r.get("completion_tokens") or 0,
        "duration_ms": r.get("duration_ms") or 0,
        "queue_ms": r.get("queue_ms"),
        "qid": r.get("id") or "",
        "seq": None,
        "source": "history",
    }


def _live_event(e: dict) -> dict:
    return {
        "t": e.get("t") or 0,
        "dir": e.get("dir") or "out",
        "service": e.get("service") or "unknown",
        "model": e.get("model") or "?",
        "prompt_head": str(e.get("prompt_head") or "")[:220],
        "query_type": e.get("query_type") or "",
        "status": e.get("status") or "",
        "prompt_tokens": e.get("prompt_tokens") or 0,
        "completion_tokens": e.get("completion_tokens") or 0,
        "duration_ms": e.get("duration_ms") or 0,
        "queue_ms": e.get("queue_ms"),
        "qid": e.get("qid") or "",
        "seq": e.get("seq"),
        "source": "live",
    }


def build_chain(rows: list[dict] | None = None,
                live_events: list[dict] | None = None,
                service: str | None = None, limit: int = 200) -> dict:
    """Merge history + live into one chronological chain with qid links."""
    evs = [_hist_event(r) for r in (rows or [])]
    evs += [_live_event(e) for e in (live_events or [])]
    if service:
        evs = [e for e in evs if e["service"] == service]
    evs = [e for e in evs if e["t"]]
    evs.sort(key=lambda e: (e["t"], 0 if e["dir"] == "in" else 1))
    evs = evs[-max(1, min(MAX_CHAIN, limit)):]

    # link IN→OUT by qid; history OUTs (numeric ids) rarely meet a live IN
    by_qid: dict[str, list[int]] = {}
    for i, e in enumerate(evs):
        if e["qid"]:
            by_qid.setdefault(str(e["qid"]), []).append(i)
    chain_of = {}
    chains = 0
    for qid, idxs in by_qid.items():
        dirs = {evs[i]["dir"] for i in idxs}
        if "in" in dirs and "out" in dirs:
            chains += 1
            for i in idxs:
                chain_of[i] = chains
    for i, e in enumerate(evs):
        e["chain"] = chain_of.get(i)
    orphans = sum(1 for e in evs if e["dir"] == "out" and e["chain"] is None)
    return {"events": evs,
            "summary": {"n": len(evs), "chains": chains, "orphans": orphans,
                        "live": sum(1 for e in evs if e["source"] == "live"),
                        "history": sum(1 for e in evs if e["source"] == "history")}}
