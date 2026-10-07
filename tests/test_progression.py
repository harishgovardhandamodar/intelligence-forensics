"""Unit tests for progressive reconstruction (chunking + convergence)."""
import datetime

from iforensics.progression import chunk_rows, progression


def _rows(n, service="svc", start=1_700_000_000, step=60):
    return [
        {"service": service, "ts": start + i * step, "prompt": f"prompt {i}",
         "prompt_tokens": 10, "completion_tokens": 5, "model": "m",
         "project": f"p{i % 2}", "direction": "out"}
        for i in range(n)
    ]


def test_chunk_rows_oldest_first_equal_sizes():
    rows = _rows(10)
    chunks = chunk_rows(rows, 5)
    assert len(chunks) == 5
    assert all(len(c) == 2 for c in chunks)
    # chunk boundaries are time-ordered
    assert chunks[0][0]["ts"] < chunks[-1][-1]["ts"]


def test_chunk_rows_too_few_uses_bigger_chunks():
    chunks = chunk_rows(_rows(2), 5)
    assert len(chunks) == 2
    assert all(len(c) == 1 for c in chunks)


def test_chunk_rows_clamps_n():
    chunks = chunk_rows(_rows(40), 99)
    assert len(chunks) <= 12


def test_chunk_rows_ignores_unordered_input():
    rows = _rows(8); rows.reverse()
    chunks = chunk_rows(rows, 4)
    assert [c[0]["ts"] for c in chunks] == sorted(c[0]["ts"] for c in chunks)


def test_progression_no_rows():
    r = progression("nope", _rows(5, service="real"))
    assert r["error"] == "no rows"
    assert r["steps"] == []


def test_progression_cumulative_rows_grow():
    r = progression("svc", _rows(20), n=4, mode="cumulative")
    assert r["total_rows"] == 20
    assert len(r["steps"]) == 4
    counts = [s["requests"] for s in r["steps"]]
    assert counts == sorted(counts) and counts[0] < counts[-1]
    assert all(s["mode"] == "cumulative" for s in r["steps"])


def test_progression_window_constant_rows():
    r = progression("svc", _rows(20), n=4, mode="window")
    assert len(r["steps"]) == 4
    assert {s["requests"] for s in r["steps"]} == {5}


def test_progression_converged_flag():
    r = progression("svc", _rows(40), n=4, mode="cumulative")
    assert isinstance(r["converged"], bool)
    assert "delta" in r["steps"][0]
    assert r["steps"][0]["delta"]["project_changed"] is False
    assert r["steps"][0]["delta"]["template_growth"] >= 0


def test_progression_window_stringify():
    r = progression("svc", _rows(4), n=2, mode="window")
    assert "→" in r["steps"][0]["window"]