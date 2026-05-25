"""Red Agent ML / LLM enrichment layer.

Optional services that augment the deterministic scanner pipeline with
language-model and embedding-based intelligence:

- :class:`LLMTriageService` — re-evaluates findings (severity, false
  positives, remediation prose).
- :class:`SemanticDedupService` — cross-scan dedup via Qdrant
  embeddings, links recurring findings instead of duplicating them.

Every service is **fail-open**: a missing dependency, a provider error,
or a parse failure returns the input findings unchanged. The
deterministic core scan flow is never blocked by an ML failure.
"""

from __future__ import annotations

from plugins.red_agent.ml.dedup import DedupResult, SemanticDedupService
from plugins.red_agent.ml.factories import (
    build_anomaly_detector,
    build_dedup_service,
    build_fp_classifier,
    build_triage_service,
)
from plugins.red_agent.ml.models import (
    AnomalyDetectorService,
    AnomalyScore,
    FPClassifierService,
)
from plugins.red_agent.ml.triage import LLMTriageService, TriageVerdict

__all__ = [
    "AnomalyDetectorService",
    "AnomalyScore",
    "DedupResult",
    "FPClassifierService",
    "LLMTriageService",
    "SemanticDedupService",
    "TriageVerdict",
    "build_anomaly_detector",
    "build_dedup_service",
    "build_fp_classifier",
    "build_triage_service",
]
