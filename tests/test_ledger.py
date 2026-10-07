"""Unit tests for the auditable action ledger (P7.27)."""
import json
import os

from iforensics import ledger as led


def test_append_chains_hashes_and_seq(tmp_path):
    base = str(tmp_path)
    e1 = led.append("r1", "orchestrator", "task.issued", task_id="t-1",
                    base_dir=base)
    e2 = led.append("r1", "profiler:s", "task.complete", task_id="t-1",
                    base_dir=base)
    assert e1["seq"] == 1 and e2["seq"] == 2
    assert e1["prev_hash"] == "genesis:r1"
    assert e2["prev_hash"] == e1["hash"]
    assert os.path.isfile(os.path.join(base, "ledger", "r1.jsonl"))
    assert led.verify("r1", base_dir=base) == {
        "run_id": "r1", "ok": True, "checked": 2,
        "failed_at": None, "reason": ""}


def test_artifact_file_is_hashed(tmp_path):
    art = os.path.join(str(tmp_path), "out.json")
    with open(art, "w") as f:
        f.write('{"a": 1}')
    e = led.append("r1", "profiler:s", "artifact.written", artifact=art,
                   base_dir=str(tmp_path))
    assert len(e["artifact_sha256"]) == 64
    out = led.verify("r1", base_dir=str(tmp_path))
    assert out["ok"] is True


def test_tamper_detected_at_exact_seq(tmp_path):
    base = str(tmp_path)
    for i in range(3):
        led.append("r1", f"agent-{i}", "task.complete", task_id=f"t-{i}",
                   base_dir=base)
    path = os.path.join(base, "ledger", "r1.jsonl")
    lines = open(path, encoding="utf-8").read().splitlines()
    entry = json.loads(lines[1])
    entry["detail"] = "forged note"
    lines[1] = json.dumps(entry, sort_keys=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    out = led.verify("r1", base_dir=base)
    assert out["ok"] is False
    assert out["failed_at"] == 2
    assert out["reason"] == "entry hash mismatch"


def test_deletion_breaks_chain(tmp_path):
    base = str(tmp_path)
    for i in range(3):
        led.append("r1", "a", "x", base_dir=base)
    path = os.path.join(base, "ledger", "r1.jsonl")
    lines = open(path, encoding="utf-8").read().splitlines()
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join([lines[0]] + lines[2:]) + "\n")
    out = led.verify("r1", base_dir=base)
    assert out["ok"] is False
    assert out["reason"] == "chain link broken"


def test_verify_missing_run_and_index(tmp_path):
    out = led.verify("nope", base_dir=str(tmp_path))
    assert out == {"run_id": "nope", "ok": False, "checked": 0,
                   "error": "no ledger for run"}
    led.append("r9", "a", "x", base_dir=str(tmp_path))
    idx = json.load(open(os.path.join(str(tmp_path), "ledger", "index.json")))
    assert "r9" in idx and idx["r9"]["path"].endswith("r9.jsonl")
    assert [e["seq"] for e in led.read("r9", base_dir=str(tmp_path))] == [1]
