"""Threat Intel Scoring."""

from typing import Set


def calculate_confidence(
    ip_count: int,
    hash_count: int,
    total_events: int,
) -> float:
    """Calculate confidence in the intel."""
    if total_events == 0:
        return 0.0

    # Base confidence
    confidence = 0.5

    # More data = higher confidence
    if total_events >= 100:
        confidence += 0.2
    elif total_events >= 50:
        confidence += 0.1

    # More unique IOCs = higher confidence
    if ip_count >= 10:
        confidence += 0.15
    if hash_count >= 5:
        confidence += 0.1

    return min(1.0, confidence)


def determine_severity(attack_types: Set[str]) -> str:
    """Determine overall severity from attack types."""
    high_severity = {"rce", "command_injection", "exploitation"}
    medium_severity = {"sql_injection", "brute_force", "scanning"}

    attack_lower = {t.lower() for t in attack_types}

    if attack_lower & high_severity:
        return "high"
    elif attack_lower & medium_severity:
        return "medium"
    return "low"
