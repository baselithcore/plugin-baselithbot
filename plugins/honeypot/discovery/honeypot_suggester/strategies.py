"""Suggestion Strategy Utilities.

Helper functions for generating honeypot configurations based on
different types of attack patterns and anomalies.
"""

import re
from typing import Any, Dict, List, Set, Tuple

from .models import SuggestedProtocol, SuggestionPriority, SuggestionType


# Common ports by protocol
PROTOCOL_PORTS: Dict[str, List[int]] = {
    "http": [80, 443, 8080, 8443, 8000, 3000],
    "ssh": [22, 2222, 22222],
    "tcp": list(range(1024, 65536)),  # Dynamic
}

# Attack vector to protocol mapping
VECTOR_TO_PROTOCOL: Dict[str, SuggestedProtocol] = {
    "sql_injection": SuggestedProtocol.HTTP,
    "command_injection": SuggestedProtocol.HTTP,
    "path_traversal": SuggestedProtocol.HTTP,
    "xss": SuggestedProtocol.HTTP,
    "rce": SuggestedProtocol.HTTP,
    "deserialization": SuggestedProtocol.HTTP,
    "lfi": SuggestedProtocol.HTTP,
    "rfi": SuggestedProtocol.HTTP,
    "ssrf": SuggestedProtocol.HTTP,
    "xxe": SuggestedProtocol.HTTP,
    "auth_bypass": SuggestedProtocol.HTTP,
    "buffer_overflow": SuggestedProtocol.TCP,
    "brute_force": SuggestedProtocol.SSH,
    "credential_stuffing": SuggestedProtocol.SSH,
    "shell_injection": SuggestedProtocol.SSH,
}

# Keywords that indicate specific service targets
SERVICE_KEYWORDS: Dict[str, Tuple[str, int]] = {
    "wordpress": ("http", 80),
    "wp-": ("http", 80),
    "phpmyadmin": ("http", 80),
    "jenkins": ("http", 8080),
    "grafana": ("http", 3000),
    "elasticsearch": ("http", 9200),
    "redis": ("tcp", 6379),
    "mysql": ("tcp", 3306),
    "postgres": ("tcp", 5432),
    "mongo": ("tcp", 27017),
    "rabbitmq": ("tcp", 5672),
    "kafka": ("tcp", 9092),
    "docker": ("http", 2375),
    "kubernetes": ("http", 6443),
    "ssh": ("ssh", 22),
    "ftp": ("tcp", 21),
    "telnet": ("tcp", 23),
    "smtp": ("tcp", 25),
    "dns": ("tcp", 53),
}


def determine_protocol_from_vector(
    attack_vector: str, payload_preview: str = ""
) -> Tuple[SuggestedProtocol, int]:
    """Determine suggested protocol and port from attack vector.

    Args:
        attack_vector: The detected attack vector type
        payload_preview: Optional payload preview for additional hints

    Returns:
        Tuple of (protocol, port)
    """
    # Check for service-specific keywords in payload
    payload_lower = payload_preview.lower()
    for keyword, (proto, port) in SERVICE_KEYWORDS.items():
        if keyword in payload_lower:
            return SuggestedProtocol(proto), port

    # Fall back to vector-based mapping
    protocol = VECTOR_TO_PROTOCOL.get(attack_vector, SuggestedProtocol.HTTP)

    # Select appropriate port
    if protocol == SuggestedProtocol.HTTP:
        port = 8080  # Non-standard to avoid conflicts
    elif protocol == SuggestedProtocol.SSH:
        port = 2222  # Non-standard SSH
    else:
        port = 9999  # Generic TCP

    return protocol, port


def calculate_priority(
    novelty_score: float, confidence: float, occurrence_count: int
) -> SuggestionPriority:
    """Calculate suggestion priority based on metrics.

    Args:
        novelty_score: How novel the pattern is (0-1)
        confidence: Detection confidence (0-1)
        occurrence_count: How many times pattern was seen

    Returns:
        Priority level
    """
    # Combined score
    score = (
        (novelty_score * 0.4)
        + (confidence * 0.3)
        + (min(occurrence_count, 10) / 10 * 0.3)
    )

    if score >= 0.8:
        return SuggestionPriority.CRITICAL
    elif score >= 0.6:
        return SuggestionPriority.HIGH
    elif score >= 0.4:
        return SuggestionPriority.MEDIUM
    else:
        return SuggestionPriority.LOW


def estimate_catch_rate(
    occurrence_count: int, source_ips_count: int, novelty_score: float
) -> float:
    """Estimate what percentage of similar attacks the honeypot would catch.

    Args:
        occurrence_count: Number of times pattern was seen
        source_ips_count: Number of unique source IPs
        novelty_score: Novelty of the pattern

    Returns:
        Estimated catch rate (0-1)
    """
    # Base rate from occurrence frequency
    base_rate = min(occurrence_count / 100, 0.5)  # Cap at 50% base

    # Boost from multiple sources (indicates widespread attack)
    source_boost = min(source_ips_count / 20, 0.3)  # Cap at 30% boost

    # Novelty penalty (very novel = might be one-off)
    novelty_penalty = novelty_score * 0.1  # Up to 10% penalty

    return min(base_rate + source_boost - novelty_penalty, 0.95)


def generate_detection_patterns(
    payload_preview: str, attack_vector: str, indicators: Dict[str, Any]
) -> List[Dict[str, str]]:
    """Generate detection patterns for the suggested honeypot.

    Args:
        payload_preview: Sample payload to analyze
        attack_vector: Detected attack vector
        indicators: Extracted indicators from the payload

    Returns:
        List of detection pattern configurations
    """
    patterns: List[Dict[str, str]] = []

    # Add patterns based on attack vector
    vector_patterns = {
        "command_injection": [
            {
                "name": "command_injection_basic",
                "regex": r"[;&|`$]|\bsh\b|\bbash\b|\bcmd\b",
                "severity": "high",
                "category": "command_injection",
            },
        ],
        "sql_injection": [
            {
                "name": "sql_injection_basic",
                "regex": r"(?i)(union|select|insert|update|delete|drop|exec)",
                "severity": "high",
                "category": "sql_injection",
            },
        ],
        "path_traversal": [
            {
                "name": "path_traversal",
                "regex": r"\.\./|\.\.\\|%2e%2e",
                "severity": "high",
                "category": "path_traversal",
            },
        ],
        "rce": [
            {
                "name": "rce_attempt",
                "regex": r"eval\(|exec\(|system\(|passthru\(|shell_exec\(",
                "severity": "critical",
                "category": "rce",
            },
        ],
    }

    if attack_vector in vector_patterns:
        patterns.extend(vector_patterns[attack_vector])

    # Extract unique patterns from payload
    extracted = extract_signature_patterns(payload_preview)
    for pattern_info in extracted:
        if pattern_info not in patterns:
            patterns.append(pattern_info)

    # Add indicator-based patterns
    if indicators:
        for indicator_type, values in indicators.items():
            if indicator_type == "urls" and values:
                patterns.append(
                    {
                        "name": "extracted_url_pattern",
                        "regex": _escape_for_regex(
                            values[0] if isinstance(values, list) else str(values)
                        ),
                        "severity": "medium",
                        "category": "ioc_match",
                    }
                )
            elif indicator_type == "shell_commands" and values:
                cmd_list = values if isinstance(values, list) else [values]
                for cmd in cmd_list[:3]:  # Limit
                    patterns.append(
                        {
                            "name": "shell_command_pattern",
                            "regex": _escape_for_regex(str(cmd)),
                            "severity": "high",
                            "category": "command_execution",
                        }
                    )

    return patterns[:10]  # Limit to 10 patterns


def extract_signature_patterns(payload: str) -> List[Dict[str, str]]:
    """Extract signature patterns from a payload.

    Args:
        payload: The payload to analyze

    Returns:
        List of pattern configurations
    """
    patterns: List[Dict[str, str]] = []

    # Look for common exploit signatures
    exploit_sigs = [
        (r"wget\s+http", "wget_download", "high"),
        (r"curl\s+.*http", "curl_download", "high"),
        (r"/etc/passwd", "passwd_access", "high"),
        (r"/etc/shadow", "shadow_access", "critical"),
        (r"base64\s+-d", "base64_decode", "medium"),
        (r"eval\s*\(", "eval_execution", "critical"),
        (r"<?php", "php_injection", "high"),
        (r"<script", "xss_attempt", "medium"),
        (r"nc\s+-[el]", "netcat_shell", "critical"),
        (r"python\s+-c", "python_exec", "high"),
        (r"perl\s+-e", "perl_exec", "high"),
        (r"\\x[0-9a-fA-F]{2}", "shellcode", "critical"),
    ]

    for regex, name, severity in exploit_sigs:
        if re.search(regex, payload, re.IGNORECASE):
            patterns.append(
                {
                    "name": name,
                    "regex": regex,
                    "severity": severity,
                    "category": "exploit_signature",
                }
            )

    return patterns


def generate_tags(
    attack_vector: str, indicators: Dict[str, Any], source_patterns: List[str]
) -> List[str]:
    """Generate tags for the suggested honeypot.

    Args:
        attack_vector: Detected attack vector
        indicators: Extracted indicators
        source_patterns: Pattern fingerprints

    Returns:
        List of tags
    """
    tags: Set[str] = {"suggested", "auto-generated"}

    # Add attack vector tag
    if attack_vector and attack_vector != "unknown":
        tags.add(attack_vector.replace("_", "-"))

    # Add indicator-based tags
    if indicators:
        if "shell_commands" in indicators:
            tags.add("shell-activity")
        if "urls" in indicators:
            tags.add("callback-detection")
        if "file_paths" in indicators:
            tags.add("file-access")

    # Limit tag count
    return sorted(list(tags))[:10]


def _escape_for_regex(text: str) -> str:
    """Escape special regex characters in text.

    Args:
        text: Text to escape

    Returns:
        Regex-safe string
    """
    special_chars = r"\.^$*+?{}[]|()/"
    for char in special_chars:
        text = text.replace(char, f"\\{char}")
    return text


def generate_rationale(
    suggestion_type: SuggestionType,
    attack_vector: str,
    occurrence_count: int,
    source_ips_count: int,
    novelty_score: float,
) -> str:
    """Generate human-readable rationale for the suggestion.

    Args:
        suggestion_type: Type of suggestion
        attack_vector: Detected attack vector
        occurrence_count: Number of occurrences
        source_ips_count: Number of unique sources
        novelty_score: Novelty score

    Returns:
        Rationale string
    """
    parts: List[str] = []

    # Opening based on type
    type_intros = {
        SuggestionType.ZERODAY_PATTERN: "Novel attack pattern detected",
        SuggestionType.BEHAVIORAL_CLUSTER: "Coordinated attack behavior identified",
        SuggestionType.PROTOCOL_ANOMALY: "Unusual protocol activity observed",
        SuggestionType.EXPLOIT_TECHNIQUE: "Specific exploit technique detected",
        SuggestionType.COMMAND_PATTERN: "Malicious command pattern found",
    }
    parts.append(type_intros.get(suggestion_type, "Attack pattern detected"))

    # Add attack vector info
    if attack_vector and attack_vector != "unknown":
        parts.append(f"using {attack_vector.replace('_', ' ')} technique")

    # Add metrics
    parts.append(
        f". Observed {occurrence_count} times from {source_ips_count} unique sources."
    )

    # Add novelty insight
    if novelty_score >= 0.8:
        parts.append(
            " This pattern is highly novel and may represent an emerging threat "
            "not yet documented in CVE databases."
        )
    elif novelty_score >= 0.6:
        parts.append(
            " This pattern shows characteristics not commonly seen in known exploits, "
            "suggesting potential variant or new technique."
        )

    # Add recommendation
    parts.append(
        " Creating this honeypot would help gather more intelligence on this "
        "attack pattern and potentially discover new variants."
    )

    return "".join(parts)
