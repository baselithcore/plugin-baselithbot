"""DGA Detection logic."""

import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Set

from ...models import AttackEvent
from ..models import NetworkAnomaly
from .utils import calculate_entropy, extract_domains


def detect_dga_domains(
    events: List[AttackEvent],
    dga_entropy_threshold: float,
    dga_consonant_ratio: float,
) -> List[NetworkAnomaly]:
    """Detect Domain Generation Algorithm patterns.

    Args:
        events: Attack events containing domain references
        dga_entropy_threshold: Minimum entropy for DGA domain detection
        dga_consonant_ratio: Maximum consonant ratio for DGA detection

    Returns:
        List of DGA-related anomalies
    """
    anomalies: List[NetworkAnomaly] = []

    # Extract domains from events
    ip_domains: Dict[str, Set[str]] = defaultdict(set)

    for event in events:
        domains = extract_domains(event)
        for domain in domains:
            ip_domains[event.source_ip].add(domain)

    # Analyze each domain
    dga_domains: Dict[str, Dict[str, Any]] = {}

    for ip, domains in ip_domains.items():
        for domain in domains:
            if is_dga_domain(domain, dga_entropy_threshold, dga_consonant_ratio):
                if domain not in dga_domains:
                    dga_domains[domain] = {
                        "ips": set(),
                        "entropy": calculate_entropy(domain),
                        "consonant_ratio": calculate_consonant_ratio(domain),
                    }
                dga_domains[domain]["ips"].add(ip)

    # Create anomalies for DGA domains
    for domain, info in dga_domains.items():
        ips = list(info["ips"])
        anomaly = NetworkAnomaly(
            anomaly_id=str(uuid.uuid4())[:8],
            anomaly_type="dga_domain",
            involved_ips=ips,
            description=(
                f"Suspected DGA domain: {domain} "
                f"(entropy: {info['entropy']:.2f}, "
                f"consonants: {info['consonant_ratio']:.0%})"
            ),
            severity="high" if len(ips) >= 3 else "medium",
            confidence=min(1.0, info["entropy"] / 5.0),
            detected_at=datetime.now(),
            metadata={
                "domain": domain,
                "entropy": info["entropy"],
                "consonant_ratio": info["consonant_ratio"],
                "source_ips": ips,
            },
        )
        anomalies.append(anomaly)

    return anomalies


def is_dga_domain(
    domain: str, entropy_threshold: float, consonant_threshold: float
) -> bool:
    """Check if domain appears to be DGA-generated."""
    # Strip TLD for analysis
    parts = domain.split(".")
    if len(parts) < 2:
        return False

    # Analyze main domain part (without TLD)
    main_part = parts[-2] if len(parts[-1]) <= 3 else parts[-1]

    # Check min length
    if len(main_part) < 6:
        return False

    # Check entropy
    entropy = calculate_entropy(main_part)
    if entropy < entropy_threshold:
        return False

    # Check consonant ratio (DGA often has high consonant ratio)
    consonant_ratio = calculate_consonant_ratio(main_part)
    if consonant_ratio > consonant_threshold:
        return True

    # Check for numeric patterns mixed with letters
    has_digits = any(c.isdigit() for c in main_part)
    has_letters = any(c.isalpha() for c in main_part)
    if has_digits and has_letters and len(main_part) > 10:
        return True

    return entropy >= 4.0  # High entropy threshold


def calculate_consonant_ratio(text: str) -> float:
    """Calculate ratio of consonants in text."""
    vowels = set("aeiouAEIOU")
    letters = [c for c in text if c.isalpha()]

    if not letters:
        return 0.0

    consonants = sum(1 for c in letters if c not in vowels)
    return consonants / len(letters)
