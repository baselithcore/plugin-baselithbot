"""CVE Hunter Event Definitions.

Defines CVE Hunter-specific events for cross-agent communication
using the core EventBus system.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# =============================================================================
# Event Names
# =============================================================================


class CVEHunterEvents:
    """CVE Hunter event name constants."""

    # Scanning events
    SCAN_STARTED = "cve_hunter.scan.started"
    SCAN_COMPLETED = "cve_hunter.scan.completed"
    CVE_SCANNED = "cve_hunter.cve.scanned"

    # Analysis events
    ANALYSIS_STARTED = "cve_hunter.analysis.started"
    ANALYSIS_COMPLETED = "cve_hunter.analysis.completed"
    CVE_ANALYZED = "cve_hunter.cve.analyzed"

    # Discovery events
    DISCOVERY_STARTED = "cve_hunter.discovery.started"
    DISCOVERY_POTENTIAL = "cve_hunter.discovery.potential"
    DISCOVERY_CONFIRMED = "cve_hunter.discovery.confirmed"
    DISCOVERY_FALSE_POSITIVE = "cve_hunter.discovery.false_positive"

    # Alert events
    ALERT_CREATED = "cve_hunter.alert.created"
    ALERT_ACKNOWLEDGED = "cve_hunter.alert.acknowledged"
    CRITICAL_DISCOVERY = "cve_hunter.alert.critical_discovery"
    # Swarm coordination events
    AGENT_TASK_ASSIGNED = "cve_hunter.swarm.task_assigned"
    AGENT_HELP_REQUESTED = "cve_hunter.swarm.help_requested"
    TEAM_FORMED = "cve_hunter.swarm.team_formed"

    # Learning events
    EXPERIENCE_RECORDED = "cve_hunter.learning.experience_recorded"
    PATTERN_LEARNED = "cve_hunter.learning.pattern_learned"


# =============================================================================
# Event Data Classes
# =============================================================================


@dataclass
class ScanEventData:
    """Data for scan events."""

    scan_id: str
    source: str
    cves_found: int = 0
    new_cves: int = 0
    duration_seconds: float = 0.0
    errors: List[str] | None = None
    timestamp: datetime | None = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for event emission."""
        return {
            "scan_id": self.scan_id,
            "source": self.source,
            "cves_found": self.cves_found,
            "new_cves": self.new_cves,
            "duration_seconds": self.duration_seconds,
            "errors": self.errors or [],
            "timestamp": (self.timestamp or datetime.now(timezone.utc)).isoformat(),
        }


@dataclass
class CVEEventData:
    """Data for CVE-specific events."""

    cve_id: str
    severity: str
    cvss_score: float
    source: str
    title: Optional[str] = None
    is_new: bool = False
    has_exploit: bool = False
    timestamp: datetime | None = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for event emission."""
        return {
            "cve_id": self.cve_id,
            "severity": self.severity,
            "cvss_score": self.cvss_score,
            "source": self.source,
            "title": self.title,
            "is_new": self.is_new,
            "has_exploit": self.has_exploit,
            "timestamp": (self.timestamp or datetime.now(timezone.utc)).isoformat(),
        }


@dataclass
class DiscoveryEventData:
    """Data for discovery events."""

    discovery_id: str
    pattern: str
    confidence: float
    source: str
    finding_type: str = "potential"
    context: Optional[str] = None
    related_cves: List[str] | None = None
    timestamp: datetime | None = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for event emission."""
        return {
            "discovery_id": self.discovery_id,
            "pattern": self.pattern,
            "confidence": self.confidence,
            "source": self.source,
            "finding_type": self.finding_type,
            "context": self.context,
            "related_cves": self.related_cves or [],
            "timestamp": (self.timestamp or datetime.now(timezone.utc)).isoformat(),
        }


@dataclass
class AlertEventData:
    """Data for alert events."""

    alert_id: str
    cve_id: str
    alert_type: str
    priority: int
    severity: str
    acknowledged: bool = False
    acknowledged_by: Optional[str] = None
    timestamp: datetime | None = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for event emission."""
        return {
            "alert_id": self.alert_id,
            "cve_id": self.cve_id,
            "alert_type": self.alert_type,
            "priority": self.priority,
            "severity": self.severity,
            "acknowledged": self.acknowledged,
            "acknowledged_by": self.acknowledged_by,
            "timestamp": (self.timestamp or datetime.now(timezone.utc)).isoformat(),
        }


@dataclass
class SwarmEventData:
    """Data for swarm coordination events."""

    agent_id: str
    task_id: str
    event_type: str
    capabilities: List[str] | None = None
    team_id: Optional[str] = None
    timestamp: datetime | None = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for event emission."""
        return {
            "agent_id": self.agent_id,
            "task_id": self.task_id,
            "event_type": self.event_type,
            "capabilities": self.capabilities or [],
            "team_id": self.team_id,
            "timestamp": (self.timestamp or datetime.now(timezone.utc)).isoformat(),
        }


@dataclass
class LearningEventData:
    """Data for learning events."""

    experience_id: str
    action: str
    reward: float
    success: bool
    pattern_type: Optional[str] = None
    timestamp: datetime | None = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for event emission."""
        return {
            "experience_id": self.experience_id,
            "action": self.action,
            "reward": self.reward,
            "success": self.success,
            "pattern_type": self.pattern_type,
            "timestamp": (self.timestamp or datetime.now(timezone.utc)).isoformat(),
        }


# =============================================================================
# Event Helper Functions
# =============================================================================


def get_event_bus():
    """Get the global EventBus instance.

    Returns:
        EventBus instance from core/events
    """
    try:
        from core.events import get_event_bus as _get_event_bus

        return _get_event_bus()
    except ImportError:
        return None


async def emit_cve_event(event_name: str, data: Dict[str, Any]) -> int:
    """Emit a CVE Hunter event.

    Args:
        event_name: Event name from CVEHunterEvents
        data: Event data dict

    Returns:
        Number of handlers invoked
    """
    bus = get_event_bus()
    if bus is None:
        return 0

    return await bus.emit(event_name, data, source="cve_hunter")


def emit_cve_event_sync(event_name: str, data: Dict[str, Any]) -> int:
    """Emit a CVE Hunter event synchronously.

    Args:
        event_name: Event name from CVEHunterEvents
        data: Event data dict

    Returns:
        Number of handlers invoked
    """
    bus = get_event_bus()
    if bus is None:
        return 0

    return bus.emit_sync(event_name, data, source="cve_hunter")
