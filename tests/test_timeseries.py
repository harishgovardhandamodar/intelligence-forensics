"""Unit tests for bucketed timeseries (parse_duration + bucketize)."""
import pytest

from iforensics.timeseries import bucketize, parse_duration


def test_parse_duration_units():
    assert parse_duration("30s") == 30
    assert parse_duration("1m") == 60
    assert parse_duration("5m") == 300
    assert parse_duration("1h") == 3600
    assert parse_duration("1d") == 86400
    assert parse_duration("90s") == 90


def test_parse_duration_rejects_garbage():
    for bad in ("", "abc", "1x", "1m30", None):
        with pytest.raises(ValueError):
            parse_duration(bad)


def _ev(t, service="s", pt=10, ct=5, status="complete", direction="out"):
    return {"t": t, "dir": direction, "service": service, "status": status,
            "prompt_tokens": pt, "completion_tokens": ct}


def test_bucketize_groups_and_totals():
    r = bucketize([_ev(100.0), _ev(101.0), _ev(160.0)], bucket_s=60,
                  window_s=None, fill=False)
    assert [b["t"] for b in r["buckets"]] == [60, 120]
    assert r["buckets"][0]["req"] == 2
    assert r["buckets"][0]["total_tokens"] == 30
    assert r["totals"] == {"req": 3, "total_tokens": 30 + 15, "errors": 0}


def test_bucketize_counts_errors():
    r = bucketize([_ev(100.0), _ev(101.0, status=""), _ev(102.0, status="error")],
                  bucket_s=60, window_s=None, fill=False)
    assert r["buckets"][0]["errors"] == 1


def test_bucketize_window_excludes_old():
    r = bucketize([_ev(100.0), _ev(400.0)], bucket_s=60, window_s=100,
                  now=450.0, fill=False)
    assert r["totals"]["req"] == 1


def test_bucketize_ignores_non_out_and_bad_ts():
    r = bucketize([_ev(100.0), _ev(100.0, direction="in"),
                   {"dir": "out", "service": "s"}], bucket_s=60,
                  window_s=None, fill=False)
    assert r["totals"]["req"] == 1


def test_bucketize_fill_inserts_zero_buckets():
    r = bucketize([_ev(130.0)], bucket_s=60, window_s=300,
                  now=310.0, fill=True)
    # 300s window / 60s bucket -> 6 buckets, one non-empty
    assert len(r["buckets"]) == 6
    assert sum(b["req"] for b in r["buckets"]) == 1


def test_bucketize_per_service_breakdown():
    r = bucketize([_ev(100.0, service="a"), _ev(101.0, service="a"),
                   _ev(102.0, service="b")], bucket_s=60, window_s=None,
                  fill=False)
    b = r["buckets"][0]
    assert b["services"]["a"]["req"] == 2
    assert b["services"]["b"]["tokens"] == 15


def test_bucketize_filter_service():
    r = bucketize([_ev(100.0, service="a"), _ev(101.0, service="b")],
                  bucket_s=60, window_s=None, services={"a"}, fill=False)
    assert r["totals"]["req"] == 1
    assert set(r["buckets"][0]["services"]) == {"a"}