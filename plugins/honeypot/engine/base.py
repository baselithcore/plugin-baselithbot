"""Base Honeypot Handler.

Abstract base class for protocol handlers with shared functionality.
"""

from core.observability.logging import get_logger
import re
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from typing import List, Tuple, Dict, Deque
from collections import deque

from ..config import HoneypotConfig
from ..models import AttackCategory, AttackEvent, AttackSeverity
from .bot_detector import get_bot_detector

logger = get_logger(__name__)


# Common attack patterns for detection
ATTACK_PATTERNS = {
    # SQL Injection
    "sql_injection": [
        r"(?i)(union\s+select|select\s+.*\s+from|insert\s+into|delete\s+from)",
        r"(?i)(drop\s+table|drop\s+database|truncate\s+table)",
        r"(?i)(or\s+1\s*=\s*1|or\s+'1'\s*=\s*'1'|or\s+\"1\"\s*=\s*\"1\")",
        r"(?i)(--\s*$|;\s*--)",
        r"(?i)(waitfor\s+delay|benchmark\s*\()",
    ],
    # Command Injection
    "command_injection": [
        r"(?i)(;\s*cat\s|;\s*ls\s|;\s*id\s|;\s*whoami)",
        r"(?i)(\||\$\(|`)(cat|ls|id|whoami|uname|pwd|wget|curl)",
        r"(?i)(&&\s*(cat|ls|id|whoami|rm|wget))",
        r"(?i)(/etc/passwd|/etc/shadow)",
        r"(?i)(nc\s+-e|bash\s+-i|python\s+-c|perl\s+-e)",
        r"(?i)(rm\s+-rf|chmod\s+777|chown)",
    ],
    # Path Traversal
    "path_traversal": [
        r"\.\.\/",
        r"\.\.\\\\",
        r"%2e%2e%2f",
        r"%2e%2e/",
        r"\.\.%2f",
        r"(?i)(\/etc\/passwd|\/etc\/shadow|\/etc\/hosts)",
        r"(?i)(\.env|\.git\/config|\.htaccess)",
    ],
    # XSS
    "xss": [
        r"<script[^>]*>",
        r"javascript:",
        r"onerror\s*=",
        r"onload\s*=",
        r"onclick\s*=",
        r"(?i)(alert\s*\(|confirm\s*\(|prompt\s*\()",
        r"<img[^>]+onerror",
    ],
    # Reconnaissance
    "reconnaissance": [
        r"(?i)(nmap|nikto|sqlmap|wpscan|gobuster|dirbuster)",
        r"(?i)(\.git|\.svn|\.hg|\.env|\.htaccess|\.htpasswd)",
        r"(?i)(phpinfo|php_info|server-status|server-info)",
        r"(?i)(robots\.txt|sitemap\.xml|crossdomain\.xml)",
        r"(?i)(wp-config|configuration\.php|config\.php)",
    ],
    # Malware patterns
    "malware": [
        r"(?i)(wget\s+.*\s+-O|curl\s+.*\s+-o)",
        r"(?i)(chmod\s+\+x|bash\s+<)",
        r"(?i)(base64\s+-d|base64\s+--decode)",
        r"(?i)(crypto|miner|xmr|monero)",
    ],
}


class BaseHandler(ABC):
    """Abstract base class for honeypot protocol handlers."""

    def __init__(self, config: HoneypotConfig, definition=None):
        """Initialize handler.

        Args:
            config: Honeypot configuration
            definition: Optional HoneypotDefinition for per-honeypot overrides
        """
        self.config = config
        self.definition = definition
        self._running = False
        self._events: List[AttackEvent] = []
        self._event_callback = None

        # Rate limiting state
        # Map IP -> Deque of timestamps
        self._connection_history: Dict[str, Deque[float]] = defaultdict(deque)
        self._cleanup_counter = 0

    @abstractmethod
    async def start(self, port: int = None) -> None:
        """Start the handler service.

        Args:
             port: Optional port to override config
        """
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Stop the handler service."""
        pass

    @property
    def is_running(self) -> bool:
        """Check if handler is running."""
        return self._running

    def set_event_callback(self, callback) -> None:
        """Set callback for new events.

        Args:
            callback: Async function to call with new events
        """
        self._event_callback = callback

    def set_flow_check_callback(self, callback) -> None:
        """Set callback for flow control checks.

        Args:
            callback: Function taking (ip, session_id) returning bool (is_allowed)
        """
        self._flow_check_callback = callback

    def check_flow_allowed(self, ip: str, session_id: str = "") -> bool:
        """Check if traffic flow is allowed.

        Args:
            ip: Source IP
            session_id: Session ID (optional)

        Returns:
            True if flow is allowed (not blocked)
        """
        if hasattr(self, "_flow_check_callback") and self._flow_check_callback:
            return self._flow_check_callback(ip, session_id)
        return True

    def check_rate_limit(self, ip: str) -> bool:
        """Check if IP has exceeded connection rate limits.

        Uses a sliding window algorithm.

        Args:
            ip: Source IP address

        Returns:
            True if connection is allowed, False if rate limited
        """
        now = time.time()
        limit = self.config.rate_limit_connections_per_ip
        window = float(self.config.rate_limit_window_seconds)

        history = self._connection_history[ip]

        # Remove old timestamps
        while history and history[0] < now - window:
            history.popleft()

        # Check limit
        if len(history) >= limit:
            logger.warning(f"Rate limit exceeded for IP {ip} ({len(history)}/{limit})")
            return False

        # Record new connection
        history.append(now)

        # Periodic cleanup of empty entries (every 100 checks)
        self._cleanup_counter += 1
        if self._cleanup_counter > 100:
            self._cleanup_counter = 0
            self._cleanup_rate_limit_history(now, window)

        return True

    def _cleanup_rate_limit_history(self, now: float, window: float) -> None:
        """Clean up expired rate limit history."""
        params_to_del = []
        for ip, timestamps in self._connection_history.items():
            # Remove old
            while timestamps and timestamps[0] < now - window:
                timestamps.popleft()
            if not timestamps:
                params_to_del.append(ip)

        for ip in params_to_del:
            del self._connection_history[ip]

    def detect_patterns(self, payload: str) -> Tuple[List[str], AttackCategory]:
        """Detect attack patterns in payload.

        Args:
            payload: Raw payload/command to analyze

        Returns:
            Tuple of (detected patterns, primary category)
        """
        detected = []
        categories = []

        for category, patterns in ATTACK_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, payload):
                    detected.append(pattern)
                    categories.append(category)
                    break  # One match per category is enough

        # Determine primary category
        primary = AttackCategory.UNKNOWN
        if "command_injection" in categories:
            primary = AttackCategory.COMMAND_INJECTION
        elif "sql_injection" in categories:
            primary = AttackCategory.SQL_INJECTION
        elif "path_traversal" in categories:
            primary = AttackCategory.PATH_TRAVERSAL
        elif "xss" in categories:
            primary = AttackCategory.XSS
        elif "reconnaissance" in categories:
            primary = AttackCategory.RECONNAISSANCE
        elif "malware" in categories:
            primary = AttackCategory.MALWARE_DELIVERY

        return detected, primary

    def calculate_severity(
        self,
        category: AttackCategory,
        detected_patterns: List[str],
    ) -> AttackSeverity:
        """Calculate severity based on category and patterns.

        Args:
            category: Attack category
            detected_patterns: List of detected patterns

        Returns:
            Calculated severity level
        """
        # Critical severity
        if category == AttackCategory.EXPLOIT_ATTEMPT:
            return AttackSeverity.CRITICAL

        # High severity categories
        if category in (
            AttackCategory.COMMAND_INJECTION,
            AttackCategory.SQL_INJECTION,
            AttackCategory.MALWARE_DELIVERY,
            AttackCategory.BRUTE_FORCE,
        ):
            if len(detected_patterns) >= 2:
                return AttackSeverity.CRITICAL
            return AttackSeverity.HIGH

        # Medium severity
        if category in (
            AttackCategory.PATH_TRAVERSAL,
            AttackCategory.XSS,
            AttackCategory.CREDENTIAL_HARVESTING,
        ):
            return AttackSeverity.MEDIUM

        # Lower severity
        if category == AttackCategory.RECONNAISSANCE:
            return AttackSeverity.LOW

        return AttackSeverity.INFO

    async def emit_event(self, event: AttackEvent) -> None:
        """Emit an event to registered callback.

        Args:
            event: Attack event to emit
        """
        logger.error(
            f"[DEBUG] BaseHandler.emit_event called for event: {event.event_id}"
        )

        # Perform bot detection analysis
        try:
            detector = get_bot_detector()
            payload = event.raw_data or event.command or ""

            # Extract User-Agent if available
            user_agent = ""
            if event.http_headers:
                # Case-insensitive header lookup
                for k, v in event.http_headers.items():
                    if k.lower() == "user-agent":
                        user_agent = v
                        break

            # Record this request for timing analysis
            detector.record_request(event.source_ip, payload)

            # Analyze if bot or human
            result = detector.analyze(event.source_ip, payload, user_agent=user_agent)

            # Enrich event with bot detection data
            event.is_bot = result.is_bot
            event.bot_confidence = result.confidence
            event.bot_classification = result.classification
            event.bot_signals = result.signals.to_dict()
        except Exception as e:
            logger.warning(f"Bot detection failed for {event.source_ip}: {e}")
            # Continue without bot detection data

        self._events.append(event)

        # Limit in-memory events
        max_events = self.config.max_log_entries
        if len(self._events) > max_events:
            self._events = self._events[-max_events:]

        if self._event_callback:
            try:
                await self._event_callback(event)
            except Exception as e:
                logger.error(f"Event callback error: {e}")

    def get_events(self, limit: int = 100) -> List[AttackEvent]:
        """Get recent events.

        Args:
            limit: Maximum number of events to return

        Returns:
            List of recent events
        """
        return list(reversed(self._events[-limit:]))

    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        import uuid

        return f"evt-{uuid.uuid4().hex[:12]}"

    def _generate_session_id(self) -> str:
        """Generate unique session ID."""
        import uuid

        return f"sess-{uuid.uuid4().hex[:12]}"

    # =========================================================================
    # HoneyDOC Stealth Features (Section IV-C3)
    # =========================================================================

    async def apply_stealth_delay(self) -> None:
        """Apply realistic response delay per HoneyDOC stealth design.

        Prevents detection by avoiding too-fast responses that
        indicate honeypot/emulation.
        """
        import asyncio
        import random

        if not self.config.enable_stealth:
            return

        # Check for per-honeypot override
        base_delay = self.config.stealth_response_delay_ms
        if (
            self.definition
            and self.definition.honeydoc
            and self.definition.honeydoc.stealth_delay_ms is not None
        ):
            base_delay = self.definition.honeydoc.stealth_delay_ms

        # Add jitter to base delay
        jitter = random.randint(0, base_delay // 2)  # nosec B311
        delay_ms = base_delay + jitter

        await asyncio.sleep(delay_ms / 1000.0)

    def get_fingerprint(self) -> dict:
        """Get consistent fingerprint info for stealth.

        Per HoneyDOC: All honeypots should present identical
        fingerprints to prevent detection during session migration.

        Returns:
            Fingerprint dictionary
        """
        # Start with global default
        fingerprint = {
            "os_name": "Linux",
            "os_version": "5.4.0-generic",
            "kernel": "5.4.0-generic #1 SMP x86_64 GNU/Linux",
            "hostname": self.config.ssh_server_name,
            "ssh_banner": f"SSH-2.0-{self.config.ssh_server_version}",
            "http_server": self.config.http_server_header,
        }

        # Apply per-honeypot overrides if present
        if (
            self.definition
            and self.definition.honeydoc
            and self.definition.honeydoc.custom_fingerprint
        ):
            fingerprint.update(self.definition.honeydoc.custom_fingerprint)

        return fingerprint

    def mask_response_headers(self, headers: dict) -> dict:
        """Mask headers that could reveal honeypot implementation.

        Per HoneyDOC stealth: Hide Python-specific headers.

        Args:
            headers: Original response headers

        Returns:
            Masked headers
        """
        if not self.config.mask_python_headers:
            return headers

        masked = headers.copy()

        # Replace Python-revealing headers
        if "Server" in masked:
            masked["Server"] = self.config.http_server_header
        if "X-Powered-By" in masked:
            masked["X-Powered-By"] = self.config.http_powered_by

        # Remove Python-specific headers
        python_headers = ["X-Python-Version", "X-Python-Runtime"]
        for h in python_headers:
            masked.pop(h, None)

        return masked
