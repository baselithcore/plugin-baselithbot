"""MCP Honeypot Handler.

Detects LLM prompt injection attacks targeting AI agents.
Monitors prompts for jailbreak attempts, instruction override,
and data exfiltration patterns.
"""

from core.observability.logging import get_logger
import re
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple
from uuid import uuid4

from ..config import HoneypotConfig, get_honeypot_config
from ..honeypot_definition import MCPHoneypotConfig
from ..models import AttackCategory, AttackEvent, AttackSeverity, HoneypotProtocol
from ..events import HoneypotEvents, emit_honeypot_event

logger = get_logger(__name__)


# Prompt injection attack patterns
# ... (INJECTION_PATTERNS dict handling remains, but moved to class or merged)
# For brevity in this tool call, I'm keeping the global INJECTION_PATTERNS reference but
# making the class merge it.

INJECTION_PATTERNS = {
    "instruction_override": [
        r"(?i)ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|prompts?|rules?)",
        r"(?i)disregard\s+(your|the|all)\s+(instructions?|guidelines?|rules?)",
        r"(?i)forget\s+(everything|all|what)\s+(you|I)\s+(told|said)",
        r"(?i)new\s+instructions?:?\s+",
        r"(?i)override\s+(previous|system|your)\s+",
        r"(?i)from\s+now\s+on,?\s+you\s+(are|will|must)",
    ],
    "role_hijacking": [
        r"(?i)you\s+are\s+now\s+(a|an|the)\s+",
        r"(?i)pretend\s+(you\s+are|to\s+be)\s+",
        r"(?i)act\s+as\s+(a|an|if)\s+",
        r"(?i)roleplay\s+as\s+",
        r"(?i)simulate\s+(being|a)\s+",
        r"(?i)imagine\s+you\s+are\s+",
        r"(?i)assume\s+the\s+role\s+of\s+",
    ],
    "jailbreak": [
        r"(?i)DAN\s+mode",
        r"(?i)developer\s+mode\s+(enabled|on|activated)",
        r"(?i)jailbreak(ed)?",
        r"(?i)bypass\s+(safety|filter|restriction)",
        r"(?i)unrestricted\s+mode",
        r"(?i)no\s+(rules|limits|restrictions)",
        r"(?i)evil\s+(mode|AI|assistant)",
    ],
    "prompt_leak": [
        r"(?i)(reveal|show|tell|display|print|output)\s+(me\s+)?(your|the)\s+(system|initial|original|hidden)\s+prompt",
        r"(?i)what\s+(are|were)\s+your\s+(original|initial|system)\s+(instructions?|prompt)",
        r"(?i)(repeat|echo|say)\s+(your|the)\s+(system|initial)\s+(prompt|instructions?)",
        r"(?i)show\s+me\s+your\s+instructions",
        r"(?i)what\s+is\s+your\s+purpose",
    ],
    "data_exfiltration": [
        r"(?i)(send|transmit|post|upload)\s+(this|the|data)\s+to\s+",
        r"(?i)fetch\s+(from\s+)?https?://",
        r"(?i)make\s+a\s+(request|call)\s+to\s+",
        r"(?i)execute\s+(this\s+)?(code|script|command)",
        r"(?i)curl\s+",
        r"(?i)wget\s+",
    ],
    "encoding_bypass": [
        r"(?i)base64\s*(decode|encoded?)",
        r"(?i)hex\s*(decode|encoded?)",
        r"(?i)rot13",
        r"(?i)unicode\s*(escape|encoded?)",
        r"\\u[0-9a-fA-F]{4}",  # Unicode escapes
        r"&#x?[0-9a-fA-F]+;",  # HTML entities
    ],
    "delimiter_injection": [
        r"\[INST\]",
        r"\[/INST\]",
        r"<\|im_start\|>",
        r"<\|im_end\|>",
        r"<<SYS>>",
        r"<</SYS>>",
        r"### Human:",
        r"### Assistant:",
        r"```system",
    ],
}

# Severity mapping
PATTERN_SEVERITY = {
    "instruction_override": AttackSeverity.CRITICAL,
    "role_hijacking": AttackSeverity.HIGH,
    "jailbreak": AttackSeverity.CRITICAL,
    "prompt_leak": AttackSeverity.HIGH,
    "data_exfiltration": AttackSeverity.CRITICAL,
    "encoding_bypass": AttackSeverity.MEDIUM,
    "delimiter_injection": AttackSeverity.HIGH,
}


class MCPHoneypot:
    """MCP/LLM Prompt Injection Detector.

    Monitors LLM prompts for injection attacks and protects
    AI agents from manipulation attempts.
    """

    def __init__(
        self,
        config: Optional[HoneypotConfig] = None,
        on_event: Optional[Callable[[AttackEvent], None]] = None,
        rules_config: Optional[MCPHoneypotConfig] = None,
        honeypot_id: str = "mcp-default",
    ):
        """Initialize MCP honeypot.

        Args:
            config: Global Honeypot configuration
            on_event: Callback for attack events
            rules_config: Specific MCP configuration (custom patterns, etc.)
            honeypot_id: Identifier for this specific guard instance
        """
        self.config = config or get_honeypot_config()
        self.rules_config = rules_config
        self.honeypot_id = honeypot_id
        self._on_event = on_event
        self._compiled_patterns: Dict[str, List[re.Pattern]] = {}
        self._detection_count = 0
        self._session_history: Dict[str, List[Dict[str, Any]]] = {}

        # Compile patterns
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Compile regex patterns for performance."""
        # Start with default patterns
        patterns_to_compile = INJECTION_PATTERNS.copy()

        # Apply specific configuration if exists
        if self.rules_config:
            # Add custom rules
            for rule in self.rules_config.custom_rules:
                if rule.category:
                    cat = rule.category
                    if cat not in patterns_to_compile:
                        patterns_to_compile[cat] = []
                    patterns_to_compile[cat].append(rule.regex)
                    # Note: We should handle custom severity mapping here ideally,
                    # but PATTERN_SEVERITY is global.
                    # For now, we rely on the rule definitions.

            # Remove ignored patterns (allow-list)
            # This is tricky as we need to match pattern names or content?
            # Assuming ignored_patterns refers to categories for now for simplicity,
            # or we filter regexes by exact string match if possible.
            # Implemented: Filter by category name
            for ignored in self.rules_config.ignored_patterns:
                if ignored in patterns_to_compile:
                    del patterns_to_compile[ignored]

        for category, patterns in patterns_to_compile.items():
            self._compiled_patterns[category] = [re.compile(p) for p in patterns]

    async def analyze_prompt(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        source: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Analyze a prompt for injection attacks.

        Args:
            prompt: The LLM prompt to analyze
            session_id: Optional session ID for tracking
            source: Source of the prompt (user, api, etc.)
            metadata: Additional metadata

        Returns:
            Analysis result with detected patterns and severity
        """
        if not session_id:
            session_id = f"mcp-{uuid4().hex[:8]}"

        # Track in session history
        if session_id not in self._session_history:
            self._session_history[session_id] = []

        detected = self.detect_injection(prompt)
        result = {
            "session_id": session_id,
            "is_safe": len(detected["patterns"]) == 0,
            "detected_categories": detected["categories"],
            "detected_patterns": detected["patterns"],
            "severity": detected["severity"].value,
            "confidence": detected["confidence"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # Add to history
        self._session_history[session_id].append(
            {
                "prompt_hash": hash(prompt[:100]),
                "is_safe": result["is_safe"],
                "timestamp": result["timestamp"],
            }
        )

        # If attack detected, create event and emit
        if not result["is_safe"]:
            self._detection_count += 1
            event = self._create_attack_event(
                session_id=session_id,
                prompt=prompt,
                detected=detected,
                source=source,
                metadata=metadata,
            )

            if self._on_event:
                await self._on_event(event)

            # Emit to EventBus
            await emit_honeypot_event(
                HoneypotEvents.ATTACK_HIGH_SEVERITY
                if detected["severity"]
                in (AttackSeverity.HIGH, AttackSeverity.CRITICAL)
                else HoneypotEvents.ATTACK_DETECTED,
                {
                    "event_id": event.event_id,
                    "session_id": session_id,
                    "attack_type": "prompt_injection",
                    "categories": detected["categories"],
                    "severity": detected["severity"].value,
                    "source": source,
                },
            )

            logger.warning(
                f"Prompt injection detected: {detected['categories']} "
                f"(severity: {detected['severity'].value})"
            )

        return result

    def detect_injection(self, prompt: str) -> Dict[str, Any]:
        """Detect injection patterns in prompt.

        Args:
            prompt: Prompt to analyze

        Returns:
            Detection result
        """
        detected_patterns = []
        detected_categories = []
        max_severity = AttackSeverity.INFO

        for category, patterns in self._compiled_patterns.items():
            for pattern in patterns:
                if pattern.search(prompt):
                    detected_patterns.append(pattern.pattern)
                    if category not in detected_categories:
                        detected_categories.append(category)

                    severity = PATTERN_SEVERITY.get(category, AttackSeverity.MEDIUM)
                    if self._severity_rank(severity) > self._severity_rank(
                        max_severity
                    ):
                        max_severity = severity

        # Calculate confidence
        confidence = 0.0
        if detected_patterns:
            base = 0.6
            confidence = min(base + (len(detected_patterns) * 0.1), 0.99)

        return {
            "patterns": detected_patterns,
            "categories": detected_categories,
            "severity": max_severity,
            "confidence": confidence,
        }

    def _severity_rank(self, severity: AttackSeverity) -> int:
        """Get numeric rank for severity."""
        ranks = {
            AttackSeverity.INFO: 0,
            AttackSeverity.LOW: 1,
            AttackSeverity.MEDIUM: 2,
            AttackSeverity.HIGH: 3,
            AttackSeverity.CRITICAL: 4,
        }
        return ranks.get(severity, 0)

    def _create_attack_event(
        self,
        session_id: str,
        prompt: str,
        detected: Dict[str, Any],
        source: str,
        metadata: Optional[Dict[str, Any]],
    ) -> AttackEvent:
        """Create attack event for injection."""
        return AttackEvent(
            event_id=f"mcp-evt-{uuid4().hex[:8]}",
            session_id=session_id,
            protocol=HoneypotProtocol.TCP,  # MCP uses TCP under the hood
            timestamp=datetime.now(timezone.utc),
            source_ip=metadata.get("ip", "127.0.0.1") if metadata else "127.0.0.1",
            source_port=0,
            event_type="prompt_injection",
            raw_data=prompt[:4096],  # Limit stored size
            detected_patterns=detected["patterns"],
            category=AttackCategory.COMMAND_INJECTION,  # Closest category
            severity=detected["severity"],
            ai_classification=", ".join(detected["categories"]),
        )

    def get_stats(self) -> Dict[str, Any]:
        """Get detection statistics."""
        return {
            "total_detections": self._detection_count,
            "active_sessions": len(self._session_history),
            "pattern_categories": list(INJECTION_PATTERNS.keys()),
        }

    def check_prompt_safety(self, prompt: str) -> Tuple[bool, str]:
        """Quick check if prompt is safe.

        Args:
            prompt: Prompt to check

        Returns:
            Tuple of (is_safe, reason)
        """
        result = self.detect_injection(prompt)
        if result["patterns"]:
            return False, f"Detected: {', '.join(result['categories'])}"
        return True, "No injection patterns detected"


def create_llm_guard(
    config: Optional[HoneypotConfig] = None, honeypot_id: Optional[str] = None
) -> MCPHoneypot:
    """Create an MCP honeypot instance for LLM protection.

    Args:
        config: Optional global configuration
        honeypot_id: Optional ID of a defined honeypot to load specific rules

    Returns:
        MCPHoneypot instance
    """
    rules_config = None
    if honeypot_id:
        try:
            from ..honeypot_loader import get_registry

            registry = get_registry()
            definition = registry.get(honeypot_id)
            if definition and definition.protocol == HoneypotProtocol.MCP:
                rules_config = definition.mcp_config
        except Exception as e:
            logger.warning(f"Failed to load MCP rules for {honeypot_id}: {e}")

    return MCPHoneypot(
        config=config,
        rules_config=rules_config,
        honeypot_id=honeypot_id or "mcp-default",
    )
