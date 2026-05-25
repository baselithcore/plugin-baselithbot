"""Heuristic Detection - Behavioral Rules.

Behavioral heuristics for detecting anomalous patterns.
"""

from core.observability.logging import get_logger
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional

from ..models import APICallSeverity, CloudAPICall, CloudSession
from .base import HeuristicRule

logger = get_logger(__name__)


class RapidStateTransitionHeuristic(HeuristicRule):
    """Detects unusually rapid state transitions (automated attack tools)."""

    MAX_TRANSITIONS_PER_MINUTE = 10

    def __init__(self):
        super().__init__(
            name="rapid_state_transitions",
            category="behavior",
            description="Detects rapid state machine transitions",
            severity=APICallSeverity.HIGH,
        )
        self._transition_times: Dict[str, List[datetime]] = defaultdict(list)

    def evaluate(
        self,
        session: CloudSession,
        call: Optional[CloudAPICall] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[HeuristicRule]:
        if session.state_transition_count < 3:
            return None

        # Calculate transition rate from history
        if len(session.state_history) < 2:
            return None

        try:
            first_transition = datetime.fromisoformat(
                session.state_history[0]["timestamp"]
            )
            last_transition = datetime.fromisoformat(
                session.state_history[-1]["timestamp"]
            )
            duration = (last_transition - first_transition).total_seconds()

            if duration > 0:
                transitions_per_minute = (
                    session.state_transition_count / duration
                ) * 60

                if transitions_per_minute > self.MAX_TRANSITIONS_PER_MINUTE:
                    return self.create_alert(
                        session=session,
                        trigger_reason=f"Rapid state transitions: {transitions_per_minute:.1f}/min",
                        evidence={
                            "transitions": session.state_transition_count,
                            "duration_seconds": duration,
                            "rate_per_minute": transitions_per_minute,
                        },
                        baseline=f"<{self.MAX_TRANSITIONS_PER_MINUTE} transitions/min",
                        observed=f"{transitions_per_minute:.1f} transitions/min",
                        deviation=min(
                            1.0,
                            transitions_per_minute
                            / (self.MAX_TRANSITIONS_PER_MINUTE * 2),
                        ),
                    )
        except (KeyError, ValueError, TypeError):
            pass

        return None


class HighErrorRateHeuristic(HeuristicRule):
    """Detects high error rate indicating fuzzing or brute force."""

    ERROR_THRESHOLD_PERCENT = 70
    MIN_REQUESTS = 10

    def __init__(self):
        super().__init__(
            name="high_error_rate",
            category="behavior",
            description="Detects high API error rate indicating fuzzing",
            severity=APICallSeverity.MEDIUM,
        )

    def evaluate(
        self,
        session: CloudSession,
        call: Optional[CloudAPICall] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[HeuristicRule]:
        total = session.error_count + session.success_count

        if total < self.MIN_REQUESTS:
            return None

        error_rate = (session.error_count / total) * 100

        if error_rate >= self.ERROR_THRESHOLD_PERCENT:
            return self.create_alert(
                session=session,
                trigger_reason=f"High error rate: {error_rate:.1f}%",
                evidence={
                    "error_count": session.error_count,
                    "success_count": session.success_count,
                    "total_requests": total,
                    "error_rate_percent": error_rate,
                },
                baseline=f"<{self.ERROR_THRESHOLD_PERCENT}% error rate",
                observed=f"{error_rate:.1f}% error rate",
                deviation=min(1.0, error_rate / 100),
            )

        return None


class AbnormalDataVolumeHeuristic(HeuristicRule):
    """Detects abnormal data volume requests (potential exfiltration)."""

    DATA_THRESHOLD_MB = 100

    def __init__(self):
        super().__init__(
            name="abnormal_data_volume",
            category="behavior",
            description="Detects abnormally large data requests",
            severity=APICallSeverity.CRITICAL,
        )

    def evaluate(
        self,
        session: CloudSession,
        call: Optional[CloudAPICall] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[HeuristicRule]:
        volume_mb = session.data_volume_requested_bytes / (1024 * 1024)

        if volume_mb >= self.DATA_THRESHOLD_MB:
            return self.create_alert(
                session=session,
                trigger_reason=f"Large data volume requested: {volume_mb:.1f} MB",
                evidence={
                    "volume_bytes": session.data_volume_requested_bytes,
                    "volume_mb": volume_mb,
                },
                baseline=f"<{self.DATA_THRESHOLD_MB} MB",
                observed=f"{volume_mb:.1f} MB",
                deviation=min(1.0, volume_mb / (self.DATA_THRESHOLD_MB * 2)),
            )

        return None
