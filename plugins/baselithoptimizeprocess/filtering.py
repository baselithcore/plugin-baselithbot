"""Interactive event-log filtering (pure), Celonis-style segmentation.

Every insight lens (variants, performance, root cause) can be scoped to a subset
of cases without re-uploading data: the caller supplies an :class:`EventFilter`
and the matching whole cases are kept. Filtering is case-grained — a case either
survives in full or is dropped entirely — so downstream throughput and variant
maths stay coherent. Deterministic and side-effect-free.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from .caselog import case_duration, group_cases, variant_fingerprint
from .event_models import Event


class EventFilter(BaseModel):
    """A case-level segmentation of an event log (all conditions AND together).

    Every field is optional; an empty filter keeps the whole log. A case must
    satisfy *all* supplied conditions to survive.
    """

    start_after: datetime | None = Field(
        default=None, description="Keep cases whose first event is at/after this."
    )
    end_before: datetime | None = Field(
        default=None, description="Keep cases whose last event is at/before this."
    )
    activity: str | None = Field(
        default=None, description="Keep cases that contain this activity."
    )
    resource: str | None = Field(
        default=None, description="Keep cases that involve this resource."
    )
    variant_id: str | None = Field(
        default=None, description="Keep cases whose path matches this variant id."
    )
    min_duration_seconds: float | None = Field(
        default=None, ge=0.0, description="Keep cases at least this long."
    )
    max_duration_seconds: float | None = Field(
        default=None, ge=0.0, description="Keep cases at most this long."
    )

    def is_empty(self) -> bool:
        """True when no condition is set (the filter is a no-op)."""
        return all(
            value is None
            for value in (
                self.start_after,
                self.end_before,
                self.activity,
                self.resource,
                self.variant_id,
                self.min_duration_seconds,
                self.max_duration_seconds,
            )
        )


def _case_matches(trace: list[Event], spec: EventFilter) -> bool:
    """Whether one ordered case trace satisfies every filter condition."""
    if spec.start_after is not None and trace[0].timestamp < spec.start_after:
        return False
    if spec.end_before is not None and trace[-1].timestamp > spec.end_before:
        return False
    activities = {event.activity for event in trace}
    if spec.activity is not None and spec.activity not in activities:
        return False
    if spec.resource is not None and spec.resource not in {e.resource for e in trace}:
        return False
    if spec.variant_id is not None:
        fingerprint = variant_fingerprint([e.activity for e in trace])
        if fingerprint != spec.variant_id:
            return False
    duration = case_duration(trace)
    if spec.min_duration_seconds is not None and duration < spec.min_duration_seconds:
        return False
    if spec.max_duration_seconds is not None and duration > spec.max_duration_seconds:
        return False
    return True


def filter_events(events: list[Event], spec: EventFilter | None) -> list[Event]:
    """Return only the events of whole cases that match ``spec``.

    A ``None`` or empty filter returns the input unchanged. Surviving cases keep
    their original event order; cases are concatenated in first-seen order.
    """
    if spec is None or spec.is_empty():
        return events
    cases = group_cases(events)
    kept: list[Event] = []
    for trace in cases.values():
        if _case_matches(trace, spec):
            kept.extend(trace)
    return kept


__all__ = ["EventFilter", "filter_events"]
