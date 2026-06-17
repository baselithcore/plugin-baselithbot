"""Performance & SLA engine (pure, deterministic).

Computes the throughput-time view analysts actually trust — percentile
distributions of end-to-end case duration and of every activity's waiting time —
and evaluates user-defined SLAs into breach rates. No averages-only summaries: a
P95 surfaces the tail that an arithmetic mean hides. Operates on a raw event log
plus the SLA definitions; no store/HTTP coupling.
"""

from __future__ import annotations

from collections import defaultdict

from ._stats import percentile, summarize
from .caselog import case_duration, group_cases
from .event_models import Event
from .sla_models import (
    ActivityPerformance,
    PerformanceReport,
    SlaDefinition,
    SlaResult,
    SlaScope,
)


def _activity_waits(cases: dict[str, list[Event]]) -> dict[str, list[float]]:
    """Wait-into-activity samples (seconds from the prior step), per activity."""
    waits: dict[str, list[float]] = defaultdict(list)
    for trace in cases.values():
        for prev, curr in zip(trace, trace[1:]):
            waits[curr.activity].append(
                (curr.timestamp - prev.timestamp).total_seconds()
            )
    return waits


def analyze_performance(
    process_id: str, events: list[Event], slas: list[SlaDefinition]
) -> PerformanceReport:
    """Build the throughput + per-activity + SLA performance report.

    Args:
        process_id: Process the report is attributed to.
        events: The raw event log (grouped into cases internally).
        slas: SLA definitions to evaluate (may be empty).

    Returns:
        A :class:`PerformanceReport`; ``case_count`` is 0 for an empty log.
    """
    cases = group_cases(events)
    durations = [case_duration(trace) for trace in cases.values()]
    waits = _activity_waits(cases)
    occurrences: dict[str, int] = defaultdict(int)
    for trace in cases.values():
        for event in trace:
            occurrences[event.activity] += 1

    activities = [
        ActivityPerformance(
            activity=activity,
            occurrences=occurrences[activity],
            wait=summarize(waits.get(activity, [])),
        )
        for activity in sorted(occurrences)
    ]
    results = [_evaluate_sla(sla, durations, waits) for sla in slas]
    return PerformanceReport(
        process_id=process_id,
        case_count=len(cases),
        cycle_time=summarize(durations),
        activities=activities,
        slas=results,
    )


def _evaluate_sla(
    sla: SlaDefinition, durations: list[float], waits: dict[str, list[float]]
) -> SlaResult:
    """Score one SLA: count observations over its threshold."""
    if sla.scope is SlaScope.ACTIVITY:
        observed = waits.get(sla.activity, [])
    else:
        observed = durations
    breaches = sum(1 for value in observed if value > sla.threshold_seconds)
    total = len(observed)
    return SlaResult(
        sla_id=sla.id,
        name=sla.name,
        scope=sla.scope,
        activity=sla.activity,
        threshold_seconds=sla.threshold_seconds,
        observations=total,
        breaches=breaches,
        breach_rate=round(breaches / total, 4) if total else 0.0,
        worst_value=round(max(observed), 4) if observed else 0.0,
        p90_value=round(percentile(observed, 90), 4) if observed else 0.0,
    )


__all__ = ["analyze_performance"]
