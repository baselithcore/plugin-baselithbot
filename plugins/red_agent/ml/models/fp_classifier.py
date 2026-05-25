"""M1 — Gradient-Boosting false-positive classifier.

Trained on the operator-supplied triage signal (``Finding.state`` set
to ``WONTFIX`` / ``ACCEPTED`` ⇒ FP, ``FIXED`` ⇒ TP). At inference time
the service projects each finding into the fixed feature vector
(see :mod:`plugins.red_agent.ml.models.features`) and returns the
predicted FP probability.

Inference is intentionally tiny (sklearn ``predict_proba`` on a
gradient-boosting tree → microseconds per finding), so the service runs
inline before the more expensive LLM-triage pass and short-circuits
high-confidence false positives without any LLM round-trip.

**Security / threat model for the model artifact.** Joblib uses pickle
under the hood — loading an attacker-controlled artifact would lead to
arbitrary code execution. The service therefore:

- loads only from a path declared in :class:`RedAgentConfig`
  (``ml_fp_classifier_model_path``), i.e. set by an operator with
  filesystem privileges;
- refuses to load when the path is missing or unreadable;
- enforces an integrity field (``feature_version``) on the artifact —
  a mismatched version disables the model. Future hardening can layer
  an ed25519 signature check on top, mirroring ``policy.py``.

Operators must treat the model directory as a trust boundary: do not
mount it from a writable shared volume; ship the artifact via the same
signed-bundle channel used for plugin integrity.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from core.observability.logging import get_logger
from plugins.red_agent.ml.models.features import (
    FEATURE_VERSION,
    extract_features,
    feature_dim,
)
from plugins.red_agent.models import Finding

logger = get_logger(__name__)

_MODEL_KEY = "model"
_VERSION_KEY = "feature_version"
_TRAINED_AT_KEY = "trained_at"


class FPClassifierService:
    """Inference wrapper around the trained FP classifier."""

    def __init__(
        self,
        *,
        model_path: str | Path | None,
        drop_threshold: float,
        enabled: bool,
    ) -> None:
        self._drop_threshold = drop_threshold
        self._enabled_flag = enabled
        self._model: Any = None
        if enabled and model_path:
            self._model = self._load(Path(model_path))

    @property
    def enabled(self) -> bool:
        return self._enabled_flag and self._model is not None

    def score(self, finding: Finding) -> float | None:
        """Return the predicted FP probability in [0, 1], or ``None``.

        ``None`` means "no opinion" (service disabled or model absent).
        Callers must not treat it as a low score.
        """
        if not self.enabled:
            return None
        try:
            features = extract_features(finding)
            proba = self._model.predict_proba([features])[0]
            # Class index 1 = positive class = "is false positive"
            return float(proba[1])
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.ml.fp_classifier.predict_failed", extra={"err": str(e)}
            )
            return None

    def annotate_and_filter(self, findings: list[Finding]) -> list[Finding]:
        """Score each finding, annotate ``evidence``, drop high-prob FPs."""
        if not self.enabled or not findings:
            return findings
        kept: list[Finding] = []
        for f in findings:
            score = self.score(f)
            if score is None:
                kept.append(f)
                continue
            new_evidence = dict(f.evidence) if isinstance(f.evidence, dict) else {}
            new_evidence["ml_fp_score"] = round(score, 4)
            mutated = f.model_copy(update={"evidence": new_evidence})
            if score >= self._drop_threshold:
                logger.info(
                    "red_agent.ml.fp_classifier.dropped",
                    extra={
                        "finding_id": str(f.id),
                        "scanner": f.scanner,
                        "score": score,
                    },
                )
                continue
            kept.append(mutated)
        return kept

    @staticmethod
    def _load(path: Path) -> Any:
        # Loading is a trust-boundary operation — see module docstring
        # for the operator contract that makes this safe.
        if not path.exists():
            logger.info(
                "red_agent.ml.fp_classifier.model_absent",
                extra={"path": str(path)},
            )
            return None
        try:
            import joblib  # type: ignore[import-untyped]
        except ImportError:
            logger.warning(
                "red_agent.ml.fp_classifier.joblib_unavailable",
                extra={"hint": "pip install joblib"},
            )
            return None
        try:
            payload = joblib.load(path)
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.ml.fp_classifier.load_failed",
                extra={"path": str(path), "err": str(e)},
            )
            return None
        if not isinstance(payload, dict) or _MODEL_KEY not in payload:
            logger.warning(
                "red_agent.ml.fp_classifier.malformed_artifact",
                extra={"path": str(path)},
            )
            return None
        version = payload.get(_VERSION_KEY)
        if version != FEATURE_VERSION:
            logger.warning(
                "red_agent.ml.fp_classifier.feature_version_mismatch",
                extra={
                    "path": str(path),
                    "artifact_version": version,
                    "expected_version": FEATURE_VERSION,
                },
            )
            return None
        return payload[_MODEL_KEY]


def train_classifier(
    *,
    samples: list[tuple[Finding, bool]],
    output_path: str | Path,
    n_estimators: int = 200,
    max_depth: int = 4,
    random_state: int = 42,
) -> dict[str, Any]:
    """Fit a gradient-boosting classifier on labeled samples.

    Build ``samples`` from persistence by mapping ``Finding.state``
    transitions:

    - ``state ∈ {WONTFIX, ACCEPTED}`` → label ``True`` (FP)
    - ``state == FIXED`` → label ``False`` (TP)
    - ``state == OPEN`` / ``TRIAGED`` → exclude (unlabeled)

    Returns a training summary dict for CI logging.
    """
    if not samples:
        raise ValueError("training set is empty")
    try:
        import joblib  # type: ignore[import-untyped]
        from sklearn.ensemble import (  # type: ignore[import-untyped]
            GradientBoostingClassifier,
        )
    except ImportError as e:
        raise RuntimeError(
            "scikit-learn and joblib are required for training. "
            "Install with: pip install scikit-learn joblib"
        ) from e

    x = [extract_features(f) for f, _ in samples]
    y = [1 if is_fp else 0 for _, is_fp in samples]
    if len(set(y)) < 2:
        raise ValueError("training set must contain both classes (TP and FP)")
    if len(x[0]) != feature_dim():
        raise RuntimeError("feature dimension mismatch — schema drift?")

    model = GradientBoostingClassifier(
        n_estimators=n_estimators,
        max_depth=max_depth,
        random_state=random_state,
    )
    model.fit(x, y)

    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        _MODEL_KEY: model,
        _VERSION_KEY: FEATURE_VERSION,
        _TRAINED_AT_KEY: datetime.now(timezone.utc).isoformat(),
    }
    joblib.dump(payload, out)

    summary = {
        "samples": len(samples),
        "positive_rate": round(sum(y) / len(y), 4),
        "feature_version": FEATURE_VERSION,
        "model_path": str(out),
    }
    logger.info(
        "red_agent.ml.fp_classifier.trained",
        extra={"summary": json.dumps(summary)},
    )
    return summary
