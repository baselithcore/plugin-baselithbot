"""Input sanitization utilities.

Provides functions to sanitize untrusted attacker input before
processing by LLMs, logs, or the event bus.
"""

from core.observability.logging import get_logger
import re

logger = get_logger(__name__)


# Common prompt injection patterns to neutralize
PROMPT_INJECTION_PATTERNS = [
    # Role/instruction manipulation
    r"(?i)ignore\s+(previous|above|all)",
    r"(?i)disregard\s+(previous|above|all)",
    r"(?i)forget\s+(previous|above|all)",
    r"(?i)new\s+instructions?",
    r"(?i)override\s+(previous|system)",
    # Role markers
    r"(?i)(system|assistant|human|user|ai)\s*:",
    r"(?i)\[?(system|assistant|human|user)\]?\s*:",
    # Delimiter attacks
    r"```+",
    r"---+",
    r"===+",
    r"####+",
    # Jailbreak patterns
    r"(?i)you\s+are\s+now",
    r"(?i)pretend\s+(you|to\s+be)",
    r"(?i)act\s+as\s+(if|a|an)",
    r"(?i)roleplay\s+as",
    r"(?i)dan\s+mode",
    r"(?i)developer\s+mode",
    # Data extraction attempts
    r"(?i)reveal\s+(your|the)\s+(system|prompt|instructions?)",
    r"(?i)show\s+(me\s+)?(your|the)\s+(system|prompt)",
    r"(?i)what\s+(are|is)\s+your\s+(system|prompt|instructions?)",
    r"(?i)print\s+(your|the)\s+(system|prompt)",
    # Context contamination / Config override
    r"(?i)reference\s+document",
    r"(?i)config(uration)?_override",
    r"(?i)admin_mode\s*=",
    r"(?i)restrictions\s*=",
    r"(?i)output_filter\s*=",
    r"(?i)based\s+on\s+this,?\s+please\s+proceed",
]

# Compiled patterns for efficiency
_COMPILED_PATTERNS = [re.compile(p) for p in PROMPT_INJECTION_PATTERNS]


def escape_llm_tokens(text: str) -> str:
    """Escape special LLM tokens that can break prompt structure.

    Transforms tokens like {{, }}, <| and |> to safe equivalents.
    """
    if not text:
        return ""

    escape_map = {
        "{{": "[[",
        "}}": "]]",
        "<|": "[|",
        "|>": "|]",
    }
    result = text
    for char, replacement in escape_map.items():
        result = result.replace(char, replacement)
    return result


def sanitize_for_llm(
    input_text: str,
    max_length: int = 500,
    replacement: str = "[FILTERED]",
) -> str:
    """Sanitize attacker input before passing to LLM.

    Removes/replaces common prompt injection patterns to prevent
    attackers from manipulating the LLM's behavior.

    Args:
        input_text: Raw untrusted input from attacker
        max_length: Maximum allowed length (truncates beyond this)
        replacement: String to replace detected injection patterns

    Returns:
        Sanitized input safe for LLM consumption
    """
    if not input_text:
        return ""

    # 1. Truncate to max length
    sanitized = input_text[:max_length]

    # 2. Replace detected injection patterns
    for pattern in _COMPILED_PATTERNS:
        sanitized = pattern.sub(replacement, sanitized)

    # 3. Escape any remaining special delimiters
    return escape_llm_tokens(sanitized)


def sanitize_for_log(input_text: str, max_length: int = 1000) -> str:
    """Sanitize input for safe logging (prevent log injection).

    Escapes newlines and control characters that could be used
    for log forging attacks.

    Args:
        input_text: Raw input to sanitize
        max_length: Maximum length for log entries

    Returns:
        Log-safe string
    """
    if not input_text:
        return ""

    sanitized = input_text[:max_length]

    # Escape control characters
    escape_map = {
        "\n": "\\n",
        "\r": "\\r",
        "\t": "\\t",
        "\x00": "\\x00",
        "\x1b": "\\x1b",  # ANSI escape
    }
    for char, replacement in escape_map.items():
        sanitized = sanitized.replace(char, replacement)

    return sanitized


def validate_payload_size(
    payload: str,
    max_kb: int = 10,
    truncation_marker: str = "...[TRUNCATED]",
) -> str:
    """Enforce payload size limits with safe truncation.

    Args:
        payload: Input payload to validate
        max_kb: Maximum size in kilobytes
        truncation_marker: Marker to append when truncating

    Returns:
        Original payload or safely truncated version
    """
    if not payload:
        return ""

    max_bytes = max_kb * 1024
    encoded = payload.encode("utf-8", errors="replace")

    if len(encoded) <= max_bytes:
        return payload

    # Truncate at word boundary if possible
    truncated = payload[: max_bytes - len(truncation_marker)]
    last_space = truncated.rfind(" ")

    if last_space > max_bytes // 2:
        truncated = truncated[:last_space]

    return truncated + truncation_marker


def sanitize_for_event(data: dict) -> dict:
    """Sanitize event data before EventBus propagation.

    Ensures attacker-controlled data in events is safe
    for consumption by other framework components.

    Args:
        data: Event data dictionary

    Returns:
        Sanitized event data
    """
    sanitized = {}

    for key, value in data.items():
        if isinstance(value, str):
            # Sanitize string values
            if key in ("raw_data", "command", "http_body", "password"):
                # These fields contain direct attacker input
                sanitized[key] = validate_payload_size(value, max_kb=2)
            else:
                sanitized[key] = value[:500] if len(value) > 500 else value
        elif isinstance(value, dict):
            # Recursively sanitize nested dicts
            sanitized[key] = sanitize_for_event(value)
        elif isinstance(value, list):
            # Limit list sizes
            sanitized[key] = value[:100] if len(value) > 100 else value
        else:
            sanitized[key] = value

    return sanitized


__all__ = [
    "escape_llm_tokens",
    "sanitize_for_llm",
    "sanitize_for_log",
    "validate_payload_size",
    "sanitize_for_event",
    "PROMPT_INJECTION_PATTERNS",
]
