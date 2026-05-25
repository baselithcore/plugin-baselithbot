"""Data Control Manager for Honeypot Plugin.

Implements flow control per HoneyDOC Section III-B2.
Handles inbound/outbound attack flow according to honeypot's intention.

Data Control functions (from paper):
- Discard uninteresting data
- Forward interesting data
- Redirect most interesting data to dedicated decoy
- Contain outbound traffic from compromised HIH
"""

from core.observability.logging import get_logger
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional, Set

from ..models import AttackEvent

logger = get_logger(__name__)


class FlowAction(str, Enum):
    """Actions for traffic flow control per HoneyDOC."""

    DROP = "drop"  # Discard the traffic
    FORWARD = "forward"  # Forward to current honeypot
    REDIRECT = "redirect"  # Redirect to HIH for deep analysis
    CONTAIN = "contain"  # Limit outbound (for HIH containment)


@dataclass
class ControlRule:
    """Traffic control rule inspired by Snort format.

    Per HoneyDOC Section V-A:
    alert protocol source-ip source-port → destination-ip destination-port
    (msg: "alert message"; sid: an integer; priority: an integer;
     content: "malicious pattern";)
    """

    sid: str  # Unique rule identifier
    protocol: str  # tcp, udp, any
    src_ip: str = "any"  # Source IP/CIDR
    src_port: str = "any"  # Source port
    dst_ip: str = "any"  # Destination IP/CIDR
    dst_port: str = "any"  # Destination port
    action: FlowAction = FlowAction.FORWARD
    content: Optional[str] = None  # Payload pattern (regex)
    priority: int = 0  # Higher = more priority
    description: str = ""
    enabled: bool = True


@dataclass
class FlowDecision:
    """Result of flow control evaluation."""

    action: FlowAction
    matched_rule: Optional[ControlRule] = None
    redirect_target: Optional[str] = None  # Honeypot ID for redirects
    reason: str = ""
    evaluated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class DataControlManager:
    """Flow control manager following HoneyDOC Captor design.

    Implements decision engine for traffic handling:
    - Rule-based classification
    - Drop/Forward/Redirect actions
    - Outbound containment for HIH
    """

    def __init__(self):
        """Initialize control manager."""
        self._rules: List[ControlRule] = []
        self._blocked_ips: Set[str] = set()
        self._contained_sessions: Set[str] = set()
        self._default_action = FlowAction.FORWARD

        # Track actions taken
        self._action_log: List[FlowDecision] = []

        logger.info("DataControlManager initialized")

    def add_rule(self, rule: ControlRule) -> None:
        """Add a control rule.

        Args:
            rule: Control rule to add
        """
        self._rules.append(rule)
        # Sort by priority (higher first)
        self._rules.sort(key=lambda r: r.priority, reverse=True)
        logger.debug(f"Added control rule: {rule.sid}")

    def remove_rule(self, sid: str) -> bool:
        """Remove a control rule by SID.

        Args:
            sid: Rule identifier

        Returns:
            True if rule was removed
        """
        original_len = len(self._rules)
        self._rules = [r for r in self._rules if r.sid != sid]
        return len(self._rules) < original_len

    def evaluate_flow(
        self,
        event: AttackEvent,
        payload: Optional[str] = None,
    ) -> FlowDecision:
        """Evaluate flow action for an event.

        Args:
            event: Attack event to evaluate
            payload: Optional payload for content matching

        Returns:
            Flow decision with action and reasoning
        """
        import re

        # Check blocked IPs first
        if event.source_ip in self._blocked_ips:
            decision = FlowDecision(
                action=FlowAction.DROP,
                reason=f"IP {event.source_ip} is blocked",
            )
            self._action_log.append(decision)
            return decision

        # Check contained sessions
        if event.session_id in self._contained_sessions:
            decision = FlowDecision(
                action=FlowAction.CONTAIN,
                reason=f"Session {event.session_id} is contained",
            )
            self._action_log.append(decision)
            return decision

        # Evaluate rules in priority order
        for rule in self._rules:
            if not rule.enabled:
                continue

            # Protocol match
            if rule.protocol != "any" and rule.protocol != event.protocol.value:
                continue

            # Content match (if specified)
            if rule.content and payload:
                try:
                    if not re.search(rule.content, payload, re.IGNORECASE):
                        continue
                except re.error:
                    logger.warning(f"Invalid regex in rule {rule.sid}")
                    continue

            # Rule matched
            decision = FlowDecision(
                action=rule.action,
                matched_rule=rule,
                reason=f"Matched rule {rule.sid}: {rule.description}",
            )
            self._action_log.append(decision)
            logger.debug(
                f"Flow decision: {rule.action.value} for event {event.event_id}"
            )
            return decision

        # Default action
        decision = FlowDecision(
            action=self._default_action,
            reason="No matching rule, using default action",
        )
        self._action_log.append(decision)
        return decision

    def block_ip(self, ip: str, reason: str = "") -> None:
        """Block an IP address.

        Args:
            ip: IP address to block
            reason: Reason for blocking
        """
        self._blocked_ips.add(ip)
        logger.info(f"Blocked IP {ip}: {reason}")

    def unblock_ip(self, ip: str) -> bool:
        """Unblock an IP address.

        Args:
            ip: IP address to unblock

        Returns:
            True if IP was unblocked
        """
        if ip in self._blocked_ips:
            self._blocked_ips.discard(ip)
            logger.info(f"Unblocked IP {ip}")
            return True
        return False

    def contain_session(self, session_id: str, reason: str = "") -> None:
        """Apply containment to a session (limit outbound).

        Per HoneyDOC: mitigate risk that adversary uses compromised
        honeypot to attack other non-Honeypot systems.

        Args:
            session_id: Session to contain
            reason: Reason for containment
        """
        self._contained_sessions.add(session_id)
        logger.info(f"Contained session {session_id}: {reason}")

    def release_session(self, session_id: str) -> bool:
        """Release containment on a session.

        Args:
            session_id: Session to release

        Returns:
            True if session was released
        """
        if session_id in self._contained_sessions:
            self._contained_sessions.discard(session_id)
            logger.info(f"Released session {session_id}")
            return True
        return False

    def get_rules(self) -> List[ControlRule]:
        """Get all control rules.

        Returns:
            List of control rules
        """
        return self._rules.copy()

    def get_blocked_ips(self) -> Set[str]:
        """Get blocked IP addresses.

        Returns:
            Set of blocked IPs
        """
        return self._blocked_ips.copy()

    def get_action_log(self, limit: int = 100) -> List[FlowDecision]:
        """Get recent action decisions.

        Args:
            limit: Maximum entries to return

        Returns:
            List of recent decisions
        """
        return list(reversed(self._action_log[-limit:]))

    def set_default_action(self, action: FlowAction) -> None:
        """Set default action for unmatched traffic.

        Args:
            action: Default action
        """
        self._default_action = action
        logger.info(f"Default action set to: {action.value}")

    def clear(self) -> None:
        """Clear all rules and state."""
        self._rules.clear()
        self._blocked_ips.clear()
        self._contained_sessions.clear()
        self._action_log.clear()
        logger.info("DataControlManager cleared")
