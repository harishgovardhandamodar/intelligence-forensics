"""Unit tests for the swarm task queue + multiprocess-safe ledger (P7.32)."""
import json
import os
import threading
import time

from iforensics import ledger as led
from iforensics import swarm


def test_roundtrip_enqueue_claim_complete(tmp_path):
    base = str(tmp_path)
    t = swarm.enqueue("profile", {"service": "s"}, run_id="r1", base_dir=base)
    got = swarm.claim("worker-1", base_dir=base)
    assert got and got["task_id"] == t["task_id"]
    assert got["claimed_by"] == "worker-1" and got["attempts"] == 1
    assert swarm.claim("worker-2", base_dir=base) is None  # queue drained
    assert swarm.complete(t["task_id"], {"ok": True}, base_dir=base) is True
    assert swarm.status(base_dir=base) == {"pending": 0, "claimed": 0,
                                           "done": 1, "failed": 0}
    done = json.load(open(os.path.join(base, "swarm", "queue", "done",
                                       t["task_id"] + ".json")))
    assert done["result"] == {"ok": True}


def test_claim_filters_kind_and_returns_others(tmp_path):
    base = str(tmp_path)
    swarm.enqueue("critic", {}, base_dir=base)
    got = swarm.claim("w", kinds=["profile"], base_dir=base)
    assert got is None
    assert swarm.status(base_dir=base)["pending"] == 1  # put back, not lost
    got = swarm.claim("w", kinds=["critic"], base_dir=base)
    assert got and got["kind"] == "critic"


def test_fail_requeues_then_parks(tmp_path):
    base = str(tmp_path)
    t = swarm.enqueue("gather", {}, base_dir=base)
    swarm.claim("w", base_dir=base)
    assert swarm.fail(t["task_id"], "boom", base_dir=base) is True
    assert swarm.status(base_dir=base)["pending"] == 1
    for _ in range(6):  # burn through MAX_ATTEMPTS
        swarm.claim("w", base_dir=base)
        swarm.fail(t["task_id"], "boom", base_dir=base)
    st = swarm.status(base_dir=base)
    assert st == {"pending": 0, "claimed": 0, "done": 0, "failed": 1}


def test_stale_claim_recovered(tmp_path):
    base = str(tmp_path)
    t = swarm.enqueue("profile", {}, base_dir=base)
    got = swarm.claim("dead-worker", base_dir=base)
    assert got["task_id"] == t["task_id"]
    cpath = os.path.join(base, "swarm", "queue", "claimed", t["task_id"] + ".json")
    old = time.time() - 3600
    os.utime(cpath, (old, old))
    got2 = swarm.claim("live-worker", base_dir=base, stale_s=60)
    assert got2 and got2["task_id"] == t["task_id"]
    assert got2["claimed_by"] == "live-worker" and got2["attempts"] == 2


def test_concurrent_claims_elect_exactly_one_winner(tmp_path):
    base = str(tmp_path)
    t = swarm.enqueue("profile", {}, base_dir=base)
    # threads race the rename; exactly one may win
    winners = []
    lock = threading.Lock()

    def tgrab():
        got = swarm.claim("w", base_dir=base)
        if got:
            with lock:
                winners.append(got["task_id"])

    ths = [threading.Thread(target=tgrab) for _ in range(8)]
    [th.start() for th in ths]
    [th.join() for th in ths]
    assert winners == [t["task_id"]]


def test_ledger_concurrent_appends_stay_ordered(tmp_path):
    base = str(tmp_path)
    n, workers = 5, 4
    ths = [threading.Thread(
        target=lambda w: [led.append("r1", f"w-{w}", f"a-{i}", base_dir=base)
                          for i in range(n)],
        args=(w,)) for w in range(workers)]
    [th.start() for th in ths]
    [th.join() for th in ths]
    out = led.verify("r1", base_dir=base)
    assert out == {"run_id": "r1", "ok": True, "checked": n * workers,
                   "failed_at": None, "reason": ""}


def test_registry_roundtrip_and_unknown(monkeypatch, tmp_path):
    from iforensics import config
    monkeypatch.setattr(config, "EVIDENCE_DIR", str(tmp_path))
    assert swarm.get_run("nope") == {"status": "unknown"}
    e = swarm.register_run("k1", {"status": "running"})
    assert e["status"] == "running" and e["started"]
    e2 = swarm.update_run("k1", {"status": "done", "run_id": "r1"})
    assert e2["status"] == "done" and e2["run_id"] == "r1"
    assert swarm.get_run("k1")["status"] == "done"
    # survives a fresh read (disk-backed, not a global)
    assert swarm.get_run("k1")["run_id"] == "r1"


def test_recoverable_tasks_lists_leftovers(tmp_path):
    base = str(tmp_path)
    swarm.enqueue("profile", {}, run_id="other", base_dir=base)
    swarm.claim("x", base_dir=base)  # park the unrelated task out of the way
    t1 = swarm.enqueue("profile", {}, run_id="r1", base_dir=base)
    t2 = swarm.enqueue("profile", {}, run_id="r1", base_dir=base)
    claimed = swarm.claim("dead", base_dir=base)  # must be an r1 task now
    assert claimed["run_id"] == "r1"
    left = swarm.recoverable_tasks("r1", base_dir=base)
    by_id = {t["task_id"]: t["_state"] for t in left}
    assert set(by_id) == {t1["task_id"], t2["task_id"]}
    assert by_id[claimed["task_id"]] == "claimed"
    assert swarm.recoverable_tasks("other", base_dir=base)[0]["_state"] == "claimed"


def test_launch_background_uses_registry(monkeypatch, tmp_path):
    import time as _time
    from iforensics import agents as ag
    from iforensics import config
    monkeypatch.setattr(config, "EVIDENCE_DIR", str(tmp_path))
    monkeypatch.setattr(ag, "run_deep_investigation",
                        lambda rows, **kw: {"run_id": "r-mock", "ok": True})
    key = ag.launch_background(lambda: [], model="m", quick=True, only=None)
    for _ in range(100):
        st = ag.background_status(key)
        if st.get("status") in ("done", "error"):
            break
        _time.sleep(0.05)
    assert st["status"] == "done" and st["run_id"] == "r-mock"
    assert ag.background_status("missing") == {"status": "unknown"}


def test_approval_roundtrip_and_miss(tmp_path):
    base = str(tmp_path)
    assert led.find_approval("r1", "prune-old", base_dir=base) is None
    e = led.approve("r1", "prune-old", "op", detail="cleanup", base_dir=base)
    assert e["actor"] == "human:op" and e["action"] == "human.approve"
    found = led.find_approval("r1", "prune-old", base_dir=base)
    assert found and found["hash"] == e["hash"]
    assert led.find_approval("r1", "other-subject", base_dir=base) is None
    assert led.verify("r1", base_dir=base)["ok"] is True


def test_worker_prune_requires_approval(tmp_path, monkeypatch):
    import cli
    from iforensics import retention as ret_mod
    monkeypatch.setenv("IF_LEDGER_DIR", str(tmp_path / "ledger"))
    monkeypatch.setattr(ret_mod, "prune_snapshots", lambda **kw: ["a.db"])
    monkeypatch.setattr(ret_mod, "prune_reports",
                        lambda **kw: {"removed": [], "kept": 0})
    monkeypatch.setattr(ret_mod, "prune_live_logs", lambda **kw: [])
    import pytest
    with pytest.raises(PermissionError):
        cli._swarm_execute("prune", {"approval": "cleanup-q3"}, "m",
                           task_id="t-1", run_id="r1")
    led.approve("r1", "cleanup-q3", "op", base_dir=str(tmp_path / "ledger"))
    out = cli._swarm_execute("prune", {"approval": "cleanup-q3"}, "m",
                             task_id="t-1", run_id="r1")
    assert out["approval"] == "cleanup-q3"
    assert out["snapshots"] == ["a.db"]


def test_prune_apply_needs_approve_flag(tmp_path, monkeypatch):
    import argparse
    import cli
    from iforensics import retention as ret_mod
    monkeypatch.setenv("IF_LEDGER_DIR", str(tmp_path / "ledger"))
    calls = []
    monkeypatch.setattr(ret_mod, "prune_snapshots",
                        lambda **kw: calls.append("db") or [])
    args = argparse.Namespace(keep_db=5, keep_reports=10, keep_days=30,
                              apply=True, approve="")
    assert cli.cmd_prune(args) == 2
    assert calls == []  # refused before touching anything
    args.approve = "ticket-42"
    assert cli.cmd_prune(args) == 0
    assert calls == ["db"]
    assert led.find_approval("ops", "ticket-42",
                             base_dir=str(tmp_path / "ledger")) is not None


def test_collect_results_groups_done_failed_missing(tmp_path):
    base = str(tmp_path)
    t1 = swarm.enqueue("profile", {}, run_id="r1", base_dir=base)
    t2 = swarm.enqueue("profile", {}, run_id="r1", base_dir=base)
    t3 = swarm.enqueue("profile", {}, run_id="r1", base_dir=base)
    c1 = swarm.claim("w", base_dir=base)
    swarm.complete(c1["task_id"], {"parsed": {"project": "p"}}, base_dir=base)
    c2 = swarm.claim("w", base_dir=base)
    swarm.fail(c2["task_id"], "worker blew up", base_dir=base, requeue=False)
    out = swarm.collect_results([t1["task_id"], t2["task_id"], t3["task_id"],
                                 "t-missing"], timeout_s=0.05, poll_s=0.05,
                                base_dir=base)
    assert len(out["done"]) == 1 and len(out["failed"]) == 1
    assert out["missing"] == sorted([t3["task_id"], "t-missing"])
    assert next(iter(out["done"].values())) == {"parsed": {"project": "p"}}
    assert next(iter(out["failed"].values())) == "worker blew up"
