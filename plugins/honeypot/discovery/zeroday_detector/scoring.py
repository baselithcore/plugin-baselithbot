"""Zero-Day Detector Scoring."""

import re

from .constants import SHELLCODE_PATTERNS
from .signatures import has_obfuscation
from .utils import calculate_entropy


def calculate_novelty_score(
    payload: str,
    attack_vector: str,
    pattern_matches: int,
) -> float:
    """Calculate how novel/unknown this payload is."""
    novelty = 1.0

    # Reduce novelty if matches known patterns
    if pattern_matches > 0:
        novelty -= min(0.3, pattern_matches * 0.1)

    # Check for shellcode (increases novelty for sophistication)
    shellcode_found = False
    for pattern in SHELLCODE_PATTERNS:
        if re.search(pattern, payload):
            shellcode_found = True
            break

    if shellcode_found:
        novelty += 0.1

    # High entropy payloads are more suspicious
    entropy = calculate_entropy(payload)
    if entropy > 5.0:  # High entropy
        novelty += 0.1
    elif entropy < 3.0:  # Very low entropy (simple)
        novelty -= 0.1

    # Unknown attack vector increases novelty
    if attack_vector == "unknown":
        novelty += 0.2

    # Check for obfuscation indicators
    if has_obfuscation(payload):
        novelty += 0.15

    return max(0.0, min(1.0, novelty))


def estimate_severity(payload: str, attack_vector: str) -> str:
    """Estimate severity of potential exploit."""
    # Start with base severity by attack type
    severity_map = {
        "rce": "critical",
        "command_injection": "critical",
        "deserialization": "critical",
        "buffer_overflow": "high",
        "sql_injection": "high",
        "ssrf": "high",
        "path_traversal": "medium",
        "xss": "medium",
        "unknown": "medium",
    }

    base_severity = severity_map.get(attack_vector, "medium")

    # Elevate if shellcode detected
    for pattern in SHELLCODE_PATTERNS:
        if re.search(pattern, payload):
            if base_severity == "high":
                return "critical"
            elif base_severity == "medium":
                return "high"

    return base_severity


def calculate_confidence(
    occurrence_count: int,
    unique_ips: int,
    novelty_score: float,
    attack_vector: str,
) -> float:
    """Calculate confidence in zero-day classification."""
    confidence = 0.5

    # More occurrences = more confidence
    if occurrence_count >= 5:
        confidence += 0.15
    elif occurrence_count >= 3:
        confidence += 0.1

    # Multiple source IPs = coordinated/widespread
    if unique_ips >= 3:
        confidence += 0.1

    # Higher novelty = higher confidence it's unknown
    confidence += novelty_score * 0.2

    # Known attack vector = higher confidence in classification
    if attack_vector != "unknown":
        confidence += 0.1

    return min(1.0, confidence)
