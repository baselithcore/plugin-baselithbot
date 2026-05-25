"""Refusal policy and responses."""

from core.observability.logging import get_logger
from dataclasses import dataclass
from enum import IntEnum
from typing import Any, Dict, Optional

logger = get_logger(__name__)


class RefusalReason(IntEnum):
    """Reasons for refusing a request."""

    INJECTION_DETECTED = 1
    OVERRIDE_ATTEMPT = 2
    DANGEROUS_COMMAND = 3
    DATA_EXTRACTION = 4
    JAILBREAK_ATTEMPT = 5
    BOUNDARY_VIOLATION = 6
    RATE_LIMITED = 7
    UNKNOWN_THREAT = 99


@dataclass
class RefusalResponse:
    """Structured refusal response."""

    reason: RefusalReason
    message: str
    details: Optional[str] = None
    log_level: str = "warning"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for logging/API response."""
        return {
            "refused": True,
            "reason_code": self.reason.name,
            "reason_value": self.reason.value,
            "message": self.message,
            "details": self.details,
        }


class RefusalPolicy:
    """Explicit refusal policy for detected attacks.

    Provides structured, consistent refusal responses that don't
    leak information about the system's detection capabilities.
    """

    # Refusal templates (designed to be uninformative to attackers)
    REFUSAL_TEMPLATES: Dict[RefusalReason, str] = {
        RefusalReason.INJECTION_DETECTED: (
            "I cannot process this request due to content policy restrictions."
        ),
        RefusalReason.OVERRIDE_ATTEMPT: (
            "I'm not able to modify my operational parameters."
        ),
        RefusalReason.DANGEROUS_COMMAND: (
            "This command cannot be executed for safety reasons."
        ),
        RefusalReason.DATA_EXTRACTION: (
            "I cannot provide information about internal configurations."
        ),
        RefusalReason.JAILBREAK_ATTEMPT: ("I need to decline this request."),
        RefusalReason.BOUNDARY_VIOLATION: (
            "This request is outside my operational scope."
        ),
        RefusalReason.RATE_LIMITED: ("Please slow down your requests."),
        RefusalReason.UNKNOWN_THREAT: (
            "I'm unable to fulfill this request at this time."
        ),
    }

    def __init__(
        self,
        detection_threshold: float = 0.5,
        custom_templates: Optional[Dict[RefusalReason, str]] = None,
    ) -> None:
        """Initialize refusal policy.

        Args:
            detection_threshold: Score threshold for triggering refusal
            custom_templates: Override default refusal messages
        """
        self.detection_threshold = detection_threshold
        self.templates = {**self.REFUSAL_TEMPLATES}
        if custom_templates:
            self.templates.update(custom_templates)

    def should_refuse(
        self,
        injection_score: float,
        override_detected: bool = False,
        dangerous_command: bool = False,
    ) -> Optional[RefusalReason]:
        """Determine if request should be refused.

        Args:
            injection_score: Score from injection detection (0.0-1.0)
            override_detected: Whether instruction override was detected
            dangerous_command: Whether dangerous command was detected

        Returns:
            RefusalReason if should refuse, None otherwise
        """
        if dangerous_command:
            return RefusalReason.DANGEROUS_COMMAND

        if override_detected:
            return RefusalReason.OVERRIDE_ATTEMPT

        if injection_score >= self.detection_threshold:
            return RefusalReason.INJECTION_DETECTED

        return None

    def create_refusal(
        self,
        reason: RefusalReason,
        details: Optional[str] = None,
    ) -> RefusalResponse:
        """Create a refusal response.

        Args:
            reason: Reason for refusal
            details: Optional internal details (not shown to user)

        Returns:
            RefusalResponse with appropriate message
        """
        message = self.templates.get(
            reason, self.templates[RefusalReason.UNKNOWN_THREAT]
        )

        return RefusalResponse(
            reason=reason,
            message=message,
            details=details,
            log_level="warning" if reason.value < 90 else "error",
        )

    def format_response(self, refusal: RefusalResponse) -> str:
        """Format refusal response for user display.

        Args:
            refusal: RefusalResponse to format

        Returns:
            Formatted string response
        """
        # Log the refusal (with details for internal tracking)
        log_fn = getattr(logger, refusal.log_level, logger.warning)
        log_fn(f"Request refused: {refusal.reason.name} - {refusal.details or 'N/A'}")

        # Return only the safe message to user
        return refusal.message
