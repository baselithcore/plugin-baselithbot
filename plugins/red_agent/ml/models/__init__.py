"""Classical-ML models layered on top of the Red Agent pipeline.

- :class:`FPClassifierService` (M1) — gradient-boosting binary classifier
  predicting the false-positive probability of a finding.
- :class:`AnomalyDetectorService` (M3) — Isolation-Forest scoring of
  rolling per-host telemetry windows, materializing anomalies as
  synthetic findings.

Both services follow the same fail-open contract as the LLM layer: a
missing model artifact, an absent dependency (``scikit-learn``), or a
runtime error is logged and the service degrades to a no-op pass-through
so the deterministic scan flow is never blocked.
"""

from __future__ import annotations

from plugins.red_agent.ml.models.anomaly import (
    AnomalyDetectorService,
    AnomalyScore,
)
from plugins.red_agent.ml.models.fp_classifier import FPClassifierService

__all__ = [
    "AnomalyDetectorService",
    "AnomalyScore",
    "FPClassifierService",
]
