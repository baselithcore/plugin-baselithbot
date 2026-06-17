"""Case-centric views over a flat event log, shared by the insight engines.

Variant, performance, and root-cause analysis all start from the same step:
group a flat event stream into per-case, chronologically-ordered traces and derive
the directly-follows edges a model is expected to allow. Centralised here so the
three engines share one definition of "a case" (and stay pure / deterministic).
"""

from __future__ import annotations

import hashlib
from collections import defaultdict

from .event_models import Event
from .models import ProcessGraph


def variant_fingerprint(sequence: list[str] | tuple[str, ...]) -> str:
    """Stable 10-hex-char id for an activity path (order-sensitive)."""
    digest = hashlib.sha256(" ".join(sequence).encode("utf-8")).hexdigest()
    return digest[:10]


def group_cases(events: list[Event]) -> dict[str, list[Event]]:
    """Group events by case id, each trace ordered chronologically."""
    grouped: dict[str, list[Event]] = defaultdict(list)
    for event in events:
        grouped[event.case_id].append(event)
    for trace in grouped.values():
        trace.sort(key=lambda e: e.timestamp)
    return grouped


def case_duration(trace: list[Event]) -> float:
    """End-to-end wall-clock duration of one case in seconds (0 for singletons)."""
    if len(trace) < 2:
        return 0.0
    return (trace[-1].timestamp - trace[0].timestamp).total_seconds()


def model_edges(model: ProcessGraph) -> set[tuple[str, str]]:
    """The set of directly-follows transitions the model permits (by node id)."""
    return {(edge.source, edge.target) for edge in model.edges}


def sequence_conforms(sequence: list[str], allowed: set[tuple[str, str]]) -> bool:
    """True if every consecutive transition in a trace is allowed by the model.

    A single-step (or empty) trace trivially conforms — there is no transition to
    violate. Activities absent from the model break conformance because no edge can
    cover the move into or out of them.
    """
    return all((src, dst) in allowed for src, dst in zip(sequence, sequence[1:]))


__all__ = [
    "variant_fingerprint",
    "group_cases",
    "case_duration",
    "model_edges",
    "sequence_conforms",
]
