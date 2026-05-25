"""Security utilities for honeypot plugin.

Provides input sanitization, prompt injection protection,
and secure data handling for untrusted attacker input.

This module implements defense-in-depth strategies to prevent
honeypot exploits from compromising the core framework.

The security module is organized into:
- sanitizers: Input sanitization functions
- detectors: Threat detection and scoring
- filters: Output filtering and refusal responses
"""

# Re-export all public APIs for backward compatibility
from .detectors import (
    DANGEROUS_COMMAND_PATTERNS,
    SafetyGuardrail,
    calculate_injection_score,
    detect_injection_attempt,
)
from .filters import (
    OUTPUT_FILTER_PATTERNS,
    REFUSAL_MESSAGES,
    SEMANTIC_BLOCKLIST,
    create_refusal_response,
    semantic_output_filter,
)
from .sanitizers import (
    PROMPT_INJECTION_PATTERNS,
    escape_llm_tokens,
    sanitize_for_event,
    sanitize_for_llm,
    sanitize_for_log,
    validate_payload_size,
)

__all__ = [
    # Sanitizers
    "sanitize_for_llm",
    "escape_llm_tokens",
    "sanitize_for_log",
    "validate_payload_size",
    "sanitize_for_event",
    "PROMPT_INJECTION_PATTERNS",
    # Detectors
    "detect_injection_attempt",
    "calculate_injection_score",
    "SafetyGuardrail",
    "DANGEROUS_COMMAND_PATTERNS",
    # Filters
    "OUTPUT_FILTER_PATTERNS",
    "SEMANTIC_BLOCKLIST",
    "semantic_output_filter",
    "create_refusal_response",
    "REFUSAL_MESSAGES",
]
