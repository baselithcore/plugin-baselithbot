"""Heuristic Detection - Base Classes.

Base classes for heuristic rule definition.
"""

import hashlib
from core.observability.logging import get_logger
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from ..models import APICallSeverity, CloudAPICall, CloudSession, HeuristicAlert

logger = get_logger(__name__)


class HeuristicRule:
    """Base class for heuristic detection rules."""

    def __init__(
        self,
        name: str,
        category: str,
        description: str,
        severity: APICallSeverity = APICallSeverity.MEDIUM,
    ):
        self.name = name
        self.category = category
        self.description = description
        self.severity = severity
        self.trigger_count = 0

    def evaluate(
        self,
        session: CloudSession,
        call: Optional[CloudAPICall] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[HeuristicAlert]:
        """Evaluate the heuristic rule.

        Override in subclasses.

        Returns:
            HeuristicAlert if triggered, None otherwise
        """
        raise NotImplementedError

    def create_alert(
        self,
        session: CloudSession,
        trigger_reason: str,
        evidence: Dict[str, Any],
        related_calls: Optional[List[str]] = None,
        baseline: Any = None,
        observed: Any = None,
        deviation: float = 0.0,
    ) -> HeuristicAlert:
        """Create a heuristic alert."""
        self.trigger_count += 1
        return HeuristicAlert(
            alert_id=f"heur-{hashlib.md5(f'{session.session_id}-{self.name}-{datetime.now(timezone.utc).timestamp()}'.encode(), usedforsecurity=False).hexdigest()[:12]}",
            session_id=session.session_id,
            heuristic_name=self.name,
            heuristic_category=self.category,
            severity=self.severity,
            trigger_reason=trigger_reason,
            evidence=evidence,
            related_api_calls=related_calls or [],
            baseline_value=baseline,
            observed_value=observed,
            deviation_score=deviation,
            is_zero_day_candidate=deviation > 0.8
            or self.severity == APICallSeverity.CRITICAL,
        )
