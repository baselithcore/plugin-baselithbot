"""Beaconing Detection logic."""

import uuid
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from ...models import AttackEvent
from ..models import NetworkAnomaly
from .utils import parse_timestamp


def detect_beaconing(
    events: List[AttackEvent],
    beaconing_min_occurrences: int,
    beaconing_interval_tolerance: float,
) -> List[NetworkAnomaly]:
    """Detect beaconing patterns (periodic C&C check-ins).

    Args:
        events: Attack events to analyze
        beaconing_min_occurrences: Minimum beacons to detect pattern
        beaconing_interval_tolerance: Tolerance for beaconing interval matching

    Returns:
        List of beaconing pattern anomalies
    """
    anomalies: List[NetworkAnomaly] = []

    # Group events by source IP and target
    ip_target_events: Dict[str, Dict[str, List[datetime]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for event in events:
        ts = parse_timestamp(event.timestamp)
        if ts:
            target = event.honeypot_id
            ip_target_events[event.source_ip][target].append(ts)

    # Analyze each IP's connection pattern per target
    for source_ip, targets in ip_target_events.items():
        for target, timestamps in targets.items():
            if len(timestamps) < beaconing_min_occurrences:
                continue

            # Sort and calculate intervals
            timestamps.sort()
            intervals = []
            for i in range(1, len(timestamps)):
                interval = (timestamps[i] - timestamps[i - 1]).total_seconds()
                if 1 <= interval <= 86400:  # 1 second to 24 hours
                    intervals.append(interval)

            if len(intervals) < beaconing_min_occurrences - 1:
                continue

            # Check for consistent interval (beaconing)
            beacon_result = detect_beacon_interval(
                intervals, beaconing_min_occurrences, beaconing_interval_tolerance
            )
            if beacon_result:
                interval_seconds, consistency = beacon_result

                anomaly = NetworkAnomaly(
                    anomaly_id=str(uuid.uuid4())[:8],
                    anomaly_type="beaconing",
                    involved_ips=[source_ip],
                    description=(
                        f"IP {source_ip} shows beaconing pattern to {target}: "
                        f"~{format_interval(interval_seconds)} interval "
                        f"({consistency:.0%} consistent)"
                    ),
                    severity="high" if consistency >= 0.9 else "medium",
                    confidence=consistency,
                    detected_at=datetime.now(),
                    metadata={
                        "source_ip": source_ip,
                        "target": target,
                        "beacon_interval_seconds": interval_seconds,
                        "consistency": consistency,
                        "occurrence_count": len(timestamps),
                    },
                )
                anomalies.append(anomaly)

    return anomalies


def detect_beacon_interval(
    intervals: List[float], min_occurrences: int, tolerance_ratio: float
) -> Optional[Tuple[float, float]]:
    """Detect if intervals follow a consistent beacon pattern.

    Returns:
        Tuple of (interval_seconds, consistency_score) or None
    """
    if len(intervals) < 3:
        return None

    # Find most common interval (within tolerance)
    interval_buckets: Dict[int, List[float]] = defaultdict(list)

    for interval in intervals:
        # Bucket by 10-second intervals for grouping
        bucket = int(interval / 10) * 10
        interval_buckets[bucket].append(interval)

    # Find largest bucket
    best_bucket = max(interval_buckets.keys(), key=lambda k: len(interval_buckets[k]))
    bucket_intervals = interval_buckets[best_bucket]

    if len(bucket_intervals) < min_occurrences - 1:
        return None

    # Calculate average interval and consistency
    avg_interval = sum(bucket_intervals) / len(bucket_intervals)

    # Count intervals within tolerance
    tolerance = avg_interval * tolerance_ratio
    consistent = sum(1 for i in intervals if abs(i - avg_interval) <= tolerance)
    consistency = consistent / len(intervals)

    if consistency >= 0.6:  # At least 60% consistent
        return (avg_interval, consistency)

    return None


def format_interval(seconds: float) -> str:
    """Format interval for human reading."""
    if seconds < 60:
        return f"{seconds:.0f}s"
    elif seconds < 3600:
        return f"{seconds / 60:.1f}m"
    else:
        return f"{seconds / 3600:.1f}h"
