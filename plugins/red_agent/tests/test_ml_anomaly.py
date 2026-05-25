"""M3 — host anomaly detector tests."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest

from plugins.red_agent.ml.models.anomaly import (
    AnomalyDetectorService,
    aggregate_per_host_features,
)


def _evt(
    agent: UUID,
    *,
    kind: str = "process_exec",
    severity: str = "info",
    correlation: str | None = None,
    attributes: dict[str, object] | None = None,
    tenant: str = "default",
) -> dict[str, object]:
    return {
        "agent_uuid": str(agent),
        "tenant_id": tenant,
        "kind": kind,
        "severity": severity,
        "correlation_id": correlation,
        "attributes": attributes or {},
    }


def _window() -> tuple[datetime, datetime]:
    end = datetime(2026, 4, 26, 12, 0, tzinfo=timezone.utc)
    return end - timedelta(minutes=15), end


def test_aggregate_features_groups_per_host_and_tenant() -> None:
    a, b = uuid4(), uuid4()
    start, end = _window()
    events = [
        _evt(a, kind="process_exec"),
        _evt(a, kind="net_conn"),
        _evt(a, kind="process_exec", severity="high"),
        _evt(b, kind="net_conn"),
    ]
    out = aggregate_per_host_features(events, window_start=start, window_end=end)
    assert ("default", a) in out and ("default", b) in out
    a_features = out[("default", a)]
    assert a_features["high_sev_ratio"] == pytest.approx(1 / 3)
    assert a_features["kind_diversity"] == 2.0
    assert a_features["events_per_minute"] > 0


def test_aggregate_features_handles_empty_events() -> None:
    start, end = _window()
    assert aggregate_per_host_features([], window_start=start, window_end=end) == {}


def test_detector_disabled_returns_empty() -> None:
    svc = AnomalyDetectorService(contamination=0.1, min_samples=5, enabled=False)
    start, end = _window()
    out = svc.score_window(events=[_evt(uuid4())], window_start=start, window_end=end)
    assert out == []


def test_detector_skips_when_below_min_samples() -> None:
    pytest.importorskip("sklearn")
    svc = AnomalyDetectorService(contamination=0.1, min_samples=10, enabled=True)
    start, end = _window()
    out = svc.score_window(
        events=[_evt(uuid4()) for _ in range(3)],
        window_start=start,
        window_end=end,
    )
    assert out == []


def test_detector_flags_clear_outlier() -> None:
    pytest.importorskip("sklearn")
    svc = AnomalyDetectorService(contamination=0.1, min_samples=5, enabled=True)
    start, end = _window()

    # 12 well-behaved hosts: small, similar volumes, no high-sev events.
    events: list[dict[str, object]] = []
    for _ in range(12):
        h = uuid4()
        events += [_evt(h, kind="process_exec") for _ in range(3)]

    # 1 outlier host: huge event volume + many high-severity records.
    outlier = uuid4()
    events += [_evt(outlier, kind="process_exec", severity="high") for _ in range(120)]

    scores = svc.score_window(events=events, window_start=start, window_end=end)
    assert scores  # non-empty
    flagged = [s for s in scores if s.is_anomaly]
    assert any(s.agent_uuid == outlier for s in flagged)
