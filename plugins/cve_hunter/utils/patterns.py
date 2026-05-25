"""CVE Hunter Pattern Utilities.

Common patterns and utility functions for vulnerability discovery.
"""

import re
from typing import List, Optional

try:
    from ..models import CVESeverity
except ImportError:
    from models import CVESeverity  # type: ignore[no-redef]


# Patterns indicating potential vulnerabilities
VULNERABILITY_PATTERNS = [
    "buffer overflow",
    "sql injection",
    "cross-site scripting",
    "xss",
    "remote code execution",
    "rce",
    "privilege escalation",
    "authentication bypass",
    "path traversal",
    "directory traversal",
    "command injection",
    "deserialization",
    "ssrf",
    "xxe",
    "race condition",
    "use after free",
    "heap overflow",
    "stack overflow",
    "format string",
    "null pointer",
    "memory corruption",
    "integer overflow",
]


def extract_context(text: str, pattern: str, window: int = 100) -> str:
    """Extract context around a pattern match.

    Args:
        text: The text to search in
        pattern: The pattern to find (case-insensitive)
        window: Number of characters of context to include

    Returns:
        Extracted context string, or empty if not found
    """
    text_lower = text.lower()
    pos = text_lower.find(pattern.lower())
    if pos == -1:
        return ""

    start = max(0, pos - window)
    end = min(len(text), pos + len(pattern) + window)
    return text[start:end]


def pattern_to_severity(pattern: str) -> CVESeverity:
    """Map vulnerability pattern to severity.

    Args:
        pattern: The vulnerability pattern

    Returns:
        CVESeverity level
    """
    critical_patterns = [
        "remote code execution",
        "rce",
        "command injection",
        "authentication bypass",
    ]
    high_patterns = [
        "sql injection",
        "buffer overflow",
        "privilege escalation",
        "deserialization",
        "ssrf",
    ]

    if pattern.lower() in critical_patterns:
        return CVESeverity.CRITICAL
    elif pattern.lower() in high_patterns:
        return CVESeverity.HIGH
    return CVESeverity.MEDIUM


def pattern_to_cwe(pattern: str) -> List[str]:
    """Map vulnerability pattern to CWE IDs.

    Args:
        pattern: The vulnerability pattern

    Returns:
        List of associated CWE IDs
    """
    mapping = {
        "sql injection": ["CWE-89"],
        "cross-site scripting": ["CWE-79"],
        "xss": ["CWE-79"],
        "buffer overflow": ["CWE-120", "CWE-119"],
        "command injection": ["CWE-78"],
        "path traversal": ["CWE-22"],
        "directory traversal": ["CWE-22"],
        "authentication bypass": ["CWE-287"],
        "ssrf": ["CWE-918"],
        "xxe": ["CWE-611"],
        "deserialization": ["CWE-502"],
    }
    return mapping.get(pattern.lower(), [])


def extract_cwe_ids(pattern: str, rule_id: Optional[str] = None) -> List[str]:
    """Extract CWE IDs from pattern/rule or map known patterns.

    Args:
        pattern: Vulnerability pattern name
        rule_id: Optional rule identifier (e.g. from semgrep)

    Returns:
        Sorted list of unique CWE IDs
    """
    cwe_ids = set(pattern_to_cwe(pattern))
    for value in [pattern, rule_id or ""]:
        for match in re.findall(r"CWE-\d+", value, flags=re.IGNORECASE):
            cwe_ids.add(match.upper())
    return sorted(cwe_ids)


def is_code_file(path: str) -> bool:
    """Check if file is a code file.

    Args:
        path: File path

    Returns:
        True if file extension matches known code types
    """
    code_extensions = {
        ".py",
        ".js",
        ".ts",
        ".java",
        ".c",
        ".cpp",
        ".h",
        ".go",
        ".rs",
        ".rb",
        ".php",
        ".cs",
        ".swift",
        ".kt",
    }
    return any(path.endswith(ext) for ext in code_extensions)
