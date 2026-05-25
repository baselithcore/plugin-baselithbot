"""Zero-Day Detector Signatures."""

import re
from typing import Dict, List, Optional, Tuple

from .constants import (
    DEFAULT_CVE_PATTERNS,
    KNOWN_PATTERNS,
    OBFUSCATION_INDICATORS,
)


def detect_attack_vector(payload: str) -> Tuple[str, int]:
    """Detect the type of attack and count pattern matches."""
    best_vector = "unknown"
    max_matches = 0

    for vector, patterns in KNOWN_PATTERNS.items():
        matches = 0
        for pattern in patterns:
            if re.search(pattern, payload):
                matches += 1
        if matches > max_matches:
            max_matches = matches
            best_vector = vector

    return best_vector, max_matches


def check_cve_matches(
    payload: str, known_cve_patterns: Optional[Dict[str, List[str]]] = None
) -> List[str]:
    """Check if payload matches known CVE patterns."""
    matches = []

    # Merge with user-provided patterns
    all_patterns = {**DEFAULT_CVE_PATTERNS, **(known_cve_patterns or {})}

    for cve, patterns in all_patterns.items():
        for pattern in patterns:
            if re.search(pattern, payload):
                matches.append(cve)
                break

    return list(set(matches))


def has_obfuscation(payload: str) -> bool:
    """Check for common obfuscation techniques."""
    for pattern in OBFUSCATION_INDICATORS:
        if re.search(pattern, payload):
            return True
    return False
