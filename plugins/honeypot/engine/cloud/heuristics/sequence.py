"""Heuristic Detection - Sequence-Based Rules.

Sequence-based heuristics for detecting attack patterns.
"""

from core.observability.logging import get_logger
from collections import defaultdict
from typing import Any, Dict, List, Optional

from ..models import APICallSeverity, CloudAPICall, CloudSession
from .base import HeuristicRule

logger = get_logger(__name__)


class PrivilegeEscalationSequenceHeuristic(HeuristicRule):
    """Detects privilege escalation attack sequences."""

    # Common privesc sequences
    ESCALATION_SEQUENCES = [
        # Classic IAM privesc
        ["GetUser", "ListAttachedUserPolicies", "AttachUserPolicy"],
        ["GetCallerIdentity", "ListRoles", "AssumeRole"],
        ["GetUser", "CreateAccessKey"],
        # Role assumption chain
        ["ListRoles", "GetRole", "AssumeRole", "GetCallerIdentity"],
        # Policy manipulation
        ["GetPolicy", "CreatePolicyVersion", "SetDefaultPolicyVersion"],
        # Backdoor creation
        ["CreateUser", "AttachUserPolicy", "CreateAccessKey"],
    ]

    def __init__(self):
        super().__init__(
            name="privesc_sequence",
            category="sequence",
            description="Detects known privilege escalation action sequences",
            severity=APICallSeverity.CRITICAL,
        )
        self._action_history: Dict[str, List[str]] = defaultdict(list)

    def evaluate(
        self,
        session: CloudSession,
        call: Optional[CloudAPICall] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[HeuristicRule]:
        if not call:
            return None

        session_id = session.session_id
        action = call.action

        # Add action to history
        self._action_history[session_id].append(action)

        # Keep only recent history
        if len(self._action_history[session_id]) > 20:
            self._action_history[session_id] = self._action_history[session_id][-20:]

        history = self._action_history[session_id]

        # Check for matching sequences
        for sequence in self.ESCALATION_SEQUENCES:
            if self._is_subsequence(sequence, history):
                return self.create_alert(
                    session=session,
                    trigger_reason=f"Privilege escalation sequence detected: {' -> '.join(sequence)}",
                    evidence={
                        "matched_sequence": sequence,
                        "recent_actions": history[-10:],
                    },
                    related_calls=[call.call_id],
                    baseline="Normal API usage patterns",
                    observed=" -> ".join(sequence),
                    deviation=0.9,
                )

        return None

    def _is_subsequence(self, pattern: List[str], history: List[str]) -> bool:
        """Check if pattern appears as subsequence in history."""
        if len(pattern) > len(history):
            return False

        pattern_idx = 0
        for action in history:
            if action == pattern[pattern_idx]:
                pattern_idx += 1
                if pattern_idx == len(pattern):
                    return True
        return False


class UnusualServiceCombinationHeuristic(HeuristicRule):
    """Detects unusual combinations of service access."""

    # Unusual service combinations that might indicate attack
    SUSPICIOUS_COMBINATIONS = [
        {"iam", "s3", "kms"},  # Data exfiltration setup
        {"iam", "lambda", "secretsmanager"},  # Backdoor setup
        {"sts", "iam", "cloudtrail"},  # Defense evasion
        {"ec2", "ssm", "iam"},  # Lateral movement
    ]

    def __init__(self):
        super().__init__(
            name="unusual_service_combo",
            category="sequence",
            description="Detects unusual combinations of service access",
            severity=APICallSeverity.HIGH,
        )

    def evaluate(
        self,
        session: CloudSession,
        call: Optional[CloudAPICall] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[HeuristicRule]:
        services = session.services_accessed

        if len(services) < 3:
            return None

        for suspicious_combo in self.SUSPICIOUS_COMBINATIONS:
            if suspicious_combo.issubset(services):
                return self.create_alert(
                    session=session,
                    trigger_reason=f"Suspicious service combination: {suspicious_combo}",
                    evidence={
                        "matched_combination": list(suspicious_combo),
                        "all_services": list(services),
                    },
                    baseline="Single-service or benign multi-service access",
                    observed=", ".join(suspicious_combo),
                    deviation=0.75,
                )

        return None
