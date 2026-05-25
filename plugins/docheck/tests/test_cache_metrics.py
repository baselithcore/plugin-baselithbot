"""Verdict cache metrics counters."""

from docheck.services.cache import _metrics, get_metrics, reset_metrics


def test_initial_metrics_zero() -> None:
    reset_metrics()
    m = get_metrics()
    assert m["hits"] == 0 and m["misses"] == 0 and m["hit_ratio"] == 0.0


def test_hit_ratio_computed() -> None:
    reset_metrics()
    _metrics["hits"] = 7
    _metrics["misses"] = 3
    m = get_metrics()
    assert m["total"] == 10
    assert m["hit_ratio"] == 0.7


def test_reset_clears() -> None:
    _metrics["hits"] = 5
    reset_metrics()
    assert get_metrics()["total"] == 0
