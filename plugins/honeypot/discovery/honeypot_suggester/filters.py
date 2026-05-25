"""Suggestion Filtering Utilities.

Advanced filtering logic for eliminating noise and deduplicating
honeypot suggestions based on similarity and relevance.
"""

from core.observability.logging import get_logger
from typing import Any, Dict, List, Set

from .models import HoneypotSuggestion, SuggestionPriority

logger = get_logger(__name__)

# Attack patterns that are too generic to warrant custom honeypots
GENERIC_PATTERNS: Set[str] = {
    "unknown",
    "generic",
    "undefined",
    "unspecified",
}

# Minimum thresholds for investigation value
MIN_SOURCE_IPS_FOR_HIGH_VALUE = 3
MIN_OCCURRENCES_FOR_HIGH_VALUE = 5
MIN_CONFIDENCE_FOR_HIGH_VALUE = 0.6


def is_generic_pattern(attack_vector: str, title: str) -> bool:
    """Check if a pattern is too generic to be actionable.

    Args:
        attack_vector: The attack vector type
        title: The suggestion title

    Returns:
        True if pattern is considered generic/noise
    """
    vector_lower = attack_vector.lower()
    title_lower = title.lower()

    # Check against known generic patterns
    for pattern in GENERIC_PATTERNS:
        if pattern in vector_lower:
            return True

    # Check for generic "unknown" titles
    if "unknown detector" in title_lower and "novel" not in title_lower:
        return True

    return False


def calculate_investigation_value(
    novelty_score: float,
    confidence: float,
    occurrence_count: int,
    source_ips_count: int,
    attack_vector: str,
    indicators: Dict[str, Any],
) -> float:
    """Calculate how valuable this pattern is for investigation.

    Higher scores indicate patterns worth dedicating a custom honeypot.

    Args:
        novelty_score: Pattern novelty (0-1)
        confidence: Detection confidence (0-1)
        occurrence_count: Number of times seen
        source_ips_count: Unique source IPs
        attack_vector: Type of attack
        indicators: Extracted IOCs

    Returns:
        Investigation value score (0-1)
    """
    # Base score from novelty and confidence
    base_score = (novelty_score * 0.35) + (confidence * 0.25)

    # Boost from occurrence frequency (capped)
    occurrence_boost = min(occurrence_count / 20, 0.15)

    # Boost from source diversity (indicates widespread campaign)
    diversity_boost = min(source_ips_count / 10, 0.15)

    # Sophistication boost from attack vector
    sophisticated_vectors = {
        "rce": 0.1,
        "deserialization": 0.1,
        "buffer_overflow": 0.08,
        "xxe": 0.08,
        "ssrf": 0.06,
        "command_injection": 0.05,
        "sql_injection": 0.04,
    }
    sophistication_boost = sophisticated_vectors.get(attack_vector, 0.0)

    # Indicator richness boost
    indicator_boost = 0.0
    if indicators:
        indicator_count = sum(
            len(v) if isinstance(v, list) else 1 for v in indicators.values() if v
        )
        indicator_boost = min(indicator_count * 0.01, 0.05)

    total = (
        base_score
        + occurrence_boost
        + diversity_boost
        + sophistication_boost
        + indicator_boost
    )

    return min(max(total, 0.0), 1.0)


def calculate_sophistication_level(
    attack_vector: str,
    indicators: Dict[str, Any],
    detection_patterns: List[Dict[str, str]],
) -> str:
    """Determine the sophistication level of an attack pattern.

    Args:
        attack_vector: Attack vector type
        indicators: Extracted indicators
        detection_patterns: Detection patterns

    Returns:
        "basic", "intermediate", or "advanced"
    """
    score = 0

    # Score by attack vector complexity
    advanced_vectors = {"rce", "deserialization", "buffer_overflow", "xxe"}
    intermediate_vectors = {"ssrf", "command_injection", "sql_injection", "lfi"}

    if attack_vector in advanced_vectors:
        score += 3
    elif attack_vector in intermediate_vectors:
        score += 2
    else:
        score += 1

    # Score by indicator richness
    if indicators:
        if "shell_commands" in indicators:
            score += 2
        if "encoded_payloads" in indicators:
            score += 1
        if "evasion_techniques" in indicators:
            score += 2

    # Score by pattern complexity
    if detection_patterns:
        complex_patterns = sum(
            1 for p in detection_patterns if p.get("severity") in ("critical", "high")
        )
        score += min(complex_patterns, 2)

    if score >= 6:
        return "advanced"
    elif score >= 3:
        return "intermediate"
    return "basic"


def generate_investigation_rationale(
    suggestion_type: str,
    attack_vector: str,
    occurrence_count: int,
    source_ips_count: int,
    novelty_score: float,
    sophistication_level: str,
) -> str:
    """Generate a concise rationale for why this suggestion is worth investigating.

    Args:
        suggestion_type: Type of suggestion
        attack_vector: Attack vector
        occurrence_count: Number of occurrences
        source_ips_count: Number of source IPs
        novelty_score: Novelty score
        sophistication_level: Sophistication level

    Returns:
        Human-readable investigation rationale
    """
    reasons = []

    # Primary reason based on novelty
    if novelty_score >= 0.85:
        reasons.append("Highly novel pattern not matching known CVEs")
    elif novelty_score >= 0.7:
        reasons.append("Novel attack technique with unique characteristics")

    # Attack sophistication
    if sophistication_level == "advanced":
        reasons.append("Advanced attack methodology indicating skilled threat actor")
    elif sophistication_level == "intermediate":
        reasons.append("Moderate complexity suggesting targeted campaign")

    # Campaign indicators
    if source_ips_count >= 10:
        reasons.append(f"Widespread campaign from {source_ips_count} sources")
    elif source_ips_count >= 5:
        reasons.append(f"Coordinated activity from {source_ips_count} sources")

    # Persistence
    if occurrence_count >= 20:
        reasons.append(f"Persistent pattern with {occurrence_count} occurrences")
    elif occurrence_count >= 10:
        reasons.append(f"Recurring pattern observed {occurrence_count} times")

    if not reasons:
        reasons.append("Pattern warrants further investigation")

    return ". ".join(reasons) + "."


def generate_descriptive_title(
    attack_vector: str,
    target_services: List[str],
    detection_patterns: List[Dict[str, str]],
    occurrence_count: int,
    source_ips_count: int,
) -> str:
    """Generate a descriptive, unique title for a suggestion.

    Avoids generic "Unknown Detector" titles.

    Args:
        attack_vector: Attack vector type
        target_services: Targeted services
        detection_patterns: Detection patterns
        occurrence_count: Number of occurrences
        source_ips_count: Number of source IPs

    Returns:
        Descriptive title string
    """
    # Format attack vector nicely
    vector_name = attack_vector.replace("_", " ").title()

    # Get primary service if available
    primary_service = None
    if target_services:
        first_service = target_services[0]
        if ":" in first_service:
            primary_service = first_service.split(":")[1]
        else:
            primary_service = first_service

    # Get severity indicator from patterns
    severity_label = "Attack"
    if detection_patterns:
        severities = [p.get("severity", "medium") for p in detection_patterns]
        if "critical" in severities:
            severity_label = "Critical Exploit"
        elif "high" in severities:
            severity_label = "High-Risk Attack"

    # Build title based on available information
    if attack_vector != "unknown" and primary_service:
        title = f"{vector_name} {severity_label} - {primary_service.title()}"
    elif attack_vector != "unknown":
        title = f"{vector_name} Pattern Detector"
    elif primary_service:
        service_name = primary_service.title()
        if source_ips_count >= 5:
            title = f"Multi-Source {service_name} Probe Detector"
        else:
            title = f"Novel {service_name} Attack Pattern"
    else:
        # Fallback with context
        if occurrence_count >= 10:
            title = f"Persistent Attack Campaign ({occurrence_count} hits)"
        elif source_ips_count >= 3:
            title = f"Coordinated Probe Pattern ({source_ips_count} sources)"
        else:
            title = "Emerging Attack Pattern Detector"

    return title


def deduplicate_suggestions(
    suggestions: List[HoneypotSuggestion],
    similarity_threshold: float = 0.8,
) -> List[HoneypotSuggestion]:
    """Deduplicate similar suggestions, keeping the highest-value ones.

    Groups suggestions by attack_vector + protocol and merges similar ones.

    Args:
        suggestions: List of suggestions to deduplicate
        similarity_threshold: How similar suggestions must be to merge (0-1)

    Returns:
        Deduplicated list of suggestions
    """
    if not suggestions:
        return []

    # Group by attack vector and protocol
    groups: Dict[str, List[HoneypotSuggestion]] = {}
    for suggestion in suggestions:
        key = (
            f"{suggestion.suggestion_type.value}:{suggestion.suggested_protocol.value}"
        )
        if key not in groups:
            groups[key] = []
        groups[key].append(suggestion)

    deduplicated: List[HoneypotSuggestion] = []

    for key, group in groups.items():
        if len(group) == 1:
            deduplicated.append(group[0])
            continue

        # Sort by confidence * catch rate (combined quality score)
        sorted_group = sorted(
            group,
            key=lambda s: s.confidence * s.estimated_catch_rate,
            reverse=True,
        )

        # Keep top suggestion, merge source IPs from others
        best = sorted_group[0]

        # Collect merged info
        all_source_ips: Set[str] = set(best.source_ips)
        total_occurrences = best.occurrence_count
        merged_count = 1

        for similar in sorted_group[1:]:
            # Check if similar enough to merge
            # (same type and protocol already checked by grouping)
            if _are_similar_patterns(best, similar, similarity_threshold):
                all_source_ips.update(similar.source_ips)
                total_occurrences += similar.occurrence_count
                merged_count += 1
            else:
                # Not similar enough, keep as separate
                deduplicated.append(similar)

        # Update best with merged data
        best.source_ips = list(all_source_ips)[:20]  # Cap at 20
        best.occurrence_count = total_occurrences

        deduplicated.append(best)

        if merged_count > 1:
            logger.debug(f"Merged {merged_count} similar suggestions into one")

    return deduplicated


def _are_similar_patterns(
    a: HoneypotSuggestion,
    b: HoneypotSuggestion,
    threshold: float,
) -> bool:
    """Check if two suggestions are similar enough to merge.

    Args:
        a: First suggestion
        b: Second suggestion
        threshold: Similarity threshold (0-1)

    Returns:
        True if suggestions are similar
    """
    # Must have same suggested port (within range)
    port_diff = abs(a.suggested_port - b.suggested_port)
    if port_diff > 100:  # Allow some port variation
        return False

    # Check tag overlap
    a_tags = set(a.tags)
    b_tags = set(b.tags)
    if a_tags and b_tags:
        overlap = len(a_tags & b_tags) / len(a_tags | b_tags)
        if overlap < threshold * 0.5:
            return False

    # Check source IP overlap (indicates same campaign)
    a_ips = set(a.source_ips)
    b_ips = set(b.source_ips)
    if a_ips and b_ips:
        ip_overlap = len(a_ips & b_ips) / min(len(a_ips), len(b_ips))
        if ip_overlap >= 0.3:  # 30% IP overlap suggests same campaign
            return True

    return False


def filter_and_rank_suggestions(
    suggestions: List[HoneypotSuggestion],
    max_suggestions: int = 15,
) -> List[HoneypotSuggestion]:
    """Apply all filtering and ranking logic to suggestions.

    This is the main entry point for filtering.

    Args:
        suggestions: Raw list of suggestions
        max_suggestions: Maximum number to return

    Returns:
        Filtered, ranked, and deduplicated suggestions
    """
    if not suggestions:
        return []

    # Step 1: Remove generic patterns
    filtered = [
        s
        for s in suggestions
        if not is_generic_pattern(
            getattr(s, "suggestion_type", s.suggestion_type).value
            if hasattr(s.suggestion_type, "value")
            else str(s.suggestion_type),
            s.title,
        )
    ]

    # Step 2: Deduplicate similar suggestions
    filtered = deduplicate_suggestions(filtered)

    # Step 3: Sort by priority, then confidence
    priority_order = {
        SuggestionPriority.CRITICAL: 0,
        SuggestionPriority.HIGH: 1,
        SuggestionPriority.MEDIUM: 2,
        SuggestionPriority.LOW: 3,
    }
    filtered.sort(
        key=lambda s: (
            priority_order.get(s.priority, 4),
            -s.confidence,
            -s.estimated_catch_rate,
        )
    )

    # Step 4: Limit to max
    return filtered[:max_suggestions]
