"""M3 — Isolation-Forest host anomaly detector.

Aggregates rolling per-host telemetry windows from
``red_agent_agent_telemetry`` into a small numeric feature vector,
fits / reuses an :class:`sklearn.ensemble.IsolationForest`, and emits
synthetic findings for hosts whose feature vector is flagged as an
outlier.

Why Isolation Forest, not autoencoder / LSTM:

- One-shot, unsupervised — no labeled corpus needed to bootstrap.
- Linear in samples × trees, runs comfortably on a single backend pod
  for fleets of thousands of hosts.
- Decision-function score is monotonic, so the operator can tune a
  single ``contamination`` knob without re-training.

Output is a list of :class:`AnomalyScore`, **not** a side effect — the
consumer (background task in :mod:`plugins.red_agent.tasks`) decides
how to materialize alerts (synthetic findings, audit events, push
notifications). Keeps this module pure-compute and unit-testable.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from core.observability.logging import get_logger

logger = get_logger(__name__)


_HIGH_SEVERITIES = {"high", "critical"}


@dataclass(slots=True)
class AnomalyScore:
    """Per-host outlier score for a telemetry window."""

    agent_uuid: UUID
    tenant_id: str
    score: float  # IsolationForest decision_function: lower = more anomalous
    is_anomaly: bool
    sample_count: int
    features: dict[str, float]
    window_start: datetime
    window_end: datetime


def aggregate_per_host_features(
    events: list[dict[str, Any]],
    *,
    window_start: datetime,
    window_end: datetime,
) -> dict[tuple[str, UUID], dict[str, float]]:
    """Roll up raw telemetry events into per-host feature dicts.

    The features capture the dimensions an analyst would intuitively
    eyeball: how chatty is the host, how diverse are its event kinds,
    is it producing a spike of high-severity records, are
    correlation-ids clustering. Order matters: each sklearn input row
    must list features in :data:`_FEATURE_ORDER`.
    """
    window_seconds = max(1.0, (window_end - window_start).total_seconds())
    grouped: dict[tuple[str, UUID], list[dict[str, Any]]] = defaultdict(list)
    for ev in events:
        try:
            agent_uuid = UUID(str(ev["agent_uuid"]))
        except (KeyError, ValueError):
            continue
        tenant = str(ev.get("tenant_id") or "default")
        grouped[(tenant, agent_uuid)].append(ev)

    out: dict[tuple[str, UUID], dict[str, float]] = {}
    for key, host_events in grouped.items():
        n = len(host_events)
        kinds = {e.get("kind") for e in host_events}
        high_sev = sum(
            1
            for e in host_events
            if (e.get("severity") or "").lower() in _HIGH_SEVERITIES
        )
        correlations = {
            e.get("correlation_id") for e in host_events if e.get("correlation_id")
        }
        attribute_keys = sum(
            len(e.get("attributes") or {})
            if isinstance(e.get("attributes"), dict)
            else 0
            for e in host_events
        )
        out[key] = {
            "events_per_minute": (n / window_seconds) * 60.0,
            "kind_diversity": float(len(kinds)),
            "high_sev_ratio": (high_sev / n) if n else 0.0,
            "correlation_density": (len(correlations) / n) if n else 0.0,
            "avg_attribute_keys": (attribute_keys / n) if n else 0.0,
            "_count": float(n),
        }
    return out


# Stable feature order consumed by IsolationForest. NEVER reorder
# without retraining — the model's split planes are tied to this layout.
_FEATURE_ORDER: list[str] = [
    "events_per_minute",
    "kind_diversity",
    "high_sev_ratio",
    "correlation_density",
    "avg_attribute_keys",
]


def _vectorize(features: dict[str, float]) -> list[float]:
    return [features[k] for k in _FEATURE_ORDER]


class AnomalyDetectorService:
    """Stateless scoring service.

    The model is refit on every :meth:`score_window` call. Isolation
    Forest training cost is small (≪ scoring an LLM on the same data)
    and re-fitting per window keeps the detector locally adaptive —
    a host that drifts into a new normal does not stay flagged
    forever.
    """

    def __init__(
        self,
        *,
        contamination: float,
        min_samples: int,
        enabled: bool,
        random_state: int = 42,
    ) -> None:
        self._contamination = contamination
        self._min_samples = min_samples
        self._enabled_flag = enabled
        self._random_state = random_state

    @property
    def enabled(self) -> bool:
        if not self._enabled_flag:
            return False
        try:
            import sklearn  # noqa: F401  pragma: no cover

            return True
        except ImportError:
            return False

    def score_window(
        self,
        *,
        events: list[dict[str, Any]],
        window_start: datetime | None = None,
        window_end: datetime | None = None,
    ) -> list[AnomalyScore]:
        """Score one rolling window of telemetry events."""
        if not self.enabled or not events:
            return []
        end = window_end or datetime.now(timezone.utc)
        start = window_start or (end - timedelta(minutes=15))
        per_host = aggregate_per_host_features(
            events, window_start=start, window_end=end
        )
        if len(per_host) < self._min_samples:
            return []
        keys = list(per_host.keys())
        x = [_vectorize(per_host[k]) for k in keys]
        try:
            from sklearn.ensemble import IsolationForest  # type: ignore[import-untyped]

            model = IsolationForest(
                contamination=self._contamination,  # type: ignore[arg-type]
                random_state=self._random_state,
                n_estimators=100,
            )
            model.fit(x)
            scores = model.decision_function(x)
            preds = model.predict(x)
        except Exception as e:  # noqa: BLE001
            logger.warning("red_agent.ml.anomaly.fit_failed", extra={"err": str(e)})
            return []

        results: list[AnomalyScore] = []
        for (tenant, agent_uuid), score, pred in zip(keys, scores, preds):
            features = per_host[(tenant, agent_uuid)]
            results.append(
                AnomalyScore(
                    agent_uuid=agent_uuid,
                    tenant_id=tenant,
                    score=float(score),
                    is_anomaly=bool(pred == -1),
                    sample_count=int(features.get("_count", 0)),
                    features={k: features[k] for k in _FEATURE_ORDER},
                    window_start=start,
                    window_end=end,
                )
            )
        return results
