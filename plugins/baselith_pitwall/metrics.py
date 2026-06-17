"""Prometheus instrumentation for the pit wall.

Reuses the shared ``prometheus_client`` primitives re-exported by
:mod:`core.observability.metrics` so the pit-wall series land on the same default
registry the platform already scrapes — no separate exposition endpoint. Metrics
are labelled by **tenant only** (bounded cardinality); session ids are
deliberately not used as labels to avoid an unbounded label explosion. All
helpers degrade to no-ops if ``prometheus_client`` is unavailable, so the realtime
hot path never depends on the metrics layer.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

try:
    from core.observability.metrics import Counter, Gauge, Histogram

    _FRAMES = Counter(
        "pitwall_frames_ingested_total",
        "Telemetry frames folded into belief state.",
        ["tenant"],
    )
    _RECS = Counter(
        "pitwall_recommendations_emitted_total",
        "Confirmed, FIA-validated recommendations emitted.",
        ["tenant", "kind"],
    )
    _SESSIONS = Gauge(
        "pitwall_sessions_active",
        "Live race sessions currently running.",
        ["tenant"],
    )
    _DECISION = Histogram(
        "pitwall_decision_seconds",
        "Wall-clock of the per-lap decision pipeline.",
        ["tenant"],
    )
    _ENABLED = True
except Exception:  # noqa: BLE001 — metrics are best-effort, never fatal
    _ENABLED = False


def record_frame(tenant: str) -> None:
    """Count one telemetry frame ingested for a tenant."""
    if _ENABLED:
        _FRAMES.labels(tenant=tenant).inc()


def record_recommendation(tenant: str, kind: str) -> None:
    """Count one emitted recommendation of ``kind`` for a tenant."""
    if _ENABLED:
        _RECS.labels(tenant=tenant, kind=kind).inc()


def inc_sessions(tenant: str) -> None:
    """Increment the live-session gauge for a tenant."""
    if _ENABLED:
        _SESSIONS.labels(tenant=tenant).inc()


def dec_sessions(tenant: str) -> None:
    """Decrement the live-session gauge for a tenant."""
    if _ENABLED:
        _SESSIONS.labels(tenant=tenant).dec()


@contextmanager
def time_decision(tenant: str) -> Iterator[None]:
    """Time the per-lap decision pipeline for a tenant (no-op if disabled)."""
    if not _ENABLED:
        yield
        return
    with _DECISION.labels(tenant=tenant).time():
        yield


__all__ = [
    "record_frame",
    "record_recommendation",
    "inc_sessions",
    "dec_sessions",
    "time_decision",
]
