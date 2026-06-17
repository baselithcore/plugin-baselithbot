"""Pure descriptive-statistics helpers shared by the insight engines.

Variant, performance, and root-cause analysis all need percentile and
distribution summaries over case durations and waiting times. Kept dependency-free
(no numpy) and deterministic so the engines stay pure and unit-testable, and the
plugin's optional ``rag``/``nlp`` extras are never dragged in for basic maths.
"""

from __future__ import annotations

from statistics import fmean

from pydantic import BaseModel, Field


def percentile(values: list[float], pct: float) -> float:
    """Linear-interpolation percentile (``pct`` in 0..100); 0.0 for an empty list.

    Matches the common "type 7" definition (NumPy's default), so results line up
    with what an analyst would compute in pandas/Excel.
    """
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    rank = (pct / 100.0) * (len(ordered) - 1)
    low = int(rank)
    high = min(low + 1, len(ordered) - 1)
    frac = rank - low
    return ordered[low] + (ordered[high] - ordered[low]) * frac


class Distribution(BaseModel):
    """A compact summary of a numeric sample (durations, waits, …)."""

    count: int = Field(..., description="Number of observations.")
    mean: float = Field(default=0.0, description="Arithmetic mean.")
    p50: float = Field(default=0.0, description="Median (50th percentile).")
    p90: float = Field(default=0.0, description="90th percentile.")
    p95: float = Field(default=0.0, description="95th percentile.")
    p99: float = Field(default=0.0, description="99th percentile.")
    min: float = Field(default=0.0, description="Smallest observation.")
    max: float = Field(default=0.0, description="Largest observation.")


def summarize(values: list[float]) -> Distribution:
    """Roll a numeric sample into a :class:`Distribution` (zeros when empty)."""
    if not values:
        return Distribution(count=0)
    return Distribution(
        count=len(values),
        mean=round(fmean(values), 4),
        p50=round(percentile(values, 50), 4),
        p90=round(percentile(values, 90), 4),
        p95=round(percentile(values, 95), 4),
        p99=round(percentile(values, 99), 4),
        min=round(min(values), 4),
        max=round(max(values), 4),
    )


__all__ = ["percentile", "summarize", "Distribution"]
