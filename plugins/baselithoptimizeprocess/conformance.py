"""Conformance checking: how faithfully a mapped model matches reality.

Given a hand-mapped (or previously mined) :class:`ProcessGraph` and a fresh
event log, this computes a fitness score and surfaces deviations — the
Signavio/Celonis governance question "does the process actually run the way we
modelled it?". Pure and deterministic.
"""

from __future__ import annotations

from collections import defaultdict

from .cost import node_cost
from .event_models import ConformanceReport, Event, TransitionDeviation
from .models import NodeKind, ProcessGraph


def _ordered_cases(events: list[Event]) -> dict[str, list[str]]:
    """Group events into per-case ordered activity sequences."""
    grouped: dict[str, list[Event]] = defaultdict(list)
    for event in events:
        grouped[event.case_id].append(event)
    return {
        case_id: [e.activity for e in sorted(evs, key=lambda e: e.timestamp)]
        for case_id, evs in grouped.items()
    }


def check_conformance(model: ProcessGraph, events: list[Event]) -> ConformanceReport:
    """Score how well an event log conforms to a model.

    Fitness is the fraction of observed directly-follows transitions (weighted by
    frequency) that exist as edges in the model. A case is "conforming" when all
    of its transitions exist in the model.

    Args:
        model: The reference process model.
        events: The observed event log.

    Returns:
        A populated :class:`ConformanceReport` (fitness 1.0 on an empty log).
    """
    allowed = {(e.source, e.target) for e in model.edges}
    starts = {n.id for n in model.nodes if n.kind is NodeKind.START}
    ends = {n.id for n in model.nodes if n.kind is NodeKind.END}
    cases = _ordered_cases(events)

    total_transitions = 0
    matched_transitions = 0
    conforming = 0
    deviating = 0
    undesired: dict[tuple[str, str], int] = defaultdict(int)
    align_cost = 0.0
    align_max = 0.0
    case_fitnesses: list[float] = []

    for sequence in cases.values():
        case_ok = True
        for src, dst in zip(sequence, sequence[1:]):
            total_transitions += 1
            if (src, dst) in allowed:
                matched_transitions += 1
            else:
                undesired[(src, dst)] += 1
                case_ok = False
        cost, ceiling = _alignment_cost(sequence, allowed, starts, ends)
        align_cost += cost
        align_max += ceiling
        case_fitnesses.append(1.0 - cost / ceiling if ceiling > 0 else 1.0)
        conforming += case_ok
        deviating += not case_ok

    fitness = 1.0 if total_transitions == 0 else matched_transitions / total_transitions
    alignment_fitness = 1.0 if align_max == 0 else 1.0 - align_cost / align_max
    avg_case_fitness = (
        sum(case_fitnesses) / len(case_fitnesses) if case_fitnesses else 1.0
    )
    observed_activities = {a for seq in cases.values() for a in seq}
    unseen = sorted(
        node.id for node in model.nodes if node.id not in observed_activities
    )
    cost_by_node = {n.id: node_cost(n) for n in model.nodes}
    deviation_cost = round(
        sum(
            cost_by_node.get(dst, 0.0) * count for (_s, dst), count in undesired.items()
        ),
        4,
    )

    return ConformanceReport(
        process_id=model.id,
        fitness=fitness,
        alignment_fitness=round(max(0.0, alignment_fitness), 4),
        avg_case_fitness=round(max(0.0, avg_case_fitness), 4),
        conforming_cases=conforming,
        deviating_cases=deviating,
        undesired_transitions=sorted(
            (
                TransitionDeviation(source=src, target=dst, count=count)
                for (src, dst), count in undesired.items()
            ),
            key=lambda d: d.count,
            reverse=True,
        ),
        unseen_activities=unseen,
        deviation_cost=deviation_cost,
        currency=model.currency,
    )


def _alignment_cost(
    sequence: list[str],
    allowed: set[tuple[str, str]],
    starts: set[str],
    ends: set[str],
) -> tuple[float, float]:
    """Replay-style cost of a trace + its maximum possible cost.

    Cost counts deviating transitions plus (when the model declares them) a
    wrong start node and a wrong end node — penalising traces that begin or end
    off-model, not just bad transitions.
    """
    transitions = max(0, len(sequence) - 1)
    cost = float(
        sum(1 for src, dst in zip(sequence, sequence[1:]) if (src, dst) not in allowed)
    )
    ceiling = float(transitions)
    if starts:
        ceiling += 1.0
        if sequence and sequence[0] not in starts:
            cost += 1.0
    if ends:
        ceiling += 1.0
        if sequence and sequence[-1] not in ends:
            cost += 1.0
    return float(cost), ceiling


__all__ = ["check_conformance"]
