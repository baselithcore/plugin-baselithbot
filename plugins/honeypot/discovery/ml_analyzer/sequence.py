"""Sequence analysis logic for ML Analyzer."""

import uuid
from collections import Counter, defaultdict
from datetime import datetime
from typing import Any, Dict, List, Set, Tuple

from ...models import AttackEvent
from ..models import NetworkAnomaly


def analyze_attack_sequences(
    events: List[AttackEvent],
    window_size: int = 5,
) -> Tuple[List[NetworkAnomaly], Dict[str, Any]]:
    """Analyze attack sequences to detect unknown attack chains.

    Looks for common patterns in attack sequences that might
    indicate automated attack playbooks.

    Args:
        events: Attack events to analyze
        window_size: Window size for sequence analysis

    Returns:
        Tuple of (anomalies, metadata)
    """
    anomalies: List[NetworkAnomaly] = []

    # Build sequences per IP
    ip_sequences: Dict[str, List[str]] = defaultdict(list)

    for event in events:
        # Create action signature
        action = create_action_signature(event)
        ip_sequences[event.source_ip].append(action)

    # Find common sequences (n-grams)
    sequence_counts: Counter = Counter()
    sequence_ips: Dict[str, Set[str]] = defaultdict(set)

    for ip, actions in ip_sequences.items():
        if len(actions) < window_size:
            continue

        # Extract n-grams
        for i in range(len(actions) - window_size + 1):
            seq = tuple(actions[i : i + window_size])
            sequence_counts[seq] += 1
            sequence_ips[seq].add(ip)

    # Report repeated sequences
    for seq, count in sequence_counts.most_common(10):
        if count >= 3 and len(sequence_ips[seq]) >= 2:
            ips = list(sequence_ips[seq])
            anomaly = NetworkAnomaly(
                anomaly_id=str(uuid.uuid4())[:8],
                anomaly_type="attack_chain",
                involved_ips=ips,
                description=(
                    f"Repeated attack sequence detected: {count} occurrences "
                    f"across {len(ips)} IPs"
                ),
                severity="medium" if count >= 5 else "low",
                confidence=min(1.0, count / 10),
                detected_at=datetime.now(),
                metadata={
                    "sequence": list(seq),
                    "occurrence_count": count,
                    "ip_count": len(ips),
                },
            )
            anomalies.append(anomaly)

    return anomalies, {
        "unique_sequences": len(sequence_counts),
        "repeated_sequences": sum(1 for c in sequence_counts.values() if c >= 3),
    }


def create_action_signature(event: AttackEvent) -> str:
    """Create action signature for sequence analysis."""
    parts = []

    # Protocol
    protocol = (
        event.protocol.value
        if hasattr(event.protocol, "value")
        else str(event.protocol)
    )
    parts.append(protocol[:3])

    # Event type
    parts.append(event.event_type[:3] if event.event_type else "unk")

    # Category
    category = (
        event.category.value
        if hasattr(event.category, "value")
        else str(event.category)
    )
    parts.append(category[:5])

    return ":".join(parts)
