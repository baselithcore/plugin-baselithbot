"""Feedback mixin for HoneypotCVECorrelator."""

from datetime import datetime, timezone
from typing import Any, Dict

from core.observability.logging import get_logger

from ...events import HoneypotEvents, emit_honeypot_event

logger = get_logger(__name__)


class FeedbackMixin:
    """Mixin providing feedback and accuracy tracking for the correlator."""

    async def record_feedback(
        self,
        correlation_id: str,
        outcome: str,
        source: str = "user",
    ) -> bool:
        """Record feedback for a correlation.

        Args:
            correlation_id: ID of the correlation
            outcome: Feedback outcome (confirmed, rejected, false_positive)
            source: Source of feedback (user, automated)

        Returns:
            True if feedback was recorded
        """
        # Find the correlation
        correlation = next(
            (c for c in self._correlations if c["correlation_id"] == correlation_id),
            None,
        )

        if not correlation:
            logger.warning(f"Correlation not found: {correlation_id}")
            return False

        # Store feedback
        self._feedback[correlation_id] = {
            "outcome": outcome,
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "correlation": correlation,
        }

        # Update accuracy metrics
        self._accuracy_metrics["total_feedback"] += 1
        if outcome in self._accuracy_metrics:
            self._accuracy_metrics[outcome] += 1

        # Emit feedback event for CVE Hunter to learn from
        await emit_honeypot_event(
            HoneypotEvents.CORRELATION_FEEDBACK,
            {
                "correlation_id": correlation_id,
                "outcome": outcome,
                "source": source,
                "matched_cves": correlation.get("matched_cves", []),
                "matched_cwes": correlation.get("matched_cwes", []),
                "category": correlation.get("category"),
                "confidence": correlation.get("confidence", 0),
            },
        )

        logger.info(f"Recorded feedback for correlation {correlation_id}: {outcome}")
        return True

    def get_accuracy_stats(self) -> Dict[str, Any]:
        """Get accuracy statistics from feedback.

        Returns:
            Dict with accuracy metrics and rates
        """
        total = self._accuracy_metrics["total_feedback"]
        if total == 0:
            accuracy_rate = 0.0
        else:
            confirmed = self._accuracy_metrics["confirmed"]
            accuracy_rate = confirmed / total

        return {
            **self._accuracy_metrics,
            "accuracy_rate": accuracy_rate,
            "recent_feedback": list(self._feedback.values())[-10:],
        }
