"""Prometheus metrics for BaselithOptimizeProcess (BOP).

Every metric uses the ``bop_`` prefix so it is trivially scrapable from the
global :mod:`core.observability` registry without colliding with ``mas_*`` core
metrics or other plugins. As a real-time *monitoring* plugin, BOP's whole job is
to make process health observable — so KPI values, breaches, bottlenecks, and
optimization runs are all exported here and surfaced on the standard ``/metrics``
endpoint alongside the rest of the framework.

The module fails quiet: if ``prometheus_client`` raises (label-cardinality or
registry conflicts during hot-reload) we log and move on — observability must
never break the monitoring or optimization path.
"""

from __future__ import annotations

from core.observability.logging import get_logger
from prometheus_client import Counter, Gauge, Histogram

from .models import Bottleneck, KpiSnapshot

logger = get_logger(__name__)

SAMPLES_INGESTED_TOTAL = Counter(
    "bop_samples_ingested_total",
    "Metric samples ingested, labeled by process.",
    ["process_id"],
)

KPI_VALUE = Gauge(
    "bop_kpi_value",
    "Latest aggregated value of a process KPI.",
    ["process_id", "kpi_id"],
)

KPI_BREACHING = Gauge(
    "bop_kpi_breaching",
    "Whether a KPI is currently breaching its target (1) or not (0).",
    ["process_id", "kpi_id"],
)

BOTTLENECKS = Gauge(
    "bop_bottlenecks",
    "Current count of detected bottlenecks by severity.",
    ["process_id", "severity"],
)

OPTIMIZATION_RUNS_TOTAL = Counter(
    "bop_optimization_runs_total",
    "Optimization passes executed, labeled by process and outcome.",
    ["process_id", "outcome"],  # outcome: ok / error
)

PROPOSALS_TOTAL = Counter(
    "bop_proposals_total",
    "Optimization proposals generated, labeled by process.",
    ["process_id"],
)

OPTIMIZE_LATENCY_SECONDS = Histogram(
    "bop_optimize_latency_seconds",
    "Wall-clock latency of an optimization pass.",
    ["process_id"],
    buckets=(0.05, 0.1, 0.5, 1, 5, 15, 30, 60, 120),
)

CONFORMANCE_FITNESS = Gauge(
    "bop_conformance_fitness",
    "Latest conformance fitness of a process model vs its event log (0-1).",
    ["process_id"],
)

RULE_FIRINGS_TOTAL = Counter(
    "bop_rule_firings_total",
    "Automation-rule firings, labeled by process and action.",
    ["process_id", "action"],
)

_SEVERITIES = ("low", "medium", "high", "critical")


def record_samples(process_id: str, count: int) -> None:
    """Count ingested samples for a process."""
    try:
        SAMPLES_INGESTED_TOTAL.labels(process_id=process_id).inc(count)
    except Exception as exc:  # noqa: BLE001 - never break ingestion
        logger.debug("bop_metric_error", metric="samples", error=str(exc))


def record_snapshots(process_id: str, snapshots: list[KpiSnapshot]) -> None:
    """Export the latest KPI value/breach gauges for a process."""
    try:
        for snap in snapshots:
            KPI_VALUE.labels(process_id=process_id, kpi_id=snap.kpi_id).set(snap.value)
            KPI_BREACHING.labels(process_id=process_id, kpi_id=snap.kpi_id).set(
                1.0 if snap.breaching else 0.0
            )
    except Exception as exc:  # noqa: BLE001
        logger.debug("bop_metric_error", metric="snapshots", error=str(exc))


def record_bottlenecks(process_id: str, bottlenecks: list[Bottleneck]) -> None:
    """Export bottleneck counts per severity, resetting absent buckets to 0."""
    try:
        counts = {sev: 0 for sev in _SEVERITIES}
        for bottleneck in bottlenecks:
            counts[bottleneck.severity.value] = (
                counts.get(bottleneck.severity.value, 0) + 1
            )
        for severity, count in counts.items():
            BOTTLENECKS.labels(process_id=process_id, severity=severity).set(count)
    except Exception as exc:  # noqa: BLE001
        logger.debug("bop_metric_error", metric="bottlenecks", error=str(exc))


def record_optimization(
    process_id: str, outcome: str, proposals: int, seconds: float
) -> None:
    """Record an optimization pass: outcome counter, proposal count, latency."""
    try:
        OPTIMIZATION_RUNS_TOTAL.labels(process_id=process_id, outcome=outcome).inc()
        if proposals:
            PROPOSALS_TOTAL.labels(process_id=process_id).inc(proposals)
        OPTIMIZE_LATENCY_SECONDS.labels(process_id=process_id).observe(seconds)
    except Exception as exc:  # noqa: BLE001
        logger.debug("bop_metric_error", metric="optimization", error=str(exc))


def record_conformance(process_id: str, fitness: float) -> None:
    """Export the latest conformance fitness for a process."""
    try:
        CONFORMANCE_FITNESS.labels(process_id=process_id).set(fitness)
    except Exception as exc:  # noqa: BLE001
        logger.debug("bop_metric_error", metric="conformance", error=str(exc))


def record_rule_firing(process_id: str, action: str) -> None:
    """Count an automation-rule firing by action type."""
    try:
        RULE_FIRINGS_TOTAL.labels(process_id=process_id, action=action).inc()
    except Exception as exc:  # noqa: BLE001
        logger.debug("bop_metric_error", metric="rule_firing", error=str(exc))


__all__ = [
    "record_samples",
    "record_snapshots",
    "record_bottlenecks",
    "record_optimization",
    "record_conformance",
    "record_rule_firing",
]
