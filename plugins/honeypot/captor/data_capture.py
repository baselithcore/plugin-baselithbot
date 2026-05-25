"""Data Capture Manager for Honeypot Plugin.

Implements unified data capture per HoneyDOC Section III-B1.
Aggregates network traffic, system activity, and firewall logs.

Three critical layers of Data Capture (from paper):
1. Firewall logs (inbound/outbound connections)
2. Network traffic (every packet and payload)
3. System activity (attacker keystroke, system call, modified files)
"""

from core.observability.logging import get_logger
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from ..models import AttackEvent

logger = get_logger(__name__)


@dataclass
class CaptureStats:
    """Statistics for data capture operations."""

    total_network_events: int = 0
    total_system_activities: int = 0
    total_firewall_logs: int = 0
    events_per_honeypot: Dict[str, int] = field(default_factory=dict)
    last_capture_time: Optional[datetime] = None


class DataCaptureManager:
    """Unified data capture manager following HoneyDOC Captor design.

    Aggregates capture from multiple sources:
    - Network events from protocol handlers
    - System activity from HIH monitoring
    - Firewall logs for connection tracking
    """

    def __init__(self, max_events: int = 10000):
        """Initialize capture manager.

        Args:
            max_events: Maximum events to retain in memory
        """
        self._max_events = max_events
        self._network_events: List[AttackEvent] = []
        self._system_activities: List[Dict[str, Any]] = []
        self._firewall_logs: List[Dict[str, Any]] = []
        self._stats = CaptureStats()
        self._event_callbacks: List[Callable[[AttackEvent], None]] = []

        logger.info("DataCaptureManager initialized")

    def capture_network_event(self, event: AttackEvent) -> None:
        """Capture network-level attack event.

        Args:
            event: Attack event from protocol handler
        """
        self._network_events.append(event)
        self._stats.total_network_events += 1
        self._stats.last_capture_time = datetime.now(timezone.utc)

        # Track per-honeypot stats
        honeypot_id = event.honeypot_id
        self._stats.events_per_honeypot[honeypot_id] = (
            self._stats.events_per_honeypot.get(honeypot_id, 0) + 1
        )

        # Enforce memory limit
        if len(self._network_events) > self._max_events:
            self._network_events = self._network_events[-self._max_events :]

        # Notify callbacks
        for callback in self._event_callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error(f"Capture callback error: {e}")

        logger.debug(f"Captured network event: {event.event_id}")

    def capture_system_activity(self, activity: Dict[str, Any]) -> None:
        """Capture system-level activity from HIH.

        Per HoneyDOC: attacker keystroke, system call, modified files.

        Args:
            activity: System activity data
        """
        activity["captured_at"] = datetime.now(timezone.utc).isoformat()
        self._system_activities.append(activity)
        self._stats.total_system_activities += 1

        # Enforce memory limit
        if len(self._system_activities) > self._max_events:
            self._system_activities = self._system_activities[-self._max_events :]

        logger.debug(f"Captured system activity: {activity.get('type', 'unknown')}")

    def capture_firewall_log(self, log_entry: Dict[str, Any]) -> None:
        """Capture firewall log entry.

        Per HoneyDOC: inbound and outbound connections.

        Args:
            log_entry: Firewall log data
        """
        log_entry["captured_at"] = datetime.now(timezone.utc).isoformat()
        self._firewall_logs.append(log_entry)
        self._stats.total_firewall_logs += 1

        # Enforce memory limit
        if len(self._firewall_logs) > self._max_events:
            self._firewall_logs = self._firewall_logs[-self._max_events :]

    def register_callback(self, callback: Callable[[AttackEvent], None]) -> None:
        """Register callback for new network events.

        Args:
            callback: Function to call with each new event
        """
        self._event_callbacks.append(callback)

    def get_network_events(
        self,
        limit: int = 100,
        honeypot_id: Optional[str] = None,
    ) -> List[AttackEvent]:
        """Get recent network events.

        Args:
            limit: Maximum events to return
            honeypot_id: Optional filter by honeypot

        Returns:
            List of recent events
        """
        events = self._network_events
        if honeypot_id:
            events = [e for e in events if e.honeypot_id == honeypot_id]
        return list(reversed(events[-limit:]))

    def get_system_activities(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent system activities.

        Args:
            limit: Maximum activities to return

        Returns:
            List of recent system activities
        """
        return list(reversed(self._system_activities[-limit:]))

    def get_firewall_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent firewall logs.

        Args:
            limit: Maximum logs to return

        Returns:
            List of recent firewall logs
        """
        return list(reversed(self._firewall_logs[-limit:]))

    def get_capture_stats(self) -> CaptureStats:
        """Get capture statistics.

        Returns:
            Current capture statistics
        """
        return self._stats

    def clear(self) -> None:
        """Clear all captured data."""
        self._network_events.clear()
        self._system_activities.clear()
        self._firewall_logs.clear()
        self._stats = CaptureStats()
        logger.info("DataCaptureManager cleared")
