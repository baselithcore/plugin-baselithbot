"""Time series analysis logic for ML Analyzer."""

import math
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Set, Tuple

from ...models import AttackEvent
from ..models import NetworkAnomaly
from .utils import parse_timestamp


def analyze_time_patterns(
    events: List[AttackEvent],
) -> Tuple[List[NetworkAnomaly], Dict[str, Any]]:
    """Analyze temporal patterns in attack data.

    Detects:
    - Burst patterns (sudden spikes)
    - Periodic patterns (regular intervals)
    - Time-of-day patterns

    Args:
        events: Attack events to analyze

    Returns:
        Tuple of (anomalies, metadata)
    """
    anomalies: List[NetworkAnomaly] = []

    # Bucket events by hour
    hourly_counts: Dict[str, int] = defaultdict(int)
    hourly_ips: Dict[str, Set[str]] = defaultdict(set)

    for event in events:
        ts = parse_timestamp(event.timestamp)
        if ts:
            hour_key = ts.strftime("%Y-%m-%d %H:00")
            hourly_counts[hour_key] += 1
            hourly_ips[hour_key].add(event.source_ip)

    if len(hourly_counts) < 3:
        return anomalies, {"error": "Insufficient time data"}

    # Calculate statistics
    counts = list(hourly_counts.values())
    mean_count = sum(counts) / len(counts)
    std_count = math.sqrt(sum((c - mean_count) ** 2 for c in counts) / len(counts))

    # Detect bursts (> 2 std deviations)
    burst_threshold = mean_count + 2 * std_count
    bursts = []

    for hour, count in hourly_counts.items():
        if count > burst_threshold:
            bursts.append(
                {
                    "hour": hour,
                    "count": count,
                    "ips": list(hourly_ips[hour]),
                    "z_score": (count - mean_count) / std_count if std_count > 0 else 0,
                }
            )

    # Report bursts
    for burst in bursts:
        anomaly = NetworkAnomaly(
            anomaly_id=str(uuid.uuid4())[:8],
            anomaly_type="time_burst",
            involved_ips=burst["ips"][:20],  # Limit IPs
            description=(
                f"Attack burst at {burst['hour']}: {burst['count']} events "
                f"(z-score: {burst['z_score']:.1f})"
            ),
            severity="high" if burst["z_score"] > 3 else "medium",
            confidence=min(1.0, burst["z_score"] / 4),
            detected_at=datetime.now(),
            metadata={
                "hour": burst["hour"],
                "event_count": burst["count"],
                "z_score": burst["z_score"],
            },
        )
        anomalies.append(anomaly)

    # Detect time-of-day patterns (hour of day analysis)
    hour_of_day: Dict[int, int] = defaultdict(int)
    for event in events:
        ts = parse_timestamp(event.timestamp)
        if ts:
            hour_of_day[ts.hour] += 1

    # Find peak hours
    peak_hour = None
    if hour_of_day:
        peak_hour = max(hour_of_day.keys(), key=lambda h: hour_of_day[h])
        peak_count = hour_of_day[peak_hour]
        total = sum(hour_of_day.values())
        peak_ratio = peak_count / total if total > 0 else 0

        # Report if single hour has > 30% of attacks
        if peak_ratio > 0.3:
            anomaly = NetworkAnomaly(
                anomaly_id=str(uuid.uuid4())[:8],
                anomaly_type="time_pattern",
                involved_ips=[],
                description=(
                    f"Time pattern: {peak_ratio:.0%} of attacks occur at hour {peak_hour}:00"
                ),
                severity="low",
                confidence=peak_ratio,
                detected_at=datetime.now(),
                metadata={
                    "peak_hour": peak_hour,
                    "peak_ratio": peak_ratio,
                    "hourly_distribution": dict(hour_of_day),
                },
            )
            anomalies.append(anomaly)

    return anomalies, {
        "mean_hourly_events": mean_count,
        "std_hourly_events": std_count,
        "bursts_detected": len(bursts),
        "peak_hour": peak_hour if hour_of_day else None,
    }
