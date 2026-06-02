"""Prometheus metrics for the BaselithMed plugin.

Each metric uses the ``baselithmed_`` prefix so it is trivially scrapable
from the global :mod:`core.observability` registry without colliding with
other plugins. Histograms use SI-friendly buckets (subseconds → seconds)
because the medical workflow mixes fast heuristic paths (<10 ms) with
slow LLM finalize calls (10-60 s).

The module intentionally fails-quiet: if the Prometheus client raises
(label cardinality issues, registry conflicts during hot-reload) we log
and move on — observability must never break the clinical path.
"""

from __future__ import annotations

from typing import Any

from prometheus_client import Counter, Histogram

from core.observability.logging import get_logger

logger = get_logger(__name__)


SESSIONS_CREATED = Counter(
    "baselithmed_sessions_created_total",
    "Number of clinical sessions created.",
)

INTERVIEW_TURNS = Counter(
    "baselithmed_interview_turns_total",
    "Number of interview turns processed.",
)

TRIAGE_DECISIONS = Counter(
    "baselithmed_triage_decisions_total",
    "Triage code assignments emitted by the deterministic engine.",
    ["code"],
)

VALIDATIONS = Counter(
    "baselithmed_validations_total",
    "Clinician validation decisions recorded.",
    ["approved"],
)

INTERACTIONS_FINDINGS = Counter(
    "baselithmed_interactions_findings_total",
    "Drug-interaction findings surfaced to the UI.",
    ["severity", "kind"],
)

EHR_PUSH_ATTEMPTS = Counter(
    "baselithmed_ehr_push_attempts_total",
    "External EHR push attempts.",
    ["outcome"],
)

CHALLENGER_VERDICTS = Counter(
    "baselithmed_challenger_verdicts_total",
    "Verdicts emitted by the deterministic DDx Challenger.",
    ["verdict"],
)

FINALIZE_LATENCY = Histogram(
    "baselithmed_finalize_latency_seconds",
    "End-to-end latency of /triage/finalize requests.",
    buckets=(0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0, 120.0),
)

INTERVIEW_TURN_LATENCY = Histogram(
    "baselithmed_interview_turn_latency_seconds",
    "End-to-end latency of /interview turn requests.",
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

DX_TOP1_CONFIDENCE = Histogram(
    "baselithmed_dx_top1_confidence",
    "Top hypothesis confidence at the moment of validation.",
    buckets=(0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0),
)


def safe_increment(counter: Counter, **labels: str) -> None:
    """Best-effort label increment that never raises."""
    try:
        if labels:
            counter.labels(**labels).inc()
        else:
            counter.inc()
    except Exception as exc:  # noqa: BLE001 — observability must not break
        logger.debug("Metric increment failed: %s", exc)


def safe_observe(histogram: Histogram, value: float) -> None:
    """Best-effort histogram observation that never raises."""
    try:
        histogram.observe(value)
    except Exception as exc:  # noqa: BLE001 — observability must not break
        logger.debug("Metric observation failed: %s", exc)


def normalize_label(value: Any) -> str:
    """Convert arbitrary values to a safe Prometheus label string.

    Prometheus labels must be strings; ``True``/``False`` would render as
    ``"True"``/``"False"`` (not ``"true"``/``"false"``), and ``None``
    would crash on ``.labels()``. Bound everything through this helper.
    """
    if value is None:
        return "unknown"
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value).strip().lower() or "unknown"
