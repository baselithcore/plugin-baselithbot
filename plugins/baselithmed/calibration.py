"""Calibration metrics for the BaselithMed differential ranker.

Records (predicted_confidence, actual_outcome) pairs every time a clinician
validates a triage report. From those pairs computes:

    * **Brier score** — mean squared error between predicted probabilities
      and binary outcomes. Lower is better; range [0, 1]. Strict scoring
      rule: rewards both accuracy and calibration.
    * **Expected Calibration Error (ECE)** — buckets predictions by
      confidence and computes the weighted average distance between
      predicted confidence and empirical accuracy. Sensitive to local
      miscalibration even when the Brier score is acceptable.
    * **Reliability bins** — per-bucket ``(midpoint, accuracy, count)``
      tuples consumed by the UI to render a reliability diagram.

The ground-truth signal is the clinician's :class:`ReportStatus`
transition: ``VALIDATED`` means the top hypothesis was clinically
plausible (outcome = 1), ``REJECTED`` means the model was off-target
(outcome = 0). This is a coarse signal (a single bit per report) — it is
enough to track top-line calibration drift without forcing clinicians to
grade every hypothesis.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
from typing import Any, Final

_DEFAULT_BINS: Final[int] = 10
_MIN_SAMPLES_FOR_REPORT: Final[int] = 5


@dataclass(frozen=True)
class CalibrationSample:
    """One (confidence, outcome) datum tied to a session + hypothesis."""

    session_id: str
    hypothesis: str
    predicted_confidence: float
    outcome: int  # 1 = clinically plausible, 0 = rejected
    recorded_at: str  # ISO-8601 UTC


@dataclass(frozen=True)
class ReliabilityBin:
    midpoint: float
    accuracy: float
    count: int


@dataclass
class CalibrationReport:
    """Summary statistics over the accumulated calibration samples."""

    sample_count: int
    brier_score: float | None
    ece: float | None
    reliability_bins: list[ReliabilityBin] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_count": self.sample_count,
            "brier_score": self.brier_score,
            "ece": self.ece,
            "reliability_bins": [
                {"midpoint": b.midpoint, "accuracy": b.accuracy, "count": b.count}
                for b in self.reliability_bins
            ],
        }


def _bin_index(confidence: float, num_bins: int) -> int:
    """Map ``confidence`` ∈ [0, 1] into ``[0, num_bins-1]``."""
    if confidence >= 1.0:
        return num_bins - 1
    if confidence <= 0.0:
        return 0
    return int(confidence * num_bins)


def brier_score(samples: list[CalibrationSample]) -> float:
    """Standard Brier score: ``mean((confidence - outcome)^2)``."""
    if not samples:
        return 0.0
    total = sum((s.predicted_confidence - s.outcome) ** 2 for s in samples)
    return total / len(samples)


def expected_calibration_error(
    samples: list[CalibrationSample],
    *,
    num_bins: int = _DEFAULT_BINS,
) -> float:
    """Weighted average of per-bin |accuracy − confidence|."""
    if not samples:
        return 0.0
    buckets: list[list[CalibrationSample]] = [[] for _ in range(num_bins)]
    for s in samples:
        buckets[_bin_index(s.predicted_confidence, num_bins)].append(s)

    total = len(samples)
    ece = 0.0
    for bucket in buckets:
        if not bucket:
            continue
        conf_mean = sum(s.predicted_confidence for s in bucket) / len(bucket)
        acc_mean = sum(s.outcome for s in bucket) / len(bucket)
        ece += (len(bucket) / total) * abs(acc_mean - conf_mean)
    return ece


def reliability_bins(
    samples: list[CalibrationSample],
    *,
    num_bins: int = _DEFAULT_BINS,
) -> list[ReliabilityBin]:
    """Return per-bucket reliability stats for diagram rendering."""
    buckets: list[list[CalibrationSample]] = [[] for _ in range(num_bins)]
    for s in samples:
        buckets[_bin_index(s.predicted_confidence, num_bins)].append(s)

    out: list[ReliabilityBin] = []
    for i, bucket in enumerate(buckets):
        if not bucket:
            continue
        midpoint = (i + 0.5) / num_bins
        accuracy = sum(s.outcome for s in bucket) / len(bucket)
        out.append(
            ReliabilityBin(midpoint=midpoint, accuracy=accuracy, count=len(bucket))
        )
    return out


class CalibrationStore:
    """Thread-safe append-only accumulator of calibration samples."""

    def __init__(self) -> None:
        self._samples: list[CalibrationSample] = []
        self._lock = RLock()

    def record(
        self,
        *,
        session_id: str,
        hypothesis: str,
        predicted_confidence: float,
        outcome: int,
    ) -> CalibrationSample:
        if outcome not in (0, 1):
            raise ValueError("outcome must be 0 or 1")
        sample = CalibrationSample(
            session_id=session_id,
            hypothesis=hypothesis,
            predicted_confidence=max(0.0, min(1.0, float(predicted_confidence))),
            outcome=outcome,
            recorded_at=datetime.now(timezone.utc).isoformat(),
        )
        with self._lock:
            self._samples.append(sample)
        return sample

    def samples(self) -> list[CalibrationSample]:
        with self._lock:
            return list(self._samples)

    def report(self, *, num_bins: int = _DEFAULT_BINS) -> CalibrationReport:
        with self._lock:
            samples = list(self._samples)
        if len(samples) < _MIN_SAMPLES_FOR_REPORT:
            return CalibrationReport(
                sample_count=len(samples),
                brier_score=None,
                ece=None,
                reliability_bins=[],
            )
        return CalibrationReport(
            sample_count=len(samples),
            brier_score=brier_score(samples),
            ece=expected_calibration_error(samples, num_bins=num_bins),
            reliability_bins=reliability_bins(samples, num_bins=num_bins),
        )
