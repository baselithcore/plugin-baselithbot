"""Case-level predictive monitoring engine (pure, empirical — no ML runtime).

Learns from completed cases: for each *state* (a case's current/most-recent
activity) it records the remaining-time-to-completion distribution, the
directly-follows successor distribution, and the total durations of cases that
passed through that state. A running case is then scored by looking up its
current state — predicting remaining time, the likely next activity, and the
empirical probability of breaching each case-scoped SLA. Every prediction traces
back to observed cases, so it is explainable and deterministic.
"""

from __future__ import annotations

from collections import defaultdict

from ._stats import summarize
from .caselog import case_duration, group_cases
from .event_models import Event
from .prediction_models import (
    CasePrediction,
    NextActivity,
    PredictorModel,
    SlaPrediction,
    StatePrediction,
)
from .sla_models import SlaDefinition, SlaScope

# Observations at a state for full confidence; fewer scales confidence down.
_CONFIDENCE_FULL = 30
# Max successor candidates returned per prediction.
_MAX_NEXT = 5


class Predictor:
    """An empirical, state-indexed predictor learned from a completed log."""

    def __init__(self, process_id: str, events: list[Event]) -> None:
        self.process_id = process_id
        self._remaining: dict[str, list[float]] = defaultdict(list)
        self._next: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self._totals_through: dict[str, list[float]] = defaultdict(list)
        self._case_count = 0
        self._learn(events)

    def _learn(self, events: list[Event]) -> None:
        """Accumulate remaining-time, successor, and total-duration statistics."""
        cases = group_cases(events)
        self._case_count = len(cases)
        for trace in cases.values():
            end = trace[-1].timestamp
            total = case_duration(trace)
            for state in {event.activity for event in trace}:
                self._totals_through[state].append(total)
            for index, event in enumerate(trace):
                state = event.activity
                self._remaining[state].append((end - event.timestamp).total_seconds())
                if index + 1 < len(trace):
                    self._next[state][trace[index + 1].activity] += 1

    def _next_activities(self, state: str) -> list[NextActivity]:
        """Successor distribution for a state, most-likely first."""
        counts = self._next.get(state, {})
        total = sum(counts.values())
        if not total:
            return []
        ranked = sorted(counts.items(), key=lambda kv: kv[1], reverse=True)
        return [
            NextActivity(activity=activity, probability=round(count / total, 4))
            for activity, count in ranked[:_MAX_NEXT]
        ]

    def model(self) -> PredictorModel:
        """Expose the learned statistics as an inspectable model card."""
        states = [
            StatePrediction(
                activity=state,
                observations=len(samples),
                remaining=summarize(samples),
                next_activities=self._next_activities(state),
                is_terminal=not self._next.get(state),
            )
            for state, samples in sorted(self._remaining.items())
        ]
        return PredictorModel(
            process_id=self.process_id, case_count=self._case_count, states=states
        )

    def predict(
        self, running_trace: list[Event], slas: list[SlaDefinition]
    ) -> CasePrediction:
        """Forecast a running case from its current state and the learned model."""
        ordered = sorted(running_trace, key=lambda e: e.timestamp)
        current = ordered[-1].activity
        elapsed = case_duration(ordered)
        remaining = summarize(self._remaining.get(current, []))
        predicted_total = round(elapsed + remaining.mean, 4)
        observations = len(self._remaining.get(current, []))
        return CasePrediction(
            process_id=self.process_id,
            case_id=ordered[-1].case_id,
            current_activity=current,
            elapsed_seconds=round(elapsed, 4),
            completed=not self._next.get(current) and observations > 0,
            predicted_remaining_seconds=remaining.mean,
            predicted_remaining_p90_seconds=remaining.p90,
            predicted_total_seconds=predicted_total,
            next_activities=self._next_activities(current),
            confidence=round(min(1.0, observations / _CONFIDENCE_FULL), 4),
            slas=[
                self._predict_sla(sla, current, predicted_total)
                for sla in slas
                if sla.scope is SlaScope.CASE
            ],
        )

    def _predict_sla(
        self, sla: SlaDefinition, state: str, projected: float
    ) -> SlaPrediction:
        """Project one case-scoped SLA outcome for a running case."""
        totals = self._totals_through.get(state, [])
        breached = sum(1 for total in totals if total > sla.threshold_seconds)
        probability = round(breached / len(totals), 4) if totals else 0.0
        return SlaPrediction(
            sla_id=sla.id,
            name=sla.name,
            threshold_seconds=sla.threshold_seconds,
            projected_seconds=projected,
            violation_probability=probability,
            will_breach=projected > sla.threshold_seconds,
        )


def build_predictor(process_id: str, events: list[Event]) -> Predictor:
    """Train an empirical predictor from a completed event log."""
    return Predictor(process_id, events)


__all__ = ["Predictor", "build_predictor"]
