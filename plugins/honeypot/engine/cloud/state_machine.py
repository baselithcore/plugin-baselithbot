"""Cloud Management Honeypot - State Machine.

Finite state machine for tracking attacker session progression
through the cloud API simulation. Implements behavioral analysis
and adaptive responses based on state transitions.
"""

from core.observability.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .models import (
    APICallSeverity,
    CloudAttackCategory,
    CloudSession,
    SessionState,
)

logger = get_logger(__name__)


# State transition rules: (current_state, trigger) -> next_state
STATE_TRANSITIONS: Dict[Tuple[SessionState, str], SessionState] = {
    # Discovery phase
    (SessionState.DISCOVERY, "probe_endpoint"): SessionState.DISCOVERY,
    (SessionState.DISCOVERY, "auth_attempt"): SessionState.PRE_AUTH,
    (SessionState.DISCOVERY, "rate_limit"): SessionState.BLOCKED,
    # Pre-authentication
    (SessionState.PRE_AUTH, "auth_success"): SessionState.AUTHENTICATED,
    (SessionState.PRE_AUTH, "auth_failure"): SessionState.PRE_AUTH,
    (SessionState.PRE_AUTH, "max_auth_exceeded"): SessionState.BLOCKED,
    (SessionState.PRE_AUTH, "mfa_challenge"): SessionState.PRE_AUTH,
    # Authenticated
    (SessionState.AUTHENTICATED, "list_resources"): SessionState.EXPLORING,
    (SessionState.AUTHENTICATED, "read_resource"): SessionState.EXPLORING,
    (SessionState.AUTHENTICATED, "iam_action"): SessionState.PRIVILEGE_ESCALATION,
    (SessionState.AUTHENTICATED, "logout"): SessionState.EXPIRED,
    (SessionState.AUTHENTICATED, "session_timeout"): SessionState.EXPIRED,
    # Exploring
    (SessionState.EXPLORING, "list_resources"): SessionState.EXPLORING,
    (SessionState.EXPLORING, "read_resource"): SessionState.EXPLORING,
    (SessionState.EXPLORING, "download_attempt"): SessionState.EXFILTRATING,
    (SessionState.EXPLORING, "iam_action"): SessionState.PRIVILEGE_ESCALATION,
    (SessionState.EXPLORING, "cross_service_access"): SessionState.LATERAL_MOVEMENT,
    (SessionState.EXPLORING, "session_timeout"): SessionState.EXPIRED,
    # Exfiltrating
    (SessionState.EXFILTRATING, "download_attempt"): SessionState.EXFILTRATING,
    (SessionState.EXFILTRATING, "bulk_download"): SessionState.EXFILTRATING,
    (SessionState.EXFILTRATING, "data_limit_exceeded"): SessionState.BLOCKED,
    (SessionState.EXFILTRATING, "session_timeout"): SessionState.EXPIRED,
    # Privilege escalation
    (
        SessionState.PRIVILEGE_ESCALATION,
        "iam_action",
    ): SessionState.PRIVILEGE_ESCALATION,
    (SessionState.PRIVILEGE_ESCALATION, "role_assumed"): SessionState.AUTHENTICATED,
    (SessionState.PRIVILEGE_ESCALATION, "privilege_denied"): SessionState.EXPLORING,
    (
        SessionState.PRIVILEGE_ESCALATION,
        "cross_service_access",
    ): SessionState.LATERAL_MOVEMENT,
    (SessionState.PRIVILEGE_ESCALATION, "session_timeout"): SessionState.EXPIRED,
    # Lateral movement
    (
        SessionState.LATERAL_MOVEMENT,
        "cross_service_access",
    ): SessionState.LATERAL_MOVEMENT,
    (SessionState.LATERAL_MOVEMENT, "download_attempt"): SessionState.EXFILTRATING,
    (SessionState.LATERAL_MOVEMENT, "iam_action"): SessionState.PRIVILEGE_ESCALATION,
    (SessionState.LATERAL_MOVEMENT, "session_timeout"): SessionState.EXPIRED,
}

# Triggers that indicate specific attack categories
TRIGGER_CATEGORY_MAP: Dict[str, CloudAttackCategory] = {
    "auth_attempt": CloudAttackCategory.CREDENTIAL_STUFFING,
    "auth_failure": CloudAttackCategory.BRUTE_FORCE,
    "mfa_challenge": CloudAttackCategory.MFA_BYPASS,
    "iam_action": CloudAttackCategory.IAM_ENUMERATION,
    "role_assumed": CloudAttackCategory.ROLE_ASSUMPTION,
    "download_attempt": CloudAttackCategory.S3_EXFILTRATION,
    "bulk_download": CloudAttackCategory.S3_EXFILTRATION,
    "cross_service_access": CloudAttackCategory.PRIVILEGE_ESCALATION,
}

# State severity ratings for threat scoring
STATE_SEVERITY: Dict[SessionState, int] = {
    SessionState.DISCOVERY: 10,
    SessionState.PRE_AUTH: 20,
    SessionState.AUTHENTICATED: 30,
    SessionState.EXPLORING: 40,
    SessionState.EXFILTRATING: 80,
    SessionState.PRIVILEGE_ESCALATION: 70,
    SessionState.LATERAL_MOVEMENT: 90,
    SessionState.BLOCKED: 0,
    SessionState.EXPIRED: 0,
}


class SessionStateMachine:
    """Manages session state transitions and behavioral tracking."""

    def __init__(
        self,
        session: CloudSession,
        max_auth_attempts: int = 5,
        session_timeout_minutes: int = 30,
        on_state_change: Optional[
            Callable[[SessionState, SessionState, str], None]
        ] = None,
    ):
        """Initialize state machine.

        Args:
            session: CloudSession to manage
            max_auth_attempts: Maximum failed auth attempts before blocking
            session_timeout_minutes: Session inactivity timeout
            on_state_change: Callback when state changes (old, new, trigger)
        """
        self.session = session
        self.max_auth_attempts = max_auth_attempts
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self.on_state_change = on_state_change

        # Behavioral tracking
        self._trigger_history: List[Dict[str, Any]] = []
        self._services_accessed: Set[str] = set()
        self._actions_by_service: Dict[str, Set[str]] = {}
        self._anomaly_scores: Dict[str, float] = {}

    @property
    def current_state(self) -> SessionState:
        """Get current session state."""
        return self.session.current_state

    @property
    def is_terminal(self) -> bool:
        """Check if session is in terminal state."""
        return self.session.current_state in (
            SessionState.BLOCKED,
            SessionState.EXPIRED,
        )

    def process_trigger(
        self,
        trigger: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Tuple[SessionState, bool]:
        """Process a trigger and potentially transition state.

        Args:
            trigger: Trigger event name
            context: Additional context for the trigger

        Returns:
            Tuple of (new_state, did_transition)
        """
        context = context or {}
        old_state = self.session.current_state

        # Check for timeout
        if self._check_timeout():
            return self._force_transition(SessionState.EXPIRED, "session_timeout")

        # Handle special auth logic
        if trigger == "auth_failure":
            self.session.auth_attempts += 1
            if self.session.auth_attempts >= self.max_auth_attempts:
                trigger = "max_auth_exceeded"

        # Look up transition
        transition_key = (old_state, trigger)
        new_state = STATE_TRANSITIONS.get(transition_key)

        if new_state is None:
            # No valid transition, stay in current state
            logger.debug(
                f"No transition for ({old_state.value}, {trigger}), staying in {old_state.value}"
            )
            self._record_trigger(trigger, context, transitioned=False)
            return old_state, False

        # Execute transition
        return self._execute_transition(old_state, new_state, trigger, context)

    def _execute_transition(
        self,
        old_state: SessionState,
        new_state: SessionState,
        trigger: str,
        context: Dict[str, Any],
    ) -> Tuple[SessionState, bool]:
        """Execute a state transition."""
        now = datetime.now(timezone.utc)

        # Update session
        self.session.current_state = new_state
        self.session.last_activity = now
        self.session.state_transition_count += 1

        # Record state history
        self.session.state_history.append(
            {
                "from_state": old_state.value,
                "to_state": new_state.value,
                "trigger": trigger,
                "timestamp": now.isoformat(),
                "context": self._sanitize_context(context),
            }
        )

        # Update threat score
        self._update_threat_score(new_state, trigger)

        # Update attack categories
        if trigger in TRIGGER_CATEGORY_MAP:
            category = TRIGGER_CATEGORY_MAP[trigger]
            self.session.detected_categories.add(category)
            if self._is_higher_priority_category(category):
                self.session.primary_category = category

        # Record trigger
        self._record_trigger(trigger, context, transitioned=True, new_state=new_state)

        # Invoke callback
        if self.on_state_change:
            try:
                self.on_state_change(old_state, new_state, trigger)
            except Exception as e:
                logger.error(f"State change callback error: {e}")

        logger.info(
            f"Session {self.session.session_id}: {old_state.value} -> {new_state.value} "
            f"(trigger: {trigger})"
        )

        return new_state, True

    def _force_transition(
        self,
        new_state: SessionState,
        reason: str,
    ) -> Tuple[SessionState, bool]:
        """Force a transition regardless of rules."""
        old_state = self.session.current_state
        return self._execute_transition(old_state, new_state, reason, {"forced": True})

    def _check_timeout(self) -> bool:
        """Check if session has timed out."""
        if self.is_terminal:
            return False

        elapsed = datetime.now(timezone.utc) - self.session.last_activity
        return elapsed > self.session_timeout

    def _update_threat_score(self, new_state: SessionState, trigger: str) -> None:
        """Update session threat score based on state and behavior."""
        base_score = STATE_SEVERITY.get(new_state, 0)

        # Add trigger-specific modifiers
        modifiers = {
            "auth_failure": 5,
            "iam_action": 10,
            "download_attempt": 15,
            "bulk_download": 25,
            "cross_service_access": 20,
            "role_assumed": 15,
        }
        modifier = modifiers.get(trigger, 0)

        # Calculate cumulative score (capped at 100)
        new_score = min(100.0, base_score + modifier + self.session.threat_score * 0.1)
        self.session.threat_score = new_score

        # Update max severity
        if new_score >= 80:
            self.session.max_severity = APICallSeverity.CRITICAL
        elif new_score >= 60:
            self.session.max_severity = APICallSeverity.HIGH
        elif new_score >= 40:
            self.session.max_severity = APICallSeverity.MEDIUM
        elif new_score >= 20:
            self.session.max_severity = APICallSeverity.LOW

    def _is_higher_priority_category(self, category: CloudAttackCategory) -> bool:
        """Check if category is higher priority than current primary."""
        priority_order = [
            CloudAttackCategory.UNKNOWN,
            CloudAttackCategory.SERVICE_DISCOVERY,
            CloudAttackCategory.IAM_ENUMERATION,
            CloudAttackCategory.BUCKET_ENUMERATION,
            CloudAttackCategory.CREDENTIAL_STUFFING,
            CloudAttackCategory.BRUTE_FORCE,
            CloudAttackCategory.MFA_BYPASS,
            CloudAttackCategory.ROLE_ASSUMPTION,
            CloudAttackCategory.PRIVILEGE_ESCALATION,
            CloudAttackCategory.SSRF,
            CloudAttackCategory.SECRETS_EXTRACTION,
            CloudAttackCategory.S3_EXFILTRATION,
            CloudAttackCategory.BACKDOOR_USER,
            CloudAttackCategory.LAMBDA_BACKDOOR,
        ]

        current_idx = (
            priority_order.index(self.session.primary_category)
            if self.session.primary_category in priority_order
            else 0
        )
        new_idx = priority_order.index(category) if category in priority_order else 0

        return new_idx > current_idx

    def _record_trigger(
        self,
        trigger: str,
        context: Dict[str, Any],
        transitioned: bool,
        new_state: Optional[SessionState] = None,
    ) -> None:
        """Record trigger for behavioral analysis."""
        self._trigger_history.append(
            {
                "trigger": trigger,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "transitioned": transitioned,
                "new_state": new_state.value if new_state else None,
                "context_keys": list(context.keys()),
            }
        )

        # Track service access patterns
        if "service" in context:
            service = context["service"]
            self._services_accessed.add(service)
            if service not in self._actions_by_service:
                self._actions_by_service[service] = set()
            if "action" in context:
                self._actions_by_service[service].add(context["action"])

    def _sanitize_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize context for storage (remove sensitive data)."""
        sensitive_keys = {
            "password",
            "secret",
            "token",
            "key",
            "credential",
            "authorization",
        }
        sanitized = {}
        for k, v in context.items():
            k_lower = k.lower()
            if any(s in k_lower for s in sensitive_keys):
                sanitized[k] = "***REDACTED***"
            elif isinstance(v, str) and len(v) > 200:
                sanitized[k] = v[:200] + "...[truncated]"
            else:
                sanitized[k] = v
        return sanitized

    def get_behavioral_profile(self) -> Dict[str, Any]:
        """Get behavioral analysis profile for the session."""
        return {
            "trigger_count": len(self._trigger_history),
            "unique_triggers": len(set(t["trigger"] for t in self._trigger_history)),
            "services_accessed": list(self._services_accessed),
            "actions_by_service": {
                svc: list(actions) for svc, actions in self._actions_by_service.items()
            },
            "state_transitions": self.session.state_transition_count,
            "threat_score": self.session.threat_score,
            "primary_category": self.session.primary_category.value,
            "detected_categories": [c.value for c in self.session.detected_categories],
            "is_terminal": self.is_terminal,
            "duration_seconds": (
                (datetime.now(timezone.utc) - self.session.started_at).total_seconds()
            ),
        }

    def predict_next_actions(self) -> List[str]:
        """Predict likely next actions based on state and history.

        Used for adaptive baiting and response generation.
        """
        predictions = []
        state = self.session.current_state

        # State-based predictions
        if state == SessionState.DISCOVERY:
            predictions.extend(
                [
                    "endpoint_enumeration",
                    "version_probe",
                    "auth_attempt",
                ]
            )
        elif state == SessionState.PRE_AUTH:
            predictions.extend(
                [
                    "credential_spray",
                    "token_reuse",
                    "mfa_probe",
                ]
            )
        elif state == SessionState.AUTHENTICATED:
            predictions.extend(
                [
                    "whoami",
                    "list_users",
                    "list_buckets",
                    "describe_instances",
                ]
            )
        elif state == SessionState.EXPLORING:
            predictions.extend(
                [
                    "get_bucket_acl",
                    "list_secrets",
                    "describe_vpcs",
                    "get_policy",
                ]
            )
        elif state == SessionState.EXFILTRATING:
            predictions.extend(
                [
                    "get_object",
                    "sync_bucket",
                    "get_secret_value",
                ]
            )
        elif state == SessionState.PRIVILEGE_ESCALATION:
            predictions.extend(
                [
                    "create_user",
                    "attach_policy",
                    "create_access_key",
                    "assume_role",
                ]
            )
        elif state == SessionState.LATERAL_MOVEMENT:
            predictions.extend(
                [
                    "cross_account_access",
                    "lambda_invoke",
                    "ssm_run_command",
                ]
            )

        return predictions

    def end_session(self, reason: str = "manual") -> None:
        """End the session and record final state."""
        now = datetime.now(timezone.utc)

        if not self.is_terminal:
            self._force_transition(SessionState.EXPIRED, f"end_session:{reason}")

        self.session.ended_at = now
        self.session.duration_seconds = (now - self.session.started_at).total_seconds()

        logger.info(
            f"Session {self.session.session_id} ended: "
            f"duration={self.session.duration_seconds:.1f}s, "
            f"threat_score={self.session.threat_score:.1f}, "
            f"category={self.session.primary_category.value}"
        )
