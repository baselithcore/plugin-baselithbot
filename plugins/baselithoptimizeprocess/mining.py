"""Process mining: discover a process model + analytics from an event log.

This is BOP's Celonis-style core. From a flat list of timestamped events it
reconstructs the *directly-follows graph* (the real process), classifies steps,
enumerates path variants, and derives per-case cycle-time samples so a freshly
mined process is immediately monitorable. Pure and deterministic — no I/O.
"""

from __future__ import annotations

from collections import defaultdict
from statistics import fmean

from .event_models import ActivityStat, Event, MiningResult, Variant
from .models import (
    KpiDefinition,
    KpiDirection,
    MetricSample,
    NodeKind,
    ProcessEdge,
    ProcessGraph,
    ProcessNode,
)

# Synthetic KPI the miner attaches so cycle time is monitorable out of the box.
CYCLE_TIME_KPI = "cycle_time_seconds"


def _cases(events: list[Event]) -> dict[str, list[Event]]:
    """Group events by case and order each case chronologically."""
    grouped: dict[str, list[Event]] = defaultdict(list)
    for event in events:
        grouped[event.case_id].append(event)
    for case in grouped.values():
        case.sort(key=lambda e: e.timestamp)
    return grouped


def _classify(
    activity: str, indegree: dict[str, int], outdegree: dict[str, int]
) -> NodeKind:
    """Assign a node kind from its directly-follows connectivity."""
    if indegree.get(activity, 0) == 0:
        return NodeKind.START
    if outdegree.get(activity, 0) == 0:
        return NodeKind.END
    if outdegree.get(activity, 0) > 1:
        return NodeKind.DECISION
    return NodeKind.TASK


def mine_event_log(
    process_id: str,
    events: list[Event],
    process_name: str = "",
    min_frequency: int = 0,
) -> tuple[ProcessGraph, MiningResult, list[MetricSample]]:
    """Discover a process model and analytics from an event log.

    Args:
        process_id: Id to assign to the discovered process.
        events: The raw event log (any order; grouped/sorted internally).
        process_name: Optional display name (defaults to the id).
        min_frequency: Drop directly-follows transitions seen fewer than this
            many times from the discovered graph (noise filter). ``0`` (default)
            keeps every transition — identical to the prior behaviour.

    Returns:
        A tuple of ``(ProcessGraph, MiningResult, cycle_time_samples)``. The
        samples carry per-case durations so the caller can ingest them and light
        up live monitoring immediately.

    Raises:
        ValueError: If the event log is empty.
    """
    if not events:
        raise ValueError("event log is empty")

    cases = _cases(events)
    follows: dict[tuple[str, str], int] = defaultdict(int)
    waits: dict[str, list[float]] = defaultdict(list)
    activity_count: dict[str, int] = defaultdict(int)
    variant_paths: dict[tuple[str, ...], list[float]] = defaultdict(list)
    rework_per_activity: dict[str, int] = defaultdict(int)
    rework_cases = 0
    samples: list[MetricSample] = []

    for case in cases.values():
        sequence = tuple(e.activity for e in case)
        local: dict[str, int] = defaultdict(int)
        for event in case:
            activity_count[event.activity] += 1
            local[event.activity] += 1
        for activity, occ in local.items():
            if occ > 1:
                rework_per_activity[activity] += occ - 1
        if any(occ > 1 for occ in local.values()):
            rework_cases += 1
        for prev, curr in zip(case, case[1:]):
            follows[(prev.activity, curr.activity)] += 1
            waits[curr.activity].append(
                (curr.timestamp - prev.timestamp).total_seconds()
            )
        duration = (case[-1].timestamp - case[0].timestamp).total_seconds()
        variant_paths[sequence].append(duration)
        samples.append(
            MetricSample(
                process_id=process_id,
                kpi_id=CYCLE_TIME_KPI,
                value=duration,
                node_id=case[-1].activity,
            )
        )

    graph = _build_graph(
        process_id, process_name, activity_count, follows, min_frequency
    )
    result = _build_result(
        process_id, cases, activity_count, waits, variant_paths, rework_per_activity
    )
    result.rework_cases = rework_cases
    result.rework_rate = round(rework_cases / len(cases), 4) if cases else 0.0
    result.self_loops = sorted({s for (s, d) in follows if s == d})
    result.concurrent_activities = _concurrent_pairs(follows)
    return graph, result, samples


def _concurrent_pairs(follows: dict[tuple[str, str], int]) -> list[list[str]]:
    """Activity pairs seen in both orders (a→b and b→a) — likely parallel."""
    pairs: set[tuple[str, str]] = set()
    for src, dst in follows:
        if src < dst and follows.get((dst, src), 0) > 0:
            pairs.add((src, dst))
    return [list(p) for p in sorted(pairs)]


def _build_graph(
    process_id: str,
    process_name: str,
    activity_count: dict[str, int],
    follows: dict[tuple[str, str], int],
    min_frequency: int = 0,
) -> ProcessGraph:
    """Turn discovered activities + transitions into a ProcessGraph."""
    kept = {edge: count for edge, count in follows.items() if count >= min_frequency}
    indegree: dict[str, int] = defaultdict(int)
    outdegree: dict[str, int] = defaultdict(int)
    for (src, dst), _count in kept.items():
        outdegree[src] += 1
        indegree[dst] += 1

    nodes = [
        ProcessNode(
            id=activity,
            name=activity,
            kind=_classify(activity, indegree, outdegree),
            metadata={"occurrences": str(count)},
        )
        for activity, count in sorted(activity_count.items())
    ]
    edges = [
        ProcessEdge(source=src, target=dst, condition=f"{count}×")
        for (src, dst), count in sorted(kept.items())
    ]
    return ProcessGraph(
        id=process_id,
        name=process_name or process_id,
        description="Discovered from event log via process mining.",
        nodes=nodes,
        edges=edges,
        kpis=[
            KpiDefinition(
                id=CYCLE_TIME_KPI,
                name="Cycle time",
                unit="s",
                direction=KpiDirection.MINIMIZE,
                description="End-to-end case duration, mined from the event log.",
            )
        ],
    )


def _build_result(
    process_id: str,
    cases: dict[str, list[Event]],
    activity_count: dict[str, int],
    waits: dict[str, list[float]],
    variant_paths: dict[tuple[str, ...], list[float]],
    rework_per_activity: dict[str, int],
) -> MiningResult:
    """Assemble analytics: activity stats, variants, and case-duration mean."""
    activity_stats = [
        ActivityStat(
            activity=activity,
            occurrences=count,
            avg_wait_seconds=fmean(waits[activity]) if waits.get(activity) else 0.0,
            rework_count=rework_per_activity.get(activity, 0),
        )
        for activity, count in sorted(activity_count.items())
    ]
    variants = sorted(
        (
            Variant(
                sequence=list(seq),
                count=len(durations),
                avg_duration_seconds=fmean(durations) if durations else 0.0,
            )
            for seq, durations in variant_paths.items()
        ),
        key=lambda v: v.count,
        reverse=True,
    )
    all_durations = [d for ds in variant_paths.values() for d in ds]
    return MiningResult(
        process_id=process_id,
        case_count=len(cases),
        activity_stats=activity_stats,
        variants=variants,
        avg_case_duration_seconds=fmean(all_durations) if all_durations else 0.0,
    )


__all__ = ["mine_event_log", "CYCLE_TIME_KPI"]
