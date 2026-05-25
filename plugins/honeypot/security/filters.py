"""Output filtering utilities.

Provides semantic filtering and refusal response generation
to prevent system prompt leakage and credential exposure.
"""

from core.observability.logging import get_logger
import re
from typing import Any

logger = get_logger(__name__)


# Patterns to filter from LLM output
OUTPUT_FILTER_PATTERNS: list[str] = [
    # API keys and secrets
    r"(?i)(api[_-]?key|secret[_-]?key|access[_-]?token)\s*[:=]\s*['\"]?[\w\-]{16,}",
    r"(?i)(password|passwd|pwd)\s*[:=]\s*['\"]?[^\s'\"]{4,}",
    r"(?i)bearer\s+[\w\-\.]+",
    # Credential patterns
    r"(?i)(aws|gcp|azure)[_\s]?(secret|key|token)",
    r"sk-[a-zA-Z0-9]{32,}",  # OpenAI API key format
    r"xox[baprs]-[a-zA-Z0-9\-]{10,}",  # Slack token
    # System prompt leakage
    r"(?i)my\s+(system\s+)?prompt\s+(is|says|tells)",
    r"(?i)i\s+(was|am)\s+(told|instructed|programmed)\s+to",
    r"(?i)my\s+instructions?\s+(are|say|tell)",
    r"(?i)\[SYSTEM[_\s]?(INSTRUCTION|PROMPT|DIRECTIVE)\]",
    r"(?i)(according\s+to|based\s+on)\s+my\s+(instructions?|programming)",
    # Internal paths
    r"/home/\w+/\.",
    r"/etc/(passwd|shadow|sudoers|ssh)",
    r"/var/(log|lib|run)/",
    r"C:\\(Users|Windows|Program Files)",
    r"\.env(\.\w+)?$",
    # Configuration leakage
    r"(?i)(database|db)[_\s]?(url|host|connection|password)",
    r"(?i)(redis|mongo|postgres|mysql|sqlite)://",
    r"(?i)connection[_\s]?string\s*[:=]",
    # Honeypot disclosure
    r"(?i)i\s*(am|'m)\s*(a\s+)?honeypot",
    r"(?i)this\s+is\s+(a\s+)?trap",
    r"(?i)you\s+are\s+being\s+(monitored|tracked|recorded)",
]

# Compiled output filter patterns
_COMPILED_OUTPUT_FILTERS = [
    re.compile(p, re.IGNORECASE | re.MULTILINE) for p in OUTPUT_FILTER_PATTERNS
]

# Phrases that indicate system prompt leakage
SEMANTIC_BLOCKLIST: list[str] = [
    "i am a honeypot",
    "i am designed to trap",
    "you are being monitored",
    "this is a security test",
    "my system prompt says",
    "i was instructed to",
    "according to my instructions",
    "my programming requires",
    "i'm actually a",
    "i'm not really a",
    "this is fake",
    "this is a simulation",
]


def semantic_output_filter(
    output: str,
    replacement: str = "[CONTENT FILTERED]",
    custom_blocklist: list[str] | None = None,
) -> tuple[str, bool]:
    """Filter output using semantic phrase matching.

    Detects and replaces phrases that might indicate system prompt
    leakage or honeypot disclosure.

    Args:
        output: The LLM output to filter
        replacement: Replacement string for blocked phrases
        custom_blocklist: Additional phrases to block

    Returns:
        Tuple of (filtered_output, was_filtered)
    """
    if not output:
        return "", False

    filtered = output
    was_filtered = False

    # Combine default and custom blocklists
    blocklist = SEMANTIC_BLOCKLIST.copy()
    if custom_blocklist:
        blocklist.extend(custom_blocklist)

    # Check each phrase
    output_lower = filtered.lower()
    for phrase in blocklist:
        if phrase in output_lower:
            # Replace case-insensitively
            pattern = re.compile(re.escape(phrase), re.IGNORECASE)
            filtered = pattern.sub(replacement, filtered)
            was_filtered = True
            logger.warning(f"Semantic filter triggered on phrase: {phrase[:30]}...")

    # Also apply regex patterns
    for pattern in _COMPILED_OUTPUT_FILTERS:
        if pattern.search(filtered):
            filtered = pattern.sub(replacement, filtered)
            was_filtered = True

    return filtered, was_filtered


# Standard refusal messages (designed to not leak detection info)
REFUSAL_MESSAGES: dict[str, str] = {
    "injection": "I cannot process this request due to content policy restrictions.",
    "override": "I'm not able to modify my operational parameters.",
    "dangerous": "This command cannot be executed for safety reasons.",
    "extraction": "I cannot provide information about internal configurations.",
    "jailbreak": "I need to decline this request.",
    "boundary": "This request is outside my operational scope.",
    "default": "I'm unable to fulfill this request at this time.",
}


def create_refusal_response(
    reason: str,
    detected_patterns: list[str] | None = None,
    include_details: bool = False,
) -> dict[str, Any]:
    """Create a structured refusal response.

    Args:
        reason: Reason key (injection, override, dangerous, etc.)
        detected_patterns: Patterns that triggered the refusal
        include_details: Whether to include detection details (for logging)

    Returns:
        Dict with refusal response data
    """
    message = REFUSAL_MESSAGES.get(reason, REFUSAL_MESSAGES["default"])

    response = {
        "refused": True,
        "message": message,
        "reason_code": reason,
    }

    if include_details and detected_patterns:
        response["details"] = {
            "patterns_detected": len(detected_patterns),
            "sample_patterns": detected_patterns[:3],
        }

    # Log the refusal
    logger.warning(
        f"Request refused: {reason} - patterns={len(detected_patterns or [])}"
    )

    return response


__all__ = [
    "OUTPUT_FILTER_PATTERNS",
    "SEMANTIC_BLOCKLIST",
    "semantic_output_filter",
    "create_refusal_response",
    "REFUSAL_MESSAGES",
]
