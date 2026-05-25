"""Heuristic Detection - Timing-Based Rules.

Timing-based heuristics for detecting automated attack tools.
"""

from core.observability.logging import get_logger
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from ..models import APICallSeverity, CloudAPICall, CloudSession
from .base import HeuristicRule

logger = get_logger(__name__)


class MachineTimingHeuristic(HeuristicRule):
    """Detects machine-like request timing patterns."""

    # Human typing/clicking rarely produces sub-100ms intervals consistently
    MIN_HUMAN_DELAY_MS = 100
    MAX_VARIANCE_FOR_BOT = 50  # Bots have very consistent timing

    def __init__(self):
        super().__init__(
            name="machine_timing",
            category="timing",
            description="Detects automated tool timing patterns",
            severity=APICallSeverity.MEDIUM,
        )

    def evaluate(
        self,
        session: CloudSession,
        call: Optional[CloudAPICall] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[HeuristicRule]:
        if not call or not call.request_timing:
            return None

        timing = call.request_timing

        # Check for sub-human timing
        if timing.min_inter_request_delay_ms is not None:
            if timing.min_inter_request_delay_ms < self.MIN_HUMAN_DELAY_MS:
                # At least some requests are faster than human capability
                if timing.request_timing_variance is not None:
                    if timing.request_timing_variance < self.MAX_VARIANCE_FOR_BOT:
                        # Very consistent timing = likely bot
                        return self.create_alert(
                            session=session,
                            trigger_reason="Consistent sub-human request timing detected",
                            evidence={
                                "min_delay_ms": timing.min_inter_request_delay_ms,
                                "avg_delay_ms": timing.avg_inter_request_delay_ms,
                                "variance": timing.request_timing_variance,
                            },
                            related_calls=[call.call_id],
                            baseline=f">={self.MIN_HUMAN_DELAY_MS}ms with variance",
                            observed=f"{timing.min_inter_request_delay_ms}ms, var={timing.request_timing_variance}",
                            deviation=0.7,
                        )

        return None


class BurstRequestHeuristic(HeuristicRule):
    """Detects sudden bursts of API requests."""

    BURST_WINDOW_SECONDS = 5
    BURST_THRESHOLD = 20  # requests per window

    def __init__(self):
        super().__init__(
            name="burst_requests",
            category="timing",
            description="Detects sudden request bursts indicating automated scanning",
            severity=APICallSeverity.HIGH,
        )
        self._request_windows: Dict[str, List[datetime]] = defaultdict(list)

    def evaluate(
        self,
        session: CloudSession,
        call: Optional[CloudAPICall] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[HeuristicRule]:
        if not call:
            return None

        now = call.timestamp
        session_id = session.session_id

        # Add current request to window
        self._request_windows[session_id].append(now)

        # Clean old entries
        cutoff = now - timedelta(seconds=self.BURST_WINDOW_SECONDS)
        self._request_windows[session_id] = [
            t for t in self._request_windows[session_id] if t > cutoff
        ]

        count = len(self._request_windows[session_id])

        if count >= self.BURST_THRESHOLD:
            return self.create_alert(
                session=session,
                trigger_reason=f"{count} requests in {self.BURST_WINDOW_SECONDS}s window",
                evidence={
                    "request_count": count,
                    "window_seconds": self.BURST_WINDOW_SECONDS,
                    "threshold": self.BURST_THRESHOLD,
                },
                related_calls=[call.call_id],
                baseline=f"<{self.BURST_THRESHOLD} requests/{self.BURST_WINDOW_SECONDS}s",
                observed=f"{count} requests/{self.BURST_WINDOW_SECONDS}s",
                deviation=min(1.0, count / (self.BURST_THRESHOLD * 2)),
            )

        return None
