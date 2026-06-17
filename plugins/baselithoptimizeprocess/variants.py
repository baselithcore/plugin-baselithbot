"""Variant analysis engine — the process-mining variant explorer (pure).

From an event log and the mapped model it builds the variant table analysts live
in: every distinct path with its case share, throughput-time distribution, model
conformance, and per-case cost. The most frequent conforming path is flagged as
the *happy path* (the reference everything else deviates from). A pure ``diff``
helper compares any two variants (added/removed steps, Δ time/cost) for the
Signavio-style side-by-side. Deterministic and side-effect-free.
"""

from __future__ import annotations

from ._stats import summarize
from .caselog import (
    case_duration,
    group_cases,
    model_edges,
    sequence_conforms,
    variant_fingerprint,
)
from .cost import node_cost
from .event_models import Event
from .models import ProcessGraph
from .variant_models import VariantDetail, VariantDiff, VariantReport

# Variants holding a smaller share than this are reported as "rare" deviations.
RARE_SHARE_THRESHOLD = 0.05


def analyze_variants(
    model: ProcessGraph,
    events: list[Event],
    rare_threshold: float = RARE_SHARE_THRESHOLD,
) -> VariantReport:
    """Build the variant breakdown of an event log against a process model.

    Args:
        model: The mapped/discovered process the log is compared against.
        events: The raw event log (grouped into cases internally).
        rare_threshold: Share below which a variant counts as a rare deviation.

    Returns:
        A :class:`VariantReport`; ``case_count`` is 0 when the log is empty.
    """
    cases = group_cases(events)
    if not cases:
        return VariantReport(
            process_id=model.id, case_count=0, variant_count=0, currency=model.currency
        )

    allowed = model_edges(model)
    cost_by_id = {node.id: round(node_cost(node), 4) for node in model.nodes}

    paths: dict[tuple[str, ...], list[float]] = {}
    for trace in cases.values():
        sequence = tuple(event.activity for event in trace)
        paths.setdefault(sequence, []).append(case_duration(trace))

    total_cases = len(cases)
    details = [
        _build_detail(seq, durations, total_cases, allowed, cost_by_id)
        for seq, durations in paths.items()
    ]
    details.sort(key=lambda v: v.count, reverse=True)

    happy_id = _mark_happy_path(details)
    conforming = sum(v.count for v in details if v.conforms)
    return VariantReport(
        process_id=model.id,
        case_count=total_cases,
        variant_count=len(details),
        happy_path_id=happy_id,
        conforming_cases=conforming,
        deviating_cases=total_cases - conforming,
        rare_variant_count=sum(1 for v in details if v.share < rare_threshold),
        currency=model.currency,
        variants=details,
    )


def _build_detail(
    sequence: tuple[str, ...],
    durations: list[float],
    total_cases: int,
    allowed: set[tuple[str, str]],
    cost_by_id: dict[str, float],
) -> VariantDetail:
    """Assemble one variant row: share, throughput, conformance, and cost."""
    seq = list(sequence)
    deviations = sum(1 for src, dst in zip(seq, seq[1:]) if (src, dst) not in allowed)
    cost = round(sum(cost_by_id.get(step, 0.0) for step in seq), 4)
    return VariantDetail(
        id=variant_fingerprint(sequence),
        sequence=seq,
        count=len(durations),
        share=round(len(durations) / total_cases, 4) if total_cases else 0.0,
        duration=summarize(durations),
        conforms=sequence_conforms(seq, allowed),
        deviation_count=deviations,
        cost_per_case=cost,
    )


def _mark_happy_path(details: list[VariantDetail]) -> str | None:
    """Flag the most frequent conforming variant as the happy path; return its id."""
    for detail in details:  # details are already sorted by count desc
        if detail.conforms:
            detail.is_happy_path = True
            return detail.id
    return None


def diff_variants(report: VariantReport, a_id: str, b_id: str) -> VariantDiff | None:
    """Compare two variants from a report; None if either id is absent.

    ``a`` is the reference (typically the happy path) and ``b`` the comparison.
    Added/removed steps use set difference on activities; the deltas are b − a so
    a positive ``cycle_time_p50_delta`` means b is slower than a.
    """
    by_id = {v.id: v for v in report.variants}
    a, b = by_id.get(a_id), by_id.get(b_id)
    if a is None or b is None:
        return None
    set_a, set_b = set(a.sequence), set(b.sequence)
    return VariantDiff(
        a_id=a.id,
        b_id=b.id,
        a_sequence=a.sequence,
        b_sequence=b.sequence,
        added_steps=sorted(set_b - set_a),
        removed_steps=sorted(set_a - set_b),
        shared_steps=sorted(set_a & set_b),
        count_delta=b.count - a.count,
        cycle_time_p50_delta=round(b.duration.p50 - a.duration.p50, 4),
        cycle_time_p90_delta=round(b.duration.p90 - a.duration.p90, 4),
        cost_delta=round(b.cost_per_case - a.cost_per_case, 4),
        currency=report.currency,
    )


__all__ = ["analyze_variants", "diff_variants", "RARE_SHARE_THRESHOLD"]
