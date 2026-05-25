"""Traffic Classification for Honeypot Plugin.

Implements rule-based traffic classification per HoneyDOC Section IV-C1.
Provides customizable traffic classification with fine-grained actions.

Multiple classification criteria (from paper):
- Signature-based (payload-based)
- Source-destination based (addresses-based)
"""

from core.observability.logging import get_logger
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .data_control import ControlRule, FlowAction

logger = get_logger(__name__)


@dataclass
class ClassificationResult:
    """Result of traffic classification."""

    matched: bool
    action: FlowAction
    matched_rules: List[ControlRule]
    primary_rule: Optional[ControlRule]
    classification_reason: str
    redirect_target: Optional[str] = None  # Honeypot ID for redirects
    classified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class TrafficClassifier:
    """Rule-based traffic classifier per HoneyDOC design.

    Supports:
    - Protocol-based filtering
    - Source/destination based filtering
    - Payload content matching (regex)
    - Priority-ordered rule evaluation
    """

    def __init__(self):
        """Initialize classifier."""
        self._rules: List[ControlRule] = []
        self._rule_stats: Dict[str, int] = {}  # sid -> hit count
        self._default_action = FlowAction.FORWARD

        logger.info("TrafficClassifier initialized")

    def add_rule(self, rule: ControlRule) -> None:
        """Add classification rule.

        Args:
            rule: Rule to add
        """
        if any(r.sid == rule.sid for r in self._rules):
            logger.warning(f"Rule {rule.sid} already exists, skipping")
            return

        self._rules.append(rule)
        self._rule_stats[rule.sid] = 0
        self._sort_rules()
        logger.debug(f"Added classification rule: {rule.sid}")

    def add_rules(self, rules: List[ControlRule]) -> None:
        """Add multiple classification rules.

        Args:
            rules: Rules to add
        """
        for rule in rules:
            self.add_rule(rule)

    def remove_rule(self, sid: str) -> bool:
        """Remove rule by SID.

        Args:
            sid: Rule identifier

        Returns:
            True if removed
        """
        original_len = len(self._rules)
        self._rules = [r for r in self._rules if r.sid != sid]
        if sid in self._rule_stats:
            del self._rule_stats[sid]
        return len(self._rules) < original_len

    def classify(
        self,
        protocol: str,
        src_ip: str,
        dst_port: int,
        payload: Optional[str] = None,
        src_port: Optional[int] = None,
        dst_ip: Optional[str] = None,
    ) -> ClassificationResult:
        """Classify traffic based on rules.

        Args:
            protocol: Protocol (tcp, udp, ssh, http)
            src_ip: Source IP address
            dst_port: Destination port
            payload: Optional payload for content matching
            src_port: Optional source port
            dst_ip: Optional destination IP

        Returns:
            Classification result with action
        """
        matched_rules: List[ControlRule] = []

        for rule in self._rules:
            if not rule.enabled:
                continue

            if self._matches_rule(
                rule, protocol, src_ip, dst_port, payload, src_port, dst_ip
            ):
                matched_rules.append(rule)
                self._rule_stats[rule.sid] = self._rule_stats.get(rule.sid, 0) + 1

        if not matched_rules:
            return ClassificationResult(
                matched=False,
                action=self._default_action,
                matched_rules=[],
                primary_rule=None,
                classification_reason="No matching rules, using default action",
            )

        # Primary rule is highest priority match
        primary_rule = matched_rules[0]

        return ClassificationResult(
            matched=True,
            action=primary_rule.action,
            matched_rules=matched_rules,
            primary_rule=primary_rule,
            classification_reason=f"Matched rule {primary_rule.sid}: {primary_rule.description}",
            redirect_target=getattr(primary_rule, "redirect_target", None),
        )

    def _matches_rule(
        self,
        rule: ControlRule,
        protocol: str,
        src_ip: str,
        dst_port: int,
        payload: Optional[str],
        src_port: Optional[int],
        dst_ip: Optional[str],
    ) -> bool:
        """Check if traffic matches a rule.

        Args:
            rule: Rule to check
            protocol: Traffic protocol
            src_ip: Source IP
            dst_port: Destination port
            payload: Optional payload
            src_port: Optional source port
            dst_ip: Optional destination IP

        Returns:
            True if matches
        """
        # Protocol match
        if rule.protocol != "any":
            if rule.protocol.lower() != protocol.lower():
                return False

        # Source IP match
        if rule.src_ip != "any":
            if not self._ip_matches(src_ip, rule.src_ip):
                return False

        # Destination port match
        if rule.dst_port != "any":
            try:
                rule_port = int(rule.dst_port)
                if rule_port != dst_port:
                    return False
            except ValueError:
                pass  # Skip invalid port specs

        # Source port match (if specified)
        if rule.src_port != "any" and src_port is not None:
            try:
                rule_src_port = int(rule.src_port)
                if rule_src_port != src_port:
                    return False
            except ValueError:
                pass

        # Destination IP match (if specified)
        if rule.dst_ip != "any" and dst_ip is not None:
            if not self._ip_matches(dst_ip, rule.dst_ip):
                return False

        # Content match (if specified)
        if rule.content and payload:
            try:
                if not re.search(rule.content, payload, re.IGNORECASE | re.DOTALL):
                    return False
            except re.error as e:
                logger.warning(f"Invalid regex in rule {rule.sid}: {e}")
                return False

        return True

    def _ip_matches(self, ip: str, pattern: str) -> bool:
        """Check if IP matches pattern (simple matching).

        Args:
            ip: IP address to check
            pattern: Pattern (can be exact IP or simple prefix)

        Returns:
            True if matches
        """
        if pattern == "any":
            return True

        # Exact match
        if ip == pattern:
            return True

        # Simple CIDR matching (basic implementation)
        if "/" in pattern:
            try:
                import ipaddress

                network = ipaddress.ip_network(pattern, strict=False)
                return ipaddress.ip_address(ip) in network
            except (ValueError, ImportError):
                return False

        # Prefix matching
        if pattern.endswith("*"):
            prefix = pattern[:-1]
            return ip.startswith(prefix)

        return False

    def _sort_rules(self) -> None:
        """Sort rules by priority (higher first)."""
        self._rules.sort(key=lambda r: r.priority, reverse=True)

    def load_rules_from_config(self, rules_config: List[Dict[str, Any]]) -> int:
        """Load rules from configuration.

        Args:
            rules_config: List of rule configurations

        Returns:
            Number of rules loaded
        """
        loaded = 0
        for rule_dict in rules_config:
            try:
                rule = ControlRule(
                    sid=rule_dict.get("sid", f"rule_{loaded}"),
                    protocol=rule_dict.get("protocol", "any"),
                    src_ip=rule_dict.get("src_ip", "any"),
                    src_port=str(rule_dict.get("src_port", "any")),
                    dst_ip=rule_dict.get("dst_ip", "any"),
                    dst_port=str(rule_dict.get("dst_port", "any")),
                    action=FlowAction(rule_dict.get("action", "forward")),
                    content=rule_dict.get("content"),
                    priority=rule_dict.get("priority", 0),
                    description=rule_dict.get("description", ""),
                    enabled=rule_dict.get("enabled", True),
                )
                self.add_rule(rule)
                loaded += 1
            except Exception as e:
                logger.warning(f"Failed to load rule: {e}")

        logger.info(f"Loaded {loaded} classification rules from config")
        return loaded

    def get_rules(self) -> List[ControlRule]:
        """Get all rules.

        Returns:
            List of rules
        """
        return self._rules.copy()

    def get_rule_stats(self) -> Dict[str, int]:
        """Get rule hit statistics.

        Returns:
            Dict of sid -> hit count
        """
        return self._rule_stats.copy()

    def set_default_action(self, action: FlowAction) -> None:
        """Set default action for unmatched traffic.

        Args:
            action: Default action
        """
        self._default_action = action

    def clear(self) -> None:
        """Clear all rules."""
        self._rules.clear()
        self._rule_stats.clear()
        logger.info("TrafficClassifier cleared")
