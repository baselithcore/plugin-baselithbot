"""MISP Threat Intelligence Bridge.

Handles automation integration with MISP (Malware Information Sharing Platform).
Supports automatic IoC export and real-time enrichment.
"""

import asyncio
from core.observability.logging import get_logger
import time
from typing import Any, Dict, List, Optional

try:
    from pymisp import PyMISP

    HAS_PYMISP = True
except ImportError:
    HAS_PYMISP = False

logger = get_logger(__name__)


class CircuitBreaker:
    """Simple Circuit Breaker pattern."""

    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED (working), OPEN (blocking)

    def record_failure(self):
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit Breaker OPENED after {self.failures} failures")

    def record_success(self):
        self.failures = 0
        self.state = "CLOSED"

    def can_execute(self) -> bool:
        if self.state == "CLOSED":
            return True

        # Check partial recovery (Half-Open logic simplified)
        if time.time() - self.last_failure_time > self.recovery_timeout:
            self.state = "HALF-OPEN"
            return True

        return False


class MISPBridge:
    """Bridge for interacting with MISP instance."""

    def __init__(self, api_url: str, api_key: str, verify_ssl: bool = True):
        self.api_url = api_url
        self.api_key = api_key
        self.verify_ssl = verify_ssl
        self._misp: Optional[Any] = None
        self._breaker = CircuitBreaker()

        if not HAS_PYMISP:
            logger.warning("PyMISP not installed. Threat Intel bridge disabled.")
            return

        try:
            self._misp = PyMISP(api_url, api_key, verify_ssl, debug=False)
            logger.info("MISP Bridge initialized")
        except Exception as e:
            logger.error(f"Failed to initialize MISP connection: {e}")
            self._breaker.record_failure()

    async def export_ioc(
        self, ioc_value: str, ioc_type: str, comment: str = "", tags: List[str] = None
    ) -> bool:
        """
        Export an IoC to MISP asynchronously.

        Args:
            ioc_value: The IoC string (IP, Domain, Hash)
            ioc_type: MISP type (ip-src, domain, sha256)
            comment: Contextual comment
            tags: List of tags to apply
        """
        if not self._misp or not self._breaker.can_execute():
            return False

        return await asyncio.to_thread(
            self._sync_export_ioc, ioc_value, ioc_type, comment, tags
        )

    def _sync_export_ioc(
        self, ioc_value: str, ioc_type: str, comment: str, tags: List[str]
    ) -> bool:
        """Synchronous implementation for thread wrapping."""
        try:
            # 1. Check if event exists for "HoneyDOC Detected" or create new
            # Simplified: finding a daily event or creating one
            event_info = f"HoneyDOC Detections - {time.strftime('%Y-%m-%d')}"

            # Search for existing event (simplified logic)
            events = self._misp.search(eventinfo=event_info, limit=1)

            if events:
                event_id = events[0]["Event"]["id"]
                event = self._misp.get_event(event_id)
            else:
                event = self._misp.new_event(
                    info=event_info, distribution=0, threat_level_id=2, analysis=0
                )

            # 2. Add Attribute
            self._misp.add_attribute(
                event=event,
                type=ioc_type,
                value=ioc_value,
                comment=comment,
                to_ids=True,
            )

            # 3. Add Tags
            if tags:
                for tag in tags:
                    self._misp.tag(event, tag)

            self._breaker.record_success()
            logger.info(f"Exported IoC {ioc_value} to MISP")
            return True

        except Exception as e:
            logger.error(f"Failed to export IoC to MISP: {e}")
            self._breaker.record_failure()
            return False

    async def enrich_event(self, ioc_value: str) -> Dict[str, Any]:
        """
        Query MISP for intelligence on an IoC.
        """
        if not self._misp or not self._breaker.can_execute():
            return {}

        return await asyncio.to_thread(self._sync_enrich, ioc_value)

    def _sync_enrich(self, ioc_value: str) -> Dict[str, Any]:
        """Synchronous enrichment."""
        try:
            # Search attributes
            result = self._misp.search(value=ioc_value, controller="attributes")
            # Logic to parse result and extract threat score/tags

            self._breaker.record_success()
            return {"raw_result": result}

        except Exception as e:
            logger.error(f"Failed to enrich IoC from MISP: {e}")
            self._breaker.record_failure()
            return {}

    async def check_connection(self) -> bool:
        """Check availability of MISP server."""
        if not self._misp:
            return False

        return await asyncio.to_thread(self._sync_check_connection)

    def _sync_check_connection(self) -> bool:
        """Synchronous connection check."""
        try:
            # Lightweight call to verify connectivity
            self._misp.get_version()
            self._breaker.record_success()
            return True
        except Exception:
            self._breaker.record_failure()
            return False

    def get_status(self) -> Dict[str, Any]:
        """Get bridge health and sync status."""
        if not HAS_PYMISP:
            return {
                "enabled": False,
                "status": "missing_dependencies",
                "sync_percentage": 0,
            }

        if not self._misp:
            return {"enabled": False, "status": "not_configured", "sync_percentage": 0}

        can_execute = self._breaker.can_execute()
        status_str = self._breaker.state

        # Calculate sync percentage based on state and verified connectivity
        # If open (failed), 0%. If half-open, 50%. If closed (healthy), 100%.
        sync_percentage = 0
        if status_str == "CLOSED":
            sync_percentage = 100
        elif status_str == "HALF-OPEN":
            sync_percentage = 50

        return {
            "enabled": True,
            "status": status_str,
            "can_execute": can_execute,
            "sync_percentage": sync_percentage,
            "failures": self._breaker.failures,
        }
