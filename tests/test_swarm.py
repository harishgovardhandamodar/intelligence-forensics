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
