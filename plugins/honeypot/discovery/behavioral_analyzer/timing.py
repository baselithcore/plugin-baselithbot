"""Timing analysis logic for Behavioral Analyzer."""

import uuid
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Set

from ...models import AttackEvent
from ..models import NetworkAnomaly
from .utils import calculate_severity, parse_timestamp


def detect_timing_sync(
    events: List[AttackEvent],
    timing_window_seconds: int,
    min_correlation_group_size: int,
    window_seconds: Optional[int] = None,
) -> List[NetworkAnomaly]:
    """Detect IPs attacking in synchronized time windows.

    Finds groups of distinct IPs that attack within ±N seconds of each other,
    which is a strong indicator of coordinated botnet activity.

    Args:
        events: Attack events to analyze
        timing_window_seconds: Default timing window
        min_correlation_group_size: Minimum IPs to form a correlation group
        window_seconds: Override timing window

    Returns:
        List of timing synchronization anomalies
    """
    window = window_seconds or timing_window_seconds
    anomalies: List[NetworkAnomaly] = []

    # Group events by honeypot and time bucket
    buckets: Dict[str, Dict[str, Set[str]]] = defaultdict(lambda: defaultdict(set))

    for event in events:
        ts = parse_timestamp(event.timestamp)
        if ts is None:
            continue

        # Create time buckets at window intervals
        bucket_key = ts.replace(
            second=(ts.second // window) * window, microsecond=0
        ).isoformat()

        buckets[event.honeypot_id][bucket_key].add(event.source_ip)

    # Find buckets with multiple distinct IPs
    for honeypot_id, time_buckets in buckets.items():
        for bucket_time, ips in time_buckets.items():
            if len(ips) >= min_correlation_group_size:
                # Calculate synchronization score
                sync_score = min(1.0, len(ips) / 10)

                anomaly = NetworkAnomaly(
                    anomaly_id=str(uuid.uuid4())[:8],
                    anomaly_type="timing_sync",
                    involved_ips=list(ips),
                    description=(
                        f"{len(ips)} IPs attacked {honeypot_id} within "
                        f"{window}s window at {bucket_time}"
                    ),
                    severity=calculate_severity(len(ips), 3, 5, 8),
                    confidence=sync_score,
                    detected_at=datetime.now(),
                    metadata={
                        "honeypot_id": honeypot_id,
                        "bucket_time": bucket_time,
                        "window_seconds": window,
                        "ip_count": len(ips),
                    },
                )
                anomalies.append(anomaly)

    return anomalies
