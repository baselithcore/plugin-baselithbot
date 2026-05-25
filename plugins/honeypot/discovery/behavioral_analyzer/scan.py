"""Scan pattern logic for Behavioral Analyzer."""

import uuid
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Set, Tuple

from ...models import AttackEvent
from ..models import NetworkAnomaly
from .utils import parse_timestamp


def detect_scan_patterns(
    events: List[AttackEvent], min_correlation_group_size: int
) -> List[NetworkAnomaly]:
    """Detect identical port scanning patterns.

    Analyzes request timing and patterns to identify IPs
    with identical scanning behavior (same scan speed, sequence).

    Args:
        events: Attack events to analyze
        min_correlation_group_size: Minimum IPs to form a correlation group

    Returns:
        List of scan pattern anomalies
    """
    anomalies: List[NetworkAnomaly] = []

    # Calculate inter-request intervals per IP
    ip_intervals: Dict[str, List[float]] = defaultdict(list)

    ip_events: Dict[str, List[datetime]] = defaultdict(list)
    for event in events:
        ts = parse_timestamp(event.timestamp)
        if ts:
            ip_events[event.source_ip].append(ts)

    # Calculate intervals
    for ip, timestamps in ip_events.items():
        if len(timestamps) < 3:
            continue

        timestamps.sort()
        for i in range(1, len(timestamps)):
            interval = (timestamps[i] - timestamps[i - 1]).total_seconds()
            if interval < 300:  # Ignore gaps > 5 minutes
                ip_intervals[ip].append(interval)

    # Compute scan pattern fingerprint (avg interval, variance)
    fingerprints: Dict[str, Tuple[float, float]] = {}
    for ip, intervals in ip_intervals.items():
        if len(intervals) >= 3:
            avg = sum(intervals) / len(intervals)
            variance = sum((i - avg) ** 2 for i in intervals) / len(intervals)
            fingerprints[ip] = (round(avg, 1), round(variance, 2))

    # Group by similar fingerprints
    pattern_groups: Dict[Tuple[float, float], Set[str]] = defaultdict(set)
    for ip, fp in fingerprints.items():
        pattern_groups[fp].add(ip)

    # Report similar scan patterns
    for pattern, ips in pattern_groups.items():
        if len(ips) >= min_correlation_group_size:
            avg_interval, variance = pattern
            anomaly = NetworkAnomaly(
                anomaly_id=str(uuid.uuid4())[:8],
                anomaly_type="scan_pattern",
                involved_ips=list(ips),
                description=(
                    f"{len(ips)} IPs have identical scanning pattern: "
                    f"~{avg_interval:.1f}s intervals (variance: {variance:.2f})"
                ),
                severity="medium" if len(ips) >= 5 else "low",
                confidence=min(1.0, 0.5 + len(ips) / 10),
                detected_at=datetime.now(),
                metadata={
                    "avg_interval_seconds": avg_interval,
                    "variance": variance,
                    "ip_count": len(ips),
                },
            )
            anomalies.append(anomaly)

    return anomalies
