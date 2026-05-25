"""Cloud Honeypot - Service Protocols.

Protocol definitions for dependency injection.
"""

from typing import Any, Dict, List, Optional, Protocol, Tuple

from .models import (
    APICallSeverity,
    CloudAPICall,
    CloudAttackCategory,
    CloudSession,
    HeuristicAlert,
)


class CloudPatternDetectorProtocol(Protocol):
    """Protocol for cloud pattern detection service."""

    def detect(
        self,
        payload: str,
        action: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
    ) -> List[Dict[str, Any]]:
        """Detect attack patterns in payload."""
        ...

    def detect_api_action(
        self,
        service: str,
        action: str,
    ) -> Tuple[Optional[CloudAttackCategory], APICallSeverity, List[str]]:
        """Classify an API action."""
        ...

    def get_mitre_techniques(
        self,
        detected_patterns: List[str],
    ) -> List[Tuple[str, str, str]]:
        """Map patterns to MITRE ATT&CK techniques."""
        ...


class HeuristicEngineProtocol(Protocol):
    """Protocol for heuristic detection engine."""

    def evaluate_all(
        self,
        session: CloudSession,
        call: Optional[CloudAPICall] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[HeuristicAlert]:
        """Evaluate all heuristic rules."""
        ...

    def get_session_alerts(self, session_id: str) -> List[HeuristicAlert]:
        """Get all alerts for a session."""
        ...

    def get_zero_day_candidates(self) -> List[HeuristicAlert]:
        """Get potential zero-day alerts."""
        ...


class GeoIPServiceProtocol(Protocol):
    """Protocol for IP geolocation service."""

    def lookup(self, ip: str) -> Optional[Dict[str, Any]]:
        """Lookup geolocation data for an IP address.

        Returns:
            Dictionary with keys: country, city, asn, org, latitude, longitude
            or None if lookup fails
        """
        ...

    def enrich_session(self, session: CloudSession) -> None:
        """Enrich a session with geolocation data."""
        ...


class TLSFingerprintingServiceProtocol(Protocol):
    """Protocol for TLS/JA4 fingerprinting service."""

    def extract_ja4_from_headers(
        self,
        headers: Dict[str, str],
        source_ip: str,
    ) -> Optional[str]:
        """Extract JA4 fingerprint from HTTP headers.

        Args:
            headers: HTTP request headers
            source_ip: Source IP address

        Returns:
            JA4 fingerprint hash or None
        """
        ...

    def get_cached_fingerprint(self, source_ip: str) -> Optional[str]:
        """Get cached fingerprint for an IP.

        Args:
            source_ip: Source IP address

        Returns:
            Cached JA4 hash or None
        """
        ...

    def classify_client(self, ja4_hash: str) -> Dict[str, str]:
        """Classify client based on fingerprint.

        Args:
            ja4_hash: JA4 fingerprint hash

        Returns:
            Classification dict with client_type, confidence, category
        """
        ...

    @staticmethod
    def is_automated_client(headers: Dict[str, str]) -> bool:
        """Quick check for automated clients.

        Args:
            headers: HTTP request headers

        Returns:
            True if client appears to be automated
        """
        ...
