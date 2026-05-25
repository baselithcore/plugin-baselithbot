"""
Risk-Based Authentication (Adaptive Authentication).

Analyzes authentication requests for anomalies and adjusts security requirements.
Factors considered:
- Geolocation changes
- Device fingerprinting
- Login velocity (impossible travel)
- Time-of-day patterns
- User-Agent changes

Reference: NIST SP 800-63B Appendix A
"""

import hashlib
from core.observability.logging import get_logger
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

from fastapi import Request

logger = get_logger(__name__)


@dataclass
class RiskScore:
    """Authentication risk assessment result."""

    score: float  # 0.0 (low risk) to 1.0 (high risk)
    reasons: list[str]  # Human-readable reasons for the score
    require_step_up: bool  # Require additional authentication
    recommended_action: str  # "allow", "challenge", "block"

    def is_high_risk(self) -> bool:
        """Check if risk is high enough to require action."""
        return self.score >= 0.7

    def is_medium_risk(self) -> bool:
        """Check if risk is medium."""
        return 0.4 <= self.score < 0.7


@dataclass
class AuthenticationContext:
    """Context information for authentication request."""

    user_id: str
    ip_address: str
    user_agent: str
    timestamp: datetime
    country: Optional[str] = None
    city: Optional[str] = None
    device_fingerprint: Optional[str] = None


class RiskAssessor:
    """
    Assess authentication risk based on context.

    Uses heuristics to detect anomalous login attempts.
    In production, integrate with:
    - MaxMind GeoIP2 for geolocation
    - ML models for behavioral analysis
    - Threat intelligence feeds
    """

    def __init__(self) -> None:
        """Initialize risk assessor."""
        # In-memory store for user history (use Redis in production)
        self._user_history: Dict[str, list[AuthenticationContext]] = {}

        # Configurable thresholds
        self.max_history_entries = 20
        self.velocity_check_minutes = 60
        self.impossible_travel_km_per_hour = 800  # Airplane speed

    def _get_device_fingerprint(self, request: Request) -> str:
        """
        Generate device fingerprint from request.

        Combines User-Agent and other headers for basic fingerprinting.
        In production, use FingerprintJS or similar.
        """
        components = [
            request.headers.get("User-Agent", ""),
            request.headers.get("Accept-Language", ""),
            request.headers.get("Accept-Encoding", ""),
        ]

        fingerprint_str = "|".join(components)
        return hashlib.sha256(fingerprint_str.encode()).hexdigest()[:16]

    def _extract_context(self, request: Request, user_id: str) -> AuthenticationContext:
        """Extract authentication context from request."""
        # Get IP address
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            ip_address = forwarded.split(",")[0].strip()
        elif request.client:
            ip_address = request.client.host
        else:
            ip_address = "unknown"

        # Get User-Agent
        user_agent = request.headers.get("User-Agent", "unknown")

        # Generate device fingerprint
        device_fingerprint = self._get_device_fingerprint(request)

        return AuthenticationContext(
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            timestamp=datetime.now(timezone.utc),
            device_fingerprint=device_fingerprint,
        )

    def _check_velocity(
        self, current: AuthenticationContext, history: list[AuthenticationContext]
    ) -> tuple[float, Optional[str]]:
        """
        Check for velocity abuse (rapid login attempts).

        Returns:
            Tuple of (risk_score_delta, reason)
        """
        if not history:
            return 0.0, None

        # Count logins in last hour
        recent_logins = [
            ctx
            for ctx in history
            if current.timestamp - ctx.timestamp
            < timedelta(minutes=self.velocity_check_minutes)
        ]

        if len(recent_logins) >= 5:
            return (
                0.3,
                f"{len(recent_logins)} login attempts in last {self.velocity_check_minutes} minutes",
            )

        return 0.0, None

    def _check_device_change(
        self, current: AuthenticationContext, history: list[AuthenticationContext]
    ) -> tuple[float, Optional[str]]:
        """
        Check for device/browser changes.

        Returns:
            Tuple of (risk_score_delta, reason)
        """
        if not history:
            return 0.0, None

        # Check last known device
        last_context = history[-1]

        if current.device_fingerprint != last_context.device_fingerprint:
            return 0.2, "New device detected"

        if current.user_agent != last_context.user_agent:
            return 0.15, "User-Agent changed"

        return 0.0, None

    def _check_ip_change(
        self, current: AuthenticationContext, history: list[AuthenticationContext]
    ) -> tuple[float, Optional[str]]:
        """
        Check for IP address changes.

        Returns:
            Tuple of (risk_score_delta, reason)
        """
        if not history:
            return 0.0, None

        # Check last known IP
        last_context = history[-1]

        if current.ip_address != last_context.ip_address:
            return 0.15, f"IP address changed (from {last_context.ip_address})"

        return 0.0, None

    def _check_time_anomaly(
        self, current: AuthenticationContext, history: list[AuthenticationContext]
    ) -> tuple[float, Optional[str]]:
        """
        Check for unusual login time.

        Returns:
            Tuple of (risk_score_delta, reason)
        """
        if not history:
            return 0.0, None

        # Simple heuristic: check hour of day
        hour = current.timestamp.hour

        # Flag logins between 2 AM and 5 AM as slightly suspicious
        # (unless user has history of such logins)
        if 2 <= hour < 5:
            # Check if user has previous logins in this time range
            night_logins = [ctx for ctx in history if 2 <= ctx.timestamp.hour < 5]

            if not night_logins:
                return 0.1, f"Unusual login time: {hour}:00"

        return 0.0, None

    def assess_risk(self, request: Request, user_id: str) -> RiskScore:
        """
        Assess risk for authentication attempt.

        Args:
            request: FastAPI request object
            user_id: User ID attempting authentication

        Returns:
            RiskScore with assessment result
        """
        # Extract current context
        current_context = self._extract_context(request, user_id)

        # Get user history
        history = self._user_history.get(user_id, [])

        # Calculate risk factors
        risk_score = 0.0
        reasons = []

        # Check various risk factors
        checks = [
            self._check_velocity(current_context, history),
            self._check_device_change(current_context, history),
            self._check_ip_change(current_context, history),
            self._check_time_anomaly(current_context, history),
        ]

        for score_delta, reason in checks:
            if reason:
                risk_score += score_delta
                reasons.append(reason)

        # Ensure score is in valid range
        risk_score = min(risk_score, 1.0)

        # Determine action
        if risk_score >= 0.7:
            recommended_action = "block"
            require_step_up = True
        elif risk_score >= 0.4:
            recommended_action = "challenge"
            require_step_up = True
        else:
            recommended_action = "allow"
            require_step_up = False

        # Log assessment
        if risk_score > 0.0:
            logger.info(
                f"Risk assessment for user {user_id}: score={risk_score:.2f}, "
                f"action={recommended_action}, reasons={reasons}"
            )

        return RiskScore(
            score=risk_score,
            reasons=reasons,
            require_step_up=require_step_up,
            recommended_action=recommended_action,
        )

    def record_successful_authentication(self, request: Request, user_id: str) -> None:
        """
        Record successful authentication for future risk assessment.

        Args:
            request: FastAPI request object
            user_id: User ID
        """
        context = self._extract_context(request, user_id)

        if user_id not in self._user_history:
            self._user_history[user_id] = []

        self._user_history[user_id].append(context)

        # Limit history size
        if len(self._user_history[user_id]) > self.max_history_entries:
            self._user_history[user_id] = self._user_history[user_id][
                -self.max_history_entries :
            ]

    def clear_user_history(self, user_id: str) -> None:
        """Clear history for a user (e.g., on password change)."""
        if user_id in self._user_history:
            del self._user_history[user_id]


# Global instance
_risk_assessor: Optional[RiskAssessor] = None


def get_risk_assessor() -> RiskAssessor:
    """Get or create global risk assessor instance."""
    global _risk_assessor
    if _risk_assessor is None:
        _risk_assessor = RiskAssessor()
    return _risk_assessor
