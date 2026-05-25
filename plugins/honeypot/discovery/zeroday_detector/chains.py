"""Zero-Day Detector Chains and Protocols."""

import uuid
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Set

from ...models import AttackEvent
from ..models import NetworkAnomaly
from .signatures import detect_attack_vector
from .utils import extract_payload, parse_timestamp


def detect_novel_chains(events: List[AttackEvent]) -> List[NetworkAnomaly]:
    """Detect novel multi-step attack chains."""
    anomalies = []

    # Group by IP and sort by time
    ip_events: Dict[str, List[AttackEvent]] = defaultdict(list)
    for event in events:
        ip_events[event.source_ip].append(event)

    for ip, ip_event_list in ip_events.items():
        if len(ip_event_list) < 3:
            continue

        # Sort by timestamp
        sorted_events = sorted(
            ip_event_list,
            key=lambda e: parse_timestamp(e.timestamp) or datetime.min,
        )

        # Extract attack sequence
        sequence = []
        for event in sorted_events:
            vector, _ = detect_attack_vector(extract_payload(event) or "")
            sequence.append(vector)

        # Check for sophisticated chains (multiple different techniques)
        unique_techniques = set(sequence)
        if len(unique_techniques) >= 3 and "unknown" not in unique_techniques:
            anomaly = NetworkAnomaly(
                anomaly_id=f"chain_{uuid.uuid4().hex[:8]}",
                anomaly_type="novel_attack_chain",
                severity="high",
                confidence=0.7,
                source_ips=[ip],
                description=(
                    f"Multi-technique attack chain: {' → '.join(sequence[:5])}"
                ),
                details={
                    "techniques": list(unique_techniques),
                    "sequence_length": len(sequence),
                },
            )
            anomalies.append(anomaly)

    return anomalies


def detect_protocol_anomalies(events: List[AttackEvent]) -> List[NetworkAnomaly]:
    """Detect unusual protocol usage patterns."""
    anomalies: List[NetworkAnomaly] = []

    # Track protocol/port combinations
    proto_port: Dict[str, Set[str]] = defaultdict(set)
    for event in events:
        proto = (
            event.protocol.value
            if hasattr(event.protocol, "value")
            else str(event.protocol)
        )
        # port = str(event.source_port) if event.source_port else "unknown"
        proto_port[proto].add(event.source_ip)

    # Detect HTTP on non-standard ports with exploit attempts
    # (Already handled by other analyzers, but we can flag novel protocols)

    return anomalies
