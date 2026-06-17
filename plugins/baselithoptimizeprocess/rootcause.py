"""Root-cause analysis engine (pure, deterministic).

Answers "why are these cases slow?" by labelling each case bad/good against a
duration cutoff, then measuring how over-represented the bad outcome is for every
case attribute (resource, activity, variant, rework pattern). Factors are ranked
by *impact score* — the excess number of bad cases the factor explains — so the
operator sees the few attributes worth acting on, not a wall of weak correlations.
"""

from __future__ import annotations

from collections import defaultdict

from ._stats import percentile
from .caselog import case_duration, group_cases, variant_fingerprint
from .event_models import Event
from .rootcause_models import FactorDimension, RootCauseFactor, RootCauseReport

# Default "slow" cutoff: the upper-quartile case duration (top 25% are 'bad').
_SLOW_PERCENTILE = 75.0
# Drop factors seen in fewer cases than this (noise / no statistical weight).
_MIN_SUPPORT = 2
# Keep at most this many ranked factors in a report.
_MAX_FACTORS = 25


def _case_factors(trace: list[Event]) -> set[tuple[FactorDimension, str]]:
    """Distinct (dimension, value) attributes a single case exhibits."""
    activities = [event.activity for event in trace]
    factors: set[tuple[FactorDimension, str]] = set()
    for event in trace:
        if event.resource:
            factors.add((FactorDimension.RESOURCE, f"resource={event.resource}"))
        factors.add((FactorDimension.ACTIVITY, f"activity={event.activity}"))
    factors.add((FactorDimension.VARIANT, f"variant={variant_fingerprint(activities)}"))
    if len(set(activities)) < len(activities):
        factors.add((FactorDimension.PATTERN, "pattern=rework"))
    return factors


def analyze_root_cause(
    process_id: str, events: list[Event], threshold_seconds: float | None = None
) -> RootCauseReport:
    """Rank the case attributes most associated with slow cases.

    Args:
        process_id: Process the report is attributed to.
        events: The raw event log (grouped into cases internally).
        threshold_seconds: Duration above which a case is 'bad'. ``None`` (default)
            derives the upper-quartile (P75) duration from the log.

    Returns:
        A :class:`RootCauseReport` with factors sorted by impact score.
    """
    cases = group_cases(events)
    durations = {cid: case_duration(trace) for cid, trace in cases.items()}
    total = len(cases)
    if total == 0:
        return RootCauseReport(
            process_id=process_id, total_cases=0, bad_cases=0, threshold_seconds=0.0
        )

    cutoff = (
        threshold_seconds
        if threshold_seconds is not None
        else percentile(list(durations.values()), _SLOW_PERCENTILE)
    )
    bad = {cid for cid, dur in durations.items() if dur > cutoff}
    baseline = len(bad) / total if total else 0.0

    seen: dict[tuple[FactorDimension, str], list[int]] = defaultdict(lambda: [0, 0])
    for cid, trace in cases.items():
        is_bad = 1 if cid in bad else 0
        for factor in _case_factors(trace):
            seen[factor][0] += 1
            seen[factor][1] += is_bad

    factors = _rank_factors(seen, baseline)
    return RootCauseReport(
        process_id=process_id,
        threshold_seconds=round(cutoff, 4),
        total_cases=total,
        bad_cases=len(bad),
        baseline_rate=round(baseline, 4),
        factors=factors,
    )


def _rank_factors(
    seen: dict[tuple[FactorDimension, str], list[int]], baseline: float
) -> list[RootCauseFactor]:
    """Turn raw (support, bad) counts into ranked, over-represented factors."""
    out: list[RootCauseFactor] = []
    for (dimension, value), (support, bad_count) in seen.items():
        if support < _MIN_SUPPORT:
            continue
        rate = bad_count / support
        lift = rate / baseline if baseline > 0 else 0.0
        if lift <= 1.0:  # only factors over-represented among bad cases
            continue
        out.append(
            RootCauseFactor(
                dimension=dimension,
                factor=value,
                cases_with_factor=support,
                bad_with_factor=bad_count,
                factor_breach_rate=round(rate, 4),
                baseline_rate=round(baseline, 4),
                lift=round(lift, 4),
                impact_score=round((rate - baseline) * support, 4),
            )
        )
    out.sort(key=lambda f: f.impact_score, reverse=True)
    return out[:_MAX_FACTORS]


__all__ = ["analyze_root_cause"]
