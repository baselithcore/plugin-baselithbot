"""Statistical anomaly detection and breach forecasting (pure, metric-driven).

Complements the threshold-based :mod:`.detection`: instead of only reacting when
a KPI already breaches its target, this module flags statistical outliers
(z-score over a rolling window) and *forecasts* an upcoming breach from the
recent trend (least-squares slope projected toward the target). The forecast
powers a proactive ``PREDICTED_BREACH`` automation trigger — catching trouble
before the target is crossed.

Deterministic and side-effect-free over a KPI's sample window.
"""

from __future__ import annotations

import math
from datetime import datetime

from pydantic import BaseModel, Field

from .models import KpiDefinition, KpiDirection, MetricSample

# Minimum samples before statistics are meaningful.
_MIN_SAMPLES = 8
# Rolling window for both anomaly detection and trend forecasting.
_WINDOW = 20
# Default z-score threshold for an outlier.
_Z_THRESHOLD = 3.0
# How many samples ahead the forecast projects.
_HORIZON = 10


class Anomaly(BaseModel):
    """A statistically anomalous KPI observation."""

    process_id: str
    kpi_id: str
    value: float
    expected: float = Field(..., description="Rolling-window mean.")
    z_score: float = Field(..., description="Std-devs from the mean (signed).")
    at: datetime


class BreachForecast(BaseModel):
    """A linear-trend projection of a KPI toward its target."""

    process_id: str
    kpi_id: str
    current: float
    target: float | None = None
    slope_per_sample: float = 0.0
    projected_value: float = 0.0
    will_breach: bool = False
    samples_to_breach: int | None = None
    horizon: int = _HORIZON


def detect_anomalies(
    kpi: KpiDefinition,
    samples: list[MetricSample],
    *,
    window: int = _WINDOW,
    z_threshold: float = _Z_THRESHOLD,
) -> list[Anomaly]:
    """Flag samples in the recent window whose z-score exceeds the threshold."""
    recent = samples[-window:]
    if len(recent) < _MIN_SAMPLES:
        return []
    values = [s.value for s in recent]
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    std = math.sqrt(variance)
    if std == 0:
        return []
    out: list[Anomaly] = []
    for sample in recent:
        z = (sample.value - mean) / std
        if abs(z) >= z_threshold:
            out.append(
                Anomaly(
                    process_id=sample.process_id,
                    kpi_id=kpi.id,
                    value=sample.value,
                    expected=round(mean, 4),
                    z_score=round(z, 2),
                    at=sample.timestamp,
                )
            )
    return out


def forecast_breach(
    kpi: KpiDefinition,
    samples: list[MetricSample],
    *,
    window: int = _WINDOW,
    horizon: int = _HORIZON,
) -> BreachForecast | None:
    """Project the KPI's recent trend toward its target; None if not forecastable."""
    if kpi.target is None:
        return None
    recent = samples[-window:]
    if len(recent) < _MIN_SAMPLES:
        return None
    values = [s.value for s in recent]
    slope, intercept = _least_squares(values)
    n = len(values)
    current = values[-1]
    projected = intercept + slope * (n - 1 + horizon)
    will_breach, steps = _breach_eta(
        kpi.direction, current, kpi.target, slope, projected, horizon
    )
    return BreachForecast(
        process_id=recent[0].process_id,
        kpi_id=kpi.id,
        current=round(current, 4),
        target=kpi.target,
        slope_per_sample=round(slope, 6),
        projected_value=round(projected, 4),
        will_breach=will_breach,
        samples_to_breach=steps,
        horizon=horizon,
    )


def _least_squares(values: list[float]) -> tuple[float, float]:
    """Return (slope, intercept) of the best-fit line over evenly-spaced points."""
    n = len(values)
    xs = range(n)
    sum_x = sum(xs)
    sum_y = sum(values)
    sum_xy = sum(i * v for i, v in zip(xs, values))
    sum_xx = sum(i * i for i in xs)
    denom = n * sum_xx - sum_x * sum_x
    if denom == 0:
        return 0.0, sum_y / n
    slope = (n * sum_xy - sum_x * sum_y) / denom
    intercept = (sum_y - slope * sum_x) / n
    return slope, intercept


def _breach_eta(
    direction: KpiDirection,
    current: float,
    target: float,
    slope: float,
    projected: float,
    horizon: int,
) -> tuple[bool, int | None]:
    """Decide whether/when the trend crosses the target (direction-aware)."""
    minimize = direction is KpiDirection.MINIMIZE
    already = current > target if minimize else current < target
    if already:
        return True, 0
    worsening = slope > 0 if minimize else slope < 0
    if not worsening or slope == 0:
        return False, None
    steps = math.ceil((target - current) / slope)
    if steps <= 0:
        return False, None
    crosses = projected > target if minimize else projected < target
    return (steps <= horizon and crosses), (steps if steps <= horizon else None)


__all__ = ["Anomaly", "BreachForecast", "detect_anomalies", "forecast_breach"]
