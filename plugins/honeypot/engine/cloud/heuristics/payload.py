"""Heuristic Detection - Payload-Based Rules.

Payload-based heuristics for detecting encoded or suspicious content.
"""

from core.observability.logging import get_logger
import re
from typing import Any, Dict, Optional

from ..models import APICallSeverity, CloudAPICall, CloudSession
from .base import HeuristicRule

logger = get_logger(__name__)


class EncodedPayloadHeuristic(HeuristicRule):
    """Detects base64 or URL-encoded payloads that may hide malicious content."""

    def __init__(self):
        super().__init__(
            name="encoded_payload",
            category="payload",
            description="Detects encoded payloads that may hide malicious content",
            severity=APICallSeverity.MEDIUM,
        )

    def evaluate(
        self,
        session: CloudSession,
        call: Optional[CloudAPICall] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[HeuristicRule]:
        if not call:
            return None

        payload = str(call.parameters)

        # Check for base64 patterns
        base64_pattern = re.compile(r"[A-Za-z0-9+/]{40,}={0,2}")
        base64_matches = base64_pattern.findall(payload)

        # Check for excessive URL encoding
        url_encoded_count = payload.count("%")

        if base64_matches and len(base64_matches[0]) > 50:
            return self.create_alert(
                session=session,
                trigger_reason="Large base64-encoded payload detected",
                evidence={
                    "base64_length": len(base64_matches[0]),
                    "match_count": len(base64_matches),
                },
                related_calls=[call.call_id],
                deviation=0.6,
            )

        if url_encoded_count > 20:
            return self.create_alert(
                session=session,
                trigger_reason="Heavily URL-encoded payload detected",
                evidence={
                    "url_encode_count": url_encoded_count,
                },
                related_calls=[call.call_id],
                deviation=0.5,
            )

        return None


class SuspiciousResourceNameHeuristic(HeuristicRule):
    """Detects suspicious patterns in resource names."""

    SUSPICIOUS_PATTERNS = [
        r"(?i)(test|tmp|temp|delete|backup|old)",  # Temporary/test resources
        r"(?i)(admin|root|superuser|god)",  # Privilege-related
        r"(?i)(hack|pwn|shell|backdoor|exploit)",  # Attack-related
        r"(?i)(\d{10,})",  # Epoch timestamps
        r"[a-f0-9]{32,}",  # Hash-like strings
    ]

    def __init__(self):
        super().__init__(
            name="suspicious_resource_name",
            category="payload",
            description="Detects suspicious patterns in resource names",
            severity=APICallSeverity.LOW,
        )
        self._patterns = [re.compile(p) for p in self.SUSPICIOUS_PATTERNS]

    def evaluate(
        self,
        session: CloudSession,
        call: Optional[CloudAPICall] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[HeuristicRule]:
        if not call:
            return None

        params_str = str(call.parameters)

        for pattern in self._patterns:
            matches = pattern.findall(params_str)
            if matches:
                return self.create_alert(
                    session=session,
                    trigger_reason=f"Suspicious resource name pattern: {matches[0][:50]}",
                    evidence={
                        "pattern": pattern.pattern,
                        "matches": matches[:5],
                    },
                    related_calls=[call.call_id],
                    deviation=0.4,
                )

        return None
