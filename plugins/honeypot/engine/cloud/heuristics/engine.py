"""Heuristic Detection - Engine.

Manages and executes heuristic rules for zero-day detection.
"""

from core.observability.logging import get_logger
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set

from ..models import APICallSeverity, CloudAPICall, CloudSession, HeuristicAlert
from .base import HeuristicRule
from .behavior import (
    AbnormalDataVolumeHeuristic,
    HighErrorRateHeuristic,
    RapidStateTransitionHeuristic,
)
from .payload import EncodedPayloadHeuristic, SuspiciousResourceNameHeuristic
from .sequence import (
    PrivilegeEscalationSequenceHeuristic,
    UnusualServiceCombinationHeuristic,
)
from .timing import BurstRequestHeuristic, MachineTimingHeuristic

logger = get_logger(__name__)


class HeuristicEngine:
    """Manages and executes heuristic rules for zero-day detection."""

    def __init__(self):
        """Initialize with default rule set."""
        self.rules: List[HeuristicRule] = [
            # Timing heuristics
            MachineTimingHeuristic(),
            BurstRequestHeuristic(),
            # Sequence heuristics
            PrivilegeEscalationSequenceHeuristic(),
            UnusualServiceCombinationHeuristic(),
            # Payload heuristics
            EncodedPayloadHeuristic(),
            SuspiciousResourceNameHeuristic(),
            # Behavioral heuristics
            RapidStateTransitionHeuristic(),
            HighErrorRateHeuristic(),
            AbnormalDataVolumeHeuristic(),
        ]
        self._alert_history: Dict[str, List[HeuristicAlert]] = defaultdict(list)
        self._suppressed_alerts: Set[str] = set()

    def add_rule(self, rule: HeuristicRule) -> None:
        """Add a custom heuristic rule."""
        self.rules.append(rule)

    def evaluate_all(
        self,
        session: CloudSession,
        call: Optional[CloudAPICall] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[HeuristicAlert]:
        """Evaluate all heuristic rules.

        Args:
            session: Current session state
            call: Optional current API call
            context: Additional context

        Returns:
            List of triggered alerts
        """
        alerts = []

        for rule in self.rules:
            try:
                alert = rule.evaluate(session, call, context)
                if alert and not self._is_suppressed(alert):
                    alerts.append(alert)
                    self._alert_history[session.session_id].append(alert)
            except Exception as e:
                logger.error(f"Heuristic rule {rule.name} failed: {e}")

        return alerts

    def _is_suppressed(self, alert: HeuristicAlert) -> bool:
        """Check if alert should be suppressed (dedup)."""
        # Create dedup key
        key = f"{alert.session_id}:{alert.heuristic_name}"

        # Don't suppress critical alerts
        if alert.severity == APICallSeverity.CRITICAL:
            return False

        # Check if we've seen this recently
        if key in self._suppressed_alerts:
            return True

        # Add to suppression set (simple implementation)
        self._suppressed_alerts.add(key)
        return False

    def get_session_alerts(self, session_id: str) -> List[HeuristicAlert]:
        """Get all alerts for a session."""
        return self._alert_history.get(session_id, [])

    def get_zero_day_candidates(self) -> List[HeuristicAlert]:
        """Get all alerts flagged as potential zero-day indicators."""
        candidates = []
        for alerts in self._alert_history.values():
            candidates.extend(a for a in alerts if a.is_zero_day_candidate)
        return candidates

    def get_rule_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Get trigger statistics for all rules."""
        return {
            rule.name: {
                "category": rule.category,
                "severity": rule.severity.value,
                "trigger_count": rule.trigger_count,
            }
            for rule in self.rules
        }

    def clear_session(self, session_id: str) -> None:
        """Clear data for ended session."""
        self._alert_history.pop(session_id, None)
        # Clear suppression for this session
        self._suppressed_alerts = {
            k for k in self._suppressed_alerts if not k.startswith(f"{session_id}:")
        }


# Singleton instance
_engine_instance: Optional[HeuristicEngine] = None


def get_heuristic_engine() -> HeuristicEngine:
    """Get singleton heuristic engine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = HeuristicEngine()
    return _engine_instance
