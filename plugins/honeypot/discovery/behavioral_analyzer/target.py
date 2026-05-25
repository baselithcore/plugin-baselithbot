"""Target correlation logic for Behavioral Analyzer."""

import uuid
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Set, Tuple

from ...models import AttackEvent
from ..models import NetworkAnomaly
from .utils import calculate_severity, parse_timestamp


def detect_target_correlation(
    events: List[AttackEvent], min_correlation_group_size: int
) -> List[NetworkAnomaly]:
    """Detect IPs attacking same ports/services in sequence.

    Identifies coordinated targeting where multiple IPs attack
    the same honeypots/services in similar order.

    Args:
        events: Attack events to analyze
        min_correlation_group_size: Minimum IPs to form a correlation group

    Returns:
        List of target correlation anomalies
    """
    anomalies: List[NetworkAnomaly] = []

    # Build attack sequences per IP
    ip_sequences: Dict[str, List[Tuple[str, datetime]]] = defaultdict(list)

    for event in events:
        ts = parse_timestamp(event.timestamp)
        if ts:
            # Target = honeypot_id + protocol
            target = f"{event.honeypot_id}:{event.protocol.value if hasattr(event.protocol, 'value') else event.protocol}"
            ip_sequences[event.source_ip].append((target, ts))

    # Sort sequences by time
    for ip in ip_sequences:
        ip_sequences[ip].sort(key=lambda x: x[1])

    # Extract target order (without timestamps)
    target_orders: Dict[str, List[str]] = {
        ip: [t[0] for t in seq[:10]]  # First 10 targets
        for ip, seq in ip_sequences.items()
        if len(seq) >= 2
    }

    # Find similar target orders
    order_groups: Dict[str, Set[str]] = defaultdict(set)
    for ip, order in target_orders.items():
        order_key = "->".join(order)
        order_groups[order_key].add(ip)

    # Report groups with similar targeting
    for order_key, ips in order_groups.items():
        if len(ips) >= min_correlation_group_size:
            targets = order_key.split("->")
            anomaly = NetworkAnomaly(
                anomaly_id=str(uuid.uuid4())[:8],
                anomaly_type="target_correlation",
                involved_ips=list(ips),
                description=(
                    f"{len(ips)} IPs attacked targets in identical sequence: "
                    f"{' → '.join(targets[:3])}{'...' if len(targets) > 3 else ''}"
                ),
                severity=calculate_severity(len(ips), 2, 4, 6),
                confidence=min(1.0, len(targets) / 5),
                detected_at=datetime.now(),
                metadata={
                    "target_sequence": targets,
                    "ip_count": len(ips),
                    "sequence_length": len(targets),
                },
            )
            anomalies.append(anomaly)

    return anomalies
