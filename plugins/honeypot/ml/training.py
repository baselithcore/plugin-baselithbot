"""TTP Training Pipeline for Model Training.

Provides continuous and batch training capabilities for the TTP predictor
using historical attack session data.

Features:
- Incremental training on new data
- Data validation and preprocessing
- Model evaluation and metrics
- Training history tracking
"""

from core.observability.logging import get_logger
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ..emulation.models import SessionState, TTP
from .features import FeatureExtractor
from .predictor import TTP_TO_IDX, TTPPredictor

logger = get_logger(__name__)


class TTPTrainingPipeline:
    """Training pipeline for TTP prediction models.

    Supports both batch training on historical data and
    incremental training on new sessions.

    Example:
        >>> pipeline = TTPTrainingPipeline()
        >>> pipeline.add_training_sample(session, detected_ttps)
        >>> if pipeline.should_train():
        ...     predictor = pipeline.train()
        ...     predictor.save_model("model.joblib")
    """

    def __init__(
        self,
        min_samples: int = 500,
        batch_size: int = 100,
        validation_split: float = 0.2,
        model_path: Optional[str] = None,
    ):
        """Initialize training pipeline.

        Args:
            min_samples: Minimum samples before training starts
            batch_size: Samples per training batch
            validation_split: Fraction for validation
            model_path: Path to save trained models
        """
        self.min_samples = min_samples
        self.batch_size = batch_size
        self.validation_split = validation_split
        self.model_path = model_path

        self.feature_extractor = FeatureExtractor()

        # Training data buffers
        self._sessions: List[SessionState] = []
        self._labels: List[List[TTP]] = []

        # Training history
        self._training_runs: List[Dict[str, Any]] = []
        self._last_training: Optional[datetime] = None

    def add_training_sample(
        self,
        session: SessionState,
        detected_ttps: List[TTP],
    ) -> None:
        """Add a labeled session for training.

        Args:
            session: Attack session
            detected_ttps: List of TTPs detected in session
        """
        if not detected_ttps:
            return

        self._sessions.append(session)
        self._labels.append(detected_ttps)

        logger.debug(
            f"Training sample added: {len(detected_ttps)} TTPs, total={len(self._sessions)}"
        )

    def should_train(self) -> bool:
        """Check if training should be triggered.

        Returns:
            True if enough samples for training
        """
        return len(self._sessions) >= self.min_samples

    def get_sample_count(self) -> int:
        """Get current number of training samples.

        Returns:
            Number of samples
        """
        return len(self._sessions)

    def train(self) -> TTPPredictor:
        """Train model on accumulated samples.

        Returns:
            Trained TTPPredictor
        """
        if not self.should_train():
            raise ValueError(
                f"Insufficient samples: {len(self._sessions)} < {self.min_samples}"
            )

        logger.info(f"Starting training on {len(self._sessions)} samples")
        start_time = datetime.now(timezone.utc)

        # Split data
        train_sessions, val_sessions, train_labels, val_labels = self._split_data()

        # Create and train predictor
        predictor = TTPPredictor()
        predictor.train(train_sessions, train_labels)

        # Evaluate
        metrics = self._evaluate(predictor, val_sessions, val_labels)

        # Record training run
        training_record = {
            "timestamp": start_time.isoformat(),
            "train_samples": len(train_sessions),
            "val_samples": len(val_sessions),
            "metrics": metrics,
        }
        self._training_runs.append(training_record)
        self._last_training = start_time

        logger.info(f"Training complete: accuracy={metrics['accuracy']:.2%}")

        # Save model if path specified
        if self.model_path:
            predictor.save_model(self.model_path)

        return predictor

    def train_incremental(self, predictor: TTPPredictor) -> TTPPredictor:
        """Incremental training on new samples.

        Uses warm start to continue training existing model.

        Args:
            predictor: Existing predictor to update

        Returns:
            Updated predictor
        """
        if len(self._sessions) < self.batch_size:
            logger.debug("Insufficient new samples for incremental training")
            return predictor

        # Only train on recent samples
        recent_sessions = self._sessions[-self.batch_size :]
        recent_labels = self._labels[-self.batch_size :]

        logger.info(f"Incremental training on {len(recent_sessions)} samples")

        # Retrain with warm start
        predictor.train(recent_sessions, recent_labels)

        if self.model_path:
            predictor.save_model(self.model_path)

        return predictor

    def _split_data(
        self,
    ) -> Tuple[
        List[SessionState], List[SessionState], List[List[TTP]], List[List[TTP]]
    ]:
        """Split data into training and validation sets.

        Returns:
            Tuple of (train_sessions, val_sessions, train_labels, val_labels)
        """
        n = len(self._sessions)
        n_val = int(n * self.validation_split)

        # Shuffle indices
        indices = list(range(n))
        np.random.shuffle(indices)

        val_indices = set(indices[:n_val])

        train_sessions = []
        train_labels = []
        val_sessions = []
        val_labels = []

        for i in range(n):
            if i in val_indices:
                val_sessions.append(self._sessions[i])
                val_labels.append(self._labels[i])
            else:
                train_sessions.append(self._sessions[i])
                train_labels.append(self._labels[i])

        return train_sessions, val_sessions, train_labels, val_labels

    def _evaluate(
        self,
        predictor: TTPPredictor,
        sessions: List[SessionState],
        labels: List[List[TTP]],
    ) -> Dict[str, float]:
        """Evaluate predictor on validation set.

        Args:
            predictor: Trained predictor
            sessions: Validation sessions
            labels: True labels

        Returns:
            Dict of evaluation metrics
        """
        correct = 0
        total = 0

        all_predictions = []
        all_labels = []

        for session, true_ttps in zip(sessions, labels):
            predictions = predictor.predict_sync(session, top_k=5)
            predicted_ttps = {p.ttp for p in predictions}

            # Check if any true TTP was predicted
            for ttp in true_ttps:
                total += 1
                if ttp in predicted_ttps:
                    correct += 1

                all_labels.append(TTP_TO_IDX[ttp])
                all_predictions.append(1 if ttp in predicted_ttps else 0)

        accuracy = correct / max(total, 1)

        # Calculate precision and recall
        tp = sum(1 for p in all_predictions if p == 1)

        precision = tp / max(tp + (total - correct), 1)
        recall = correct / max(total, 1)
        f1 = 2 * precision * recall / max(precision + recall, 1e-6)

        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "total_samples": total,
        }

    def get_training_history(self) -> List[Dict[str, Any]]:
        """Get training history.

        Returns:
            List of training run records
        """
        return self._training_runs

    def get_ttp_distribution(self) -> Dict[TTP, int]:
        """Get distribution of TTPs in training data.

        Returns:
            Dict mapping TTP to count
        """
        distribution: Dict[TTP, int] = {}

        for labels in self._labels:
            for ttp in labels:
                distribution[ttp] = distribution.get(ttp, 0) + 1

        return distribution

    def clear_data(self) -> None:
        """Clear training data buffer."""
        self._sessions.clear()
        self._labels.clear()
        logger.info("Training data cleared")

    def export_dataset(self, path: str) -> None:
        """Export training dataset to file.

        Args:
            path: Path to save dataset
        """
        import json

        data = []
        for session, labels in zip(self._sessions, self._labels):
            data.append(
                {
                    "session_id": session.session_id,
                    "commands": [r.command for r in session.command_history],
                    "ttps": [ttp.value for ttp in labels],
                }
            )

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

        logger.info(f"Dataset exported to {path}")

    def import_dataset(self, path: str) -> int:
        """Import training dataset from file.

        Args:
            path: Path to dataset file

        Returns:
            Number of samples imported
        """
        import json
        from ..emulation.models import CommandRecord

        with open(path) as f:
            data = json.load(f)

        imported = 0
        for item in data:
            session = SessionState(
                session_id=item["session_id"],
                command_history=[
                    CommandRecord(command=cmd, timestamp=datetime.now(timezone.utc))
                    for cmd in item["commands"]
                ],
            )
            ttps = [TTP(v) for v in item["ttps"]]

            self.add_training_sample(session, ttps)
            imported += 1

        logger.info(f"Imported {imported} samples from {path}")
        return imported
