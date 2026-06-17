"""Pure metric-aggregation and bottleneck-detection logic.

No I/O, no framework imports beyond the domain models — every function here is a
deterministic transform from samples to snapshots/bottlenecks, which keeps the
logic trivially unit-testable and free of hidden state. The service layer owns
fetching samples and persisting results; this module only computes.
"""

from __future__ import annotations

from statistics import fmean

from .models import (
    Bottleneck,
    KpiDefinition,
    KpiDirection,
    KpiSnapshot,
    MetricSample,
    Severity,
)


def aggregate_kpi(
    kpi: KpiDefinition, samples: list[MetricSample]
) -> KpiSnapshot | None:
    """Aggregate a KPI's recent samples into a single snapshot.

    Uses the arithmetic mean of the sample window as the current value, then
    flags a breach when that value violates the KPI target given its direction.

    Args:
        kpi: The KPI definition (target + direction live here).
        samples: Recent samples for this KPI (any node scope).

    Returns:
        A :class:`KpiSnapshot`, or None when there are no samples to aggregate.
    """
    if not samples:
        return None
    value = fmean(s.value for s in samples)
    breaching = _is_breaching(value, kpi.target, kpi.direction)
    return KpiSnapshot(
        process_id=samples[0].process_id,
        kpi_id=kpi.id,
        value=value,
        target=kpi.target,
        direction=kpi.direction,
        breaching=breaching,
        sample_count=len(samples),
    )


def detect_bottleneck(
    kpi: KpiDefinition, samples: list[MetricSample]
) -> Bottleneck | None:
    """Detect a bottleneck for one KPI and localize it to its worst node.

    A bottleneck is raised only when the aggregate value breaches the target.
    Localization picks the node whose mean most strongly violates the target;
    when samples carry no node attribution the bottleneck stays process-level.

    Args:
        kpi: The KPI definition.
        samples: Recent samples for this KPI.

    Returns:
        A :class:`Bottleneck`, or None when within target / no data.
    """
    snapshot = aggregate_kpi(kpi, samples)
    if snapshot is None or not snapshot.breaching or kpi.target is None:
        return None

    node_id = _worst_node(samples, kpi.target, kpi.direction)
    severity = _severity(snapshot.value, kpi.target, kpi.direction)
    arrow = "above" if kpi.direction is KpiDirection.MINIMIZE else "below"
    detail = (
        f"KPI '{kpi.name}' at {snapshot.value:.3f}{_unit(kpi)} is {arrow} target "
        f"{kpi.target:.3f}{_unit(kpi)}"
    )
    if node_id is not None:
        detail += f"; worst step: {node_id}"
    return Bottleneck(
        process_id=snapshot.process_id,
        kpi_id=kpi.id,
        node_id=node_id,
        severity=severity,
        observed=snapshot.value,
        target=kpi.target,
        detail=detail,
    )


def _is_breaching(value: float, target: float | None, direction: KpiDirection) -> bool:
    """True when ``value`` violates ``target`` for the given direction."""
    if target is None:
        return False
    if direction is KpiDirection.MINIMIZE:
        return value > target
    return value < target


def _severity(value: float, target: float, direction: KpiDirection) -> Severity:
    """Map relative deviation from target onto a severity bucket."""
    deviation = _relative_deviation(value, target, direction)
    if deviation >= 1.0:
        return Severity.CRITICAL
    if deviation >= 0.5:
        return Severity.HIGH
    if deviation >= 0.2:
        return Severity.MEDIUM
    return Severity.LOW


def _relative_deviation(value: float, target: float, direction: KpiDirection) -> float:
    """Fractional breach magnitude (0 == on target); direction-aware."""
    denom = abs(target) or 1.0
    if direction is KpiDirection.MINIMIZE:
        return max(0.0, (value - target) / denom)
    return max(0.0, (target - value) / denom)


def _worst_node(
    samples: list[MetricSample], target: float, direction: KpiDirection
) -> str | None:
    """Return the node id whose mean most violates the target, if any."""
    by_node: dict[str, list[float]] = {}
    for sample in samples:
        if sample.node_id is not None:
            by_node.setdefault(sample.node_id, []).append(sample.value)
    if not by_node:
        return None
    return max(
        by_node,
        key=lambda nid: _relative_deviation(fmean(by_node[nid]), target, direction),
    )


def _unit(kpi: KpiDefinition) -> str:
    """Render a KPI unit suffix for messages (' s', ' USD', …)."""
    return f" {kpi.unit}" if kpi.unit else ""


__all__ = ["aggregate_kpi", "detect_bottleneck"]
