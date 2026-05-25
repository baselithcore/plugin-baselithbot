"""Honeypot Event Definitions.

Defines Honeypot-specific events for cross-agent and cross-plugin
communication using the core EventBus system.
"""

import logging
from core.observability.logging import get_logger
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = get_logger(__name__)
stdlib_logger = logging.getLogger(__name__)


# =============================================================================
# Event Names
# =============================================================================


class HoneypotEvents:
    """Honeypot event name constants."""

    # Attack events
    ATTACK_DETECTED = "honeypot.attack.detected"
    ATTACK_ANALYZED = "honeypot.attack.analyzed"
    ATTACK_HIGH_SEVERITY = "honeypot.attack.high_severity"

    # Session events
    SESSION_STARTED = "honeypot.session.started"
    SESSION_ENDED = "honeypot.session.ended"
    SESSION_SUSPICIOUS = "honeypot.session.suspicious"

    # CVE correlation events
    CVE_CORRELATION_FOUND = "honeypot.cve.correlation_found"
    CVE_CORRELATION_REQUESTED = "honeypot.cve.correlation_requested"

    # Service events
    SERVICE_STARTED = "honeypot.service.started"
    SERVICE_STOPPED = "honeypot.service.stopped"
    SERVICE_ERROR = "honeypot.service.error"

    # Pattern events
    PATTERN_DETECTED = "honeypot.pattern.detected"
    PATTERN_NEW = "honeypot.pattern.new"

    # Learning events
    PATTERN_LEARNED = "honeypot.learning.pattern_learned"
    EXPERIENCE_RECORDED = "honeypot.learning.experience_recorded"
    FEEDBACK_RECEIVED = "honeypot.learning.feedback_received"

    # Cross-plugin events (for CVE Hunter integration)
    REQUEST_CVE_LOOKUP = "honeypot.integration.request_cve_lookup"
    ATTACK_FOR_ANALYSIS = "honeypot.integration.attack_for_analysis"
    CORRELATION_FEEDBACK = "honeypot.integration.correlation_feedback"

    # Pentest events
    PENTEST_STARTED = "honeypot.pentest.started"
    PENTEST_COMPLETED = "honeypot.pentest.completed"
    PLAYBOOK_GENERATED = "honeypot.pentest.playbook_generated"
    VULNERABILITY_FOUND = "honeypot.pentest.vulnerability_found"

    # Notification events
    NOTIFICATION_SENT = "honeypot.notification.sent"
    NOTIFICATION_FAILED = "honeypot.notification.failed"


# =============================================================================
# Event Data Classes
# =============================================================================


@dataclass
class AttackEventData:
    """Data for attack detection events."""

    event_id: str
    session_id: str
    honeypot_id: str
    protocol: str
    source_ip: str
    source_port: int
    category: str
    severity: str
    detected_patterns: List[str]
    raw_data: Optional[str] = None
    command: Optional[str] = None
    http_path: Optional[str] = None
    http_path: Optional[str] = None
    timestamp: Optional[datetime] = None
    geo: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for event emission."""
        return {
            "event_id": self.event_id,
            "session_id": self.session_id,
            "honeypot_id": self.honeypot_id,
            "protocol": self.protocol,
            "source_ip": self.source_ip,
            "source_port": self.source_port,
            "category": self.category,
            "severity": self.severity,
            "detected_patterns": self.detected_patterns,
            "raw_data": self.raw_data,
            "command": self.command,
            "http_path": self.http_path,
            "timestamp": (self.timestamp or datetime.now(timezone.utc)).isoformat(),
            "geo": self.geo or {},
        }


@dataclass
class SessionEventData:
    """Data for session events."""

    session_id: str
    protocol: str
    source_ip: str
    event_count: int = 0
    auth_attempts: int = 0
    auth_success: bool = False
    max_severity: str = "info"
    duration_seconds: Optional[float] = None
    commands: Optional[List[str]] = None
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for event emission."""
        return {
            "session_id": self.session_id,
            "protocol": self.protocol,
            "source_ip": self.source_ip,
            "event_count": self.event_count,
            "auth_attempts": self.auth_attempts,
            "auth_success": self.auth_success,
            "max_severity": self.max_severity,
            "duration_seconds": self.duration_seconds,
            "commands": self.commands or [],
            "timestamp": (self.timestamp or datetime.now(timezone.utc)).isoformat(),
        }


@dataclass
class CVECorrelationEventData:
    """Data for CVE correlation events."""

    correlation_id: str
    event_id: str
    attack_pattern: str
    matched_cves: List[str]
    matched_cwes: List[str]
    confidence: float
    source: str = "honeypot"
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for event emission."""
        return {
            "correlation_id": self.correlation_id,
            "event_id": self.event_id,
            "attack_pattern": self.attack_pattern,
            "matched_cves": self.matched_cves,
            "matched_cwes": self.matched_cwes,
            "confidence": self.confidence,
            "source": self.source,
            "timestamp": (self.timestamp or datetime.now(timezone.utc)).isoformat(),
        }


@dataclass
class ServiceEventData:
    """Data for service lifecycle events."""

    service_name: str
    protocol: str
    port: int
    status: str
    error_message: Optional[str] = None
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for event emission."""
        return {
            "service_name": self.service_name,
            "protocol": self.protocol,
            "port": self.port,
            "status": self.status,
            "error_message": self.error_message,
            "timestamp": (self.timestamp or datetime.now(timezone.utc)).isoformat(),
        }


@dataclass
class PatternEventData:
    """Data for pattern detection events."""

    pattern_id: str
    pattern_type: str
    pattern_value: str
    confidence: float
    source_ip: str
    occurrences: int = 1
    related_events: Optional[List[str]] = None
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for event emission."""
        return {
            "pattern_id": self.pattern_id,
            "pattern_type": self.pattern_type,
            "pattern_value": self.pattern_value,
            "confidence": self.confidence,
            "source_ip": self.source_ip,
            "occurrences": self.occurrences,
            "related_events": self.related_events or [],
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
    context: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for event emission."""
        return {
            "experience_id": self.experience_id,
            "action": self.action,
            "reward": self.reward,
            "success": self.success,
            "pattern_type": self.pattern_type,
            "context": self.context or {},
            "timestamp": (self.timestamp or datetime.now(timezone.utc)).isoformat(),
        }


# =============================================================================
# Event Helper Functions
# =============================================================================


def get_event_bus():
    """Get the global EventBus instance.

    Returns:
        EventBus instance from core/events or None
    """
    try:
        from core.events import get_event_bus as _get_event_bus

        return _get_event_bus()
    except ImportError:
        return None


async def emit_honeypot_event(event_name: str, data: Dict[str, Any]) -> int:
    """Emit a Honeypot event.

    Args:
        event_name: Event name from HoneypotEvents
        data: Event data dict

    Returns:
        Number of handlers invoked
    """
    bus = get_event_bus()
    if bus is None:
        return 0

    return await bus.emit(event_name, data, source="honeypot")


def emit_honeypot_event_sync(event_name: str, data: Dict[str, Any]) -> int:
    """Emit a Honeypot event synchronously.

    Args:
        event_name: Event name from HoneypotEvents
        data: Event data dict

    Returns:
        Number of handlers invoked
    """
    bus = get_event_bus()
    if bus is None:
        return 0

    return bus.emit_sync(event_name, data, source="honeypot")


class HoneypotEventHandler:
    """Handler for subscribing to and handling honeypot events."""

    def __init__(self, event_bus=None):
        """Initialize event handler.

        Args:
            event_bus: Optional EventBus instance
        """
        self._event_bus = event_bus or get_event_bus()
        self._subscriptions = []
        self._cve_cache: Dict[str, Dict[str, Any]] = {}
        self._recent_alerts: List[Dict[str, Any]] = []

    def subscribe(self) -> None:
        """Subscribe to relevant events."""
        if not self._event_bus:
            return

        # =====================================================================
        # Honeypot Events
        # =====================================================================

        # Subscribe to internal honeypot events if needed for global state
        # self._event_bus.on(HoneypotEvents.ATTACK_DETECTED)(self._handle_attack)

        # =====================================================================
        # Cross-Plugin: CVE Hunter Events
        # =====================================================================

        self._event_bus.on("cve_hunter.alert.critical_discovery")(
            self._handle_critical_cve_discovery
        )
        self._event_bus.on("honeypot.attack.analyzed")(self._handle_attack_analyzed)

    async def _handle_attack_analyzed(self, data: Dict[str, Any]) -> None:
        """Handle analysis results from CVE Hunter.

        Args:
            data: Analysis data including analysis_summary, request_id, etc.
        """
        request_id = data.get("request_id")
        analysis = data.get("analysis", {})

        logger.info(f"Received deep analysis result for request {request_id}")

        # Here we could persist the result to the database or update an in-memory cache
        # For now, we logging it and adding it to recent alerts if critical

        if analysis.get("success"):
            # If we had a mechanism to push to frontend via websocket, we would do it here
            pass

    async def _handle_critical_cve_discovery(self, data: Dict[str, Any]) -> None:
        """Handle proactive critical CVE discovery notification.

        When CVE Hunter discovers a critical vulnerability, Honeypot should
        activate defensive rules or enhanced monitoring for related patterns.
        """

        logger = get_logger(__name__)

        cve_id = data.get("cve_id")
        title = data.get("title")
        cwes = data.get("cwe_ids", [])

        message = (
            f"CRITICAL CVE DISCOVERY ALERT: {cve_id} - {title}. "
            f"Activating defensive posture for CWEs: {cwes}"
        )
        logger.warning(message)
        stdlib_logger.warning(message)

        # Add to recent alerts
        self._recent_alerts.append(data)
        if len(self._recent_alerts) > 50:
            self._recent_alerts.pop(0)

        # Future: Dynamically update Captor rules or Sensitivity classification

    def _persist_attack_event(self, data: Dict[str, Any]) -> None:
        """Async callback wrapper to persist attack event."""

        try:
            # Depending on how 'data' is structured, we might need to reconstruction the Model
            # But usually persistence is better done at the source (Coordinator/Detector)
            # However, hooking into the event bus is decoupling.
            # We need to make sure 'data' has everything needed for AttackEvent.
            # Ideally, we pass the generic dict to DAO if it accepts dict, or reconstruct.
            # For now, let's assume we can reconstruct or simple logging.
            # But better: have the Coordinator call DAO directly, OR have this handler decode.
            # Given 'AttackEventData.to_dict()' output, it might miss some fields like 'geo' objects unless flattened.
            pass
        except Exception as e:
            logger.error(f"Failed to persist attack event: {e}")

    def unsubscribe(self) -> None:
        """Unsubscribe from events."""
        # EventBus handles cleanup on shutdown
        pass
