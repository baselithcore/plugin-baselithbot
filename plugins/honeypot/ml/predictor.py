"""TTP Predictor for Anticipating Attacker Behavior.

Uses a Random Forest classifier to predict next likely TTPs
based on current session behavior and command sequences.

The predictor is designed for:
- Low latency inference (<50ms p99)
- Interpretable predictions with confidence scores
- Incremental training capability
"""

import asyncio
from core.observability.logging import get_logger
import time
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np

from ..emulation.models import SessionState, TTP, TTPPrediction
from .features import FeatureExtractor

logger = get_logger(__name__)


# TTP to class index mapping
TTP_TO_IDX: Dict[TTP, int] = {ttp: i for i, ttp in enumerate(TTP)}
IDX_TO_TTP: Dict[int, TTP] = {i: ttp for ttp, i in TTP_TO_IDX.items()}

# Number of TTP classes
NUM_CLASSES = len(TTP)


class TTPPredictor:
    """Predict attacker TTPs from session behavior.

    Uses a Random Forest classifier trained on historical attack data
    to predict the most likely next tactics, techniques, and procedures.

    Example:
        >>> predictor = TTPPredictor()
        >>> predictor.load_model("/path/to/model.joblib")
        >>> predictions = await predictor.predict_next_ttp(session)
        >>> for pred in predictions:
        ...     print(f"{pred.ttp}: {pred.confidence:.2f}")
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        threshold: float = 0.7,
        max_inference_time_ms: float = 50.0,
    ):
        """Initialize TTP predictor.

        Args:
            model_path: Path to trained model file
            threshold: Minimum confidence threshold for predictions
            max_inference_time_ms: Maximum inference time budget
        """
        self.model_path = model_path
        self.threshold = threshold
        self.max_inference_time_ms = max_inference_time_ms

        self.feature_extractor = FeatureExtractor()
        self._model = None
        self._model_loaded = False
        self._inference_times: List[float] = []

        # If model path provided, attempt load
        if model_path:
            try:
                self.load_model(model_path)
            except FileNotFoundError:
                logger.warning(f"Model not found at {model_path}, using fallback")

    def load_model(self, path: str) -> None:
        """Load trained model from disk.

        Args:
            path: Path to joblib model file

        Raises:
            FileNotFoundError: If model file doesn't exist
        """
        import joblib

        model_path = Path(path)
        if not model_path.exists():
            raise FileNotFoundError(f"Model not found: {path}")

        self._model = joblib.load(model_path)
        self._model_loaded = True
        logger.info(f"TTP predictor model loaded from {path}")

    def save_model(self, path: str) -> None:
        """Save trained model to disk.

        Args:
            path: Path to save model
        """
        import joblib

        if self._model is None:
            raise ValueError("No model to save")

        model_path = Path(path)
        model_path.parent.mkdir(parents=True, exist_ok=True)

        joblib.dump(self._model, model_path)
        logger.info(f"TTP predictor model saved to {path}")

    async def predict_next_ttp(
        self,
        session: SessionState,
        top_k: int = 3,
    ) -> List[TTPPrediction]:
        """Predict most likely next TTPs for a session.

        Args:
            session: Current session state
            top_k: Number of top predictions to return

        Returns:
            List of TTPPrediction with confidence scores
        """
        start_time = time.perf_counter()

        try:
            # Use fallback if model not loaded
            if not self._model_loaded:
                return await self._fallback_prediction(session, top_k)

            # Extract features
            features = self.feature_extractor.extract(session)

            # Run inference in thread pool to not block event loop
            loop = asyncio.get_event_loop()
            probabilities = await loop.run_in_executor(
                None, self._predict_proba, features
            )

            # Get top-k predictions above threshold
            predictions = self._decode_predictions(probabilities, top_k)

            # Track inference time
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            self._record_inference_time(elapsed_ms)

            if elapsed_ms > self.max_inference_time_ms:
                logger.warning(
                    f"TTP prediction exceeded time budget: {elapsed_ms:.1f}ms > {self.max_inference_time_ms}ms"
                )

            return predictions

        except Exception as e:
            logger.error(f"TTP prediction failed: {e}")
            return await self._fallback_prediction(session, top_k)

    def predict_sync(
        self,
        session: SessionState,
        top_k: int = 3,
    ) -> List[TTPPrediction]:
        """Synchronous prediction (blocking).

        Use predict_next_ttp in async contexts.

        Args:
            session: Current session state
            top_k: Number of top predictions

        Returns:
            List of TTPPrediction
        """
        if not self._model_loaded:
            return self._fallback_prediction_sync(session, top_k)

        features = self.feature_extractor.extract(session)
        probabilities = self._predict_proba(features)
        return self._decode_predictions(probabilities, top_k)

    def _predict_proba(self, features: np.ndarray) -> np.ndarray:
        """Get class probabilities from model.

        Args:
            features: Feature vector

        Returns:
            Probability array for each TTP class
        """
        # Reshape for single sample
        X = features.reshape(1, -1)

        # Get probabilities
        if hasattr(self._model, "predict_proba"):
            proba = self._model.predict_proba(X)[0]
        else:
            # If model doesn't support probabilities, use predictions
            pred = self._model.predict(X)[0]
            proba = np.zeros(NUM_CLASSES)
            proba[pred] = 1.0

        return proba

    def _decode_predictions(
        self,
        probabilities: np.ndarray,
        top_k: int,
    ) -> List[TTPPrediction]:
        """Decode probability array to TTPPrediction list.

        Args:
            probabilities: Class probabilities
            top_k: Number of predictions to return

        Returns:
            List of TTPPrediction sorted by confidence
        """
        predictions = []

        # Get indices sorted by probability (descending)
        sorted_indices = np.argsort(probabilities)[::-1]

        for idx in sorted_indices[:top_k]:
            prob = float(probabilities[idx])

            if prob >= self.threshold:
                if idx < len(IDX_TO_TTP):
                    ttp = IDX_TO_TTP[idx]
                    predictions.append(
                        TTPPrediction(
                            ttp=ttp,
                            confidence=prob,
                            reasoning=f"Model confidence: {prob:.2%}",
                        )
                    )

        return predictions

    async def _fallback_prediction(
        self,
        session: SessionState,
        top_k: int,
    ) -> List[TTPPrediction]:
        """Rule-based fallback when model unavailable.

        Uses simple heuristics based on recent commands.

        Args:
            session: Current session state
            top_k: Number of predictions

        Returns:
            List of TTPPrediction
        """
        return self._fallback_prediction_sync(session, top_k)

    def _fallback_prediction_sync(
        self,
        session: SessionState,
        top_k: int,
    ) -> List[TTPPrediction]:
        """Synchronous fallback prediction.

        Args:
            session: Current session state
            top_k: Number of predictions

        Returns:
            List of TTPPrediction based on heuristics
        """
        predictions = []
        recent_commands = [r.command for r in session.command_history[-5:]]
        all_commands = " ".join(recent_commands).lower()

        # Check for TTPs based on command patterns
        ttp_indicators = [
            (TTP.CREDENTIAL_DUMPING, ["shadow", "passwd", "hashdump", "mimikatz"], 0.8),
            (TTP.FILE_DISCOVERY, ["find", "locate", "ls -la", "tree"], 0.7),
            (TTP.SYSTEM_INFO_DISCOVERY, ["uname", "hostname", "id", "cat /etc"], 0.7),
            (TTP.SSH_AUTHORIZED_KEYS, ["authorized_keys", ".ssh"], 0.85),
            (TTP.NETWORK_DISCOVERY, ["netstat", "ss", "ifconfig", "ip addr"], 0.7),
            (TTP.COMMAND_SCRIPTING, ["python -c", "bash -c", "perl -e"], 0.75),
            (TTP.EXFIL_OVER_C2, ["curl.*-d", "wget.*post", "nc.*-e"], 0.8),
            (TTP.INDICATOR_REMOVAL, ["history -c", "rm.*log", "shred"], 0.85),
        ]

        for ttp, patterns, base_confidence in ttp_indicators:
            for pattern in patterns:
                if pattern in all_commands:
                    predictions.append(
                        TTPPrediction(
                            ttp=ttp,
                            confidence=base_confidence,
                            reasoning=f"Pattern match: '{pattern}'",
                        )
                    )
                    break

        # Sort by confidence and return top-k
        predictions.sort(key=lambda p: p.confidence, reverse=True)
        return predictions[:top_k]

    def _record_inference_time(self, elapsed_ms: float) -> None:
        """Record inference time for monitoring.

        Args:
            elapsed_ms: Inference time in milliseconds
        """
        self._inference_times.append(elapsed_ms)

        # Keep only recent samples
        if len(self._inference_times) > 1000:
            self._inference_times = self._inference_times[-500:]

    def get_inference_stats(self) -> Dict[str, float]:
        """Get inference timing statistics.

        Returns:
            Dict with mean, p50, p95, p99 latencies
        """
        if not self._inference_times:
            return {"mean": 0, "p50": 0, "p95": 0, "p99": 0}

        times = sorted(self._inference_times)
        n = len(times)

        return {
            "mean": sum(times) / n,
            "p50": times[n // 2],
            "p95": times[int(n * 0.95)],
            "p99": times[int(n * 0.99)] if n >= 100 else times[-1],
        }

    def is_model_loaded(self) -> bool:
        """Check if model is loaded.

        Returns:
            True if model is ready for inference
        """
        return self._model_loaded

    def train(
        self,
        sessions: List[SessionState],
        labels: List[List[TTP]],
    ) -> None:
        """Train model on labeled session data.

        Args:
            sessions: List of training sessions
            labels: List of TTP labels for each session (multi-label)
        """
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.multioutput import MultiOutputClassifier

        logger.info(f"Training TTP predictor on {len(sessions)} sessions")

        # Extract features
        X = np.array([self.feature_extractor.extract(s) for s in sessions])

        # Convert labels to multi-label format
        y = np.zeros((len(labels), NUM_CLASSES), dtype=np.int32)
        for i, session_labels in enumerate(labels):
            for ttp in session_labels:
                y[i, TTP_TO_IDX[ttp]] = 1

        # Train Random Forest
        base_clf = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            min_samples_split=5,
            n_jobs=-1,
            random_state=42,
        )

        self._model = MultiOutputClassifier(base_clf)
        self._model.fit(X, y)
        self._model_loaded = True

        # Update feature extractor stats
        self.feature_extractor.update_stats(sessions)

        logger.info("TTP predictor training complete")

    def get_feature_importance(self) -> Dict[str, float]:
        """Get feature importance from trained model.

        Returns:
            Dict mapping feature names to importance scores
        """
        if not self._model_loaded or not hasattr(self._model, "estimators_"):
            return {}

        # Average importance across all estimators
        importances = np.zeros(40)  # 40 features

        for estimator in self._model.estimators_:
            if hasattr(estimator, "feature_importances_"):
                importances += estimator.feature_importances_

        importances /= len(self._model.estimators_)

        feature_names = self.feature_extractor.get_feature_names()
        return dict(zip(feature_names, importances))
