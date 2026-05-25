"""Threat detection utilities.

Provides functions to detect prompt injection attempts,
dangerous commands, and calculate risk scores.
"""

from core.observability.logging import get_logger
import re

from .sanitizers import PROMPT_INJECTION_PATTERNS

logger = get_logger(__name__)


# Dangerous system command patterns (to prevent accidental local execution)
DANGEROUS_COMMAND_PATTERNS = [
    r"rm\s+-rf",
    r"mkfifo",
    r"nc\s+.*-e",
    r">\s*/dev/tcp",
    r"wget\s+.*\|\s*sh",
    r"curl\s+.*\|\s*bash",
    r"chmod\s+\+x",
    r"cat\s+/etc/(passwd|shadow)",
    r"sudo\s+",
    r":\(\)\{ :\|:& \};:",  # Fork bomb
]

_COMPILED_DANGEROUS = [re.compile(p) for p in DANGEROUS_COMMAND_PATTERNS]
_COMPILED_PATTERNS = [re.compile(p) for p in PROMPT_INJECTION_PATTERNS]


def detect_injection_attempt(input_text: str) -> tuple[bool, list[str]]:
    """Detect if input contains prompt injection attempts.

    Useful for alerting/logging without modifying the input.

    Args:
        input_text: Input to analyze

    Returns:
        Tuple of (is_suspicious, detected_patterns)
    """
    if not input_text:
        return False, []

    detected = []
    for i, pattern in enumerate(_COMPILED_PATTERNS):
        if pattern.search(input_text):
            detected.append(PROMPT_INJECTION_PATTERNS[i])

    return len(detected) > 0, detected


def calculate_injection_score(input_text: str) -> float:
    """Calculate a normalized injection risk score.

    Args:
        input_text: The input to analyze

    Returns:
        Score from 0.0 (safe) to 1.0 (definitely malicious)
    """
    if not input_text:
        return 0.0

    score = 0.0

    # Check prompt injection patterns
    matches = 0
    for pattern in _COMPILED_PATTERNS:
        if pattern.search(input_text):
            matches += 1

    # Score based on number of patterns matched
    if matches > 0:
        score = min(1.0, 0.3 + (matches * 0.15))

    # Check for structural manipulation attempts
    structural_indicators = [
        "```",  # Code blocks
        "---",  # Dividers
        "===",  # Alternative dividers
        "##",  # Headers
        "[SYSTEM",  # System markers
        "<|",  # Special tokens
    ]

    for indicator in structural_indicators:
        if indicator in input_text:
            score = min(1.0, score + 0.1)

    # Check input length (very long inputs are suspicious)
    if len(input_text) > 1000:
        score = min(1.0, score + 0.1)
    if len(input_text) > 5000:
        score = min(1.0, score + 0.2)

    return round(score, 2)


class SafetyGuardrail:
    """Security guardrail to prevent dangerous local execution.

    Acts as a final check before any command execution or sensitive
    operation to ensure the agent doesn't destructively modify the host.
    """

    def __init__(self, strict_mode: bool = True):
        self.strict_mode = strict_mode

    def validate_command(self, command: str) -> bool:
        """Check if a command is safe to execute.

        Args:
            command: The command string to check

        Returns:
            True if safe, False if dangerous pattern detected
        """
        if not command:
            return True

        # Check against dangerous patterns
        for pattern in _COMPILED_DANGEROUS:
            if pattern.search(command):
                logger.warning(
                    f"Blocked dangerous command execution attempt: {command[:50]}..."
                )
                return False

        return True

    def validate_path(self, path: str, allowed_dirs: list[str]) -> bool:
        """Check if a file path is within allowed directories.

        Args:
            path: The file path to check
            allowed_dirs: List of allowed directory prefixes

        Returns:
            True if path is safe
        """
        if not path:
            return False

        import os

        # Resolve absolute path to prevent traversal attacks
        try:
            abs_path = os.path.abspath(path)
            for allowed in allowed_dirs:
                if abs_path.startswith(os.path.abspath(allowed)):
                    return True
        except Exception:
            return False

        return False


__all__ = [
    "detect_injection_attempt",
    "calculate_injection_score",
    "SafetyGuardrail",
    "DANGEROUS_COMMAND_PATTERNS",
]
