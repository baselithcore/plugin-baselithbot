"""Temporal evolution analysis for Botnet Profiler."""

from collections import defaultdict
from typing import Any, Dict, List, Set

from ...models import AttackEvent
from .utils import parse_timestamp


def analyze_temporal_evolution(events: List[AttackEvent]) -> Dict[str, Any]:
    """Analyze how the botnet evolved over time.

    Args:
        events: List of events

    Returns:
        Dict describing temporal evolution
    """
    # Track IPs per time bucket (hourly)
    hourly_ips: Dict[str, Set[str]] = defaultdict(set)

    first_seen = None
    last_seen = None

    for event in events:
        ts = parse_timestamp(event.timestamp)
        if ts:
            hour_key = ts.strftime("%Y-%m-%d %H:00")
            hourly_ips[hour_key].add(event.source_ip)

            if first_seen is None or ts < first_seen:
                first_seen = ts
            if last_seen is None or ts > last_seen:
                last_seen = ts

    # Calculate growth trend
    sorted_hours = sorted(hourly_ips.keys())
    hourly_counts = [len(hourly_ips[h]) for h in sorted_hours]

    # Simple trend: compare first half vs second half
    if len(hourly_counts) >= 4:
        first_half = sum(hourly_counts[: len(hourly_counts) // 2])
        second_half = sum(hourly_counts[len(hourly_counts) // 2 :])
        if second_half > first_half * 1.2:
            trend = "growing"
        elif first_half > second_half * 1.2:
            trend = "declining"
        else:
            trend = "stable"
    else:
        trend = "unknown"

    # Track new vs returning IPs
    all_seen: Set[str] = set()
    new_per_hour: Dict[str, int] = {}

    for hour in sorted_hours:
        new_count = len(hourly_ips[hour] - all_seen)
        new_per_hour[hour] = new_count
        all_seen.update(hourly_ips[hour])

    return {
        "first_seen": first_seen.isoformat() if first_seen else None,
        "last_seen": last_seen.isoformat() if last_seen else None,
        "duration_hours": (
            (last_seen - first_seen).total_seconds() / 3600
            if first_seen and last_seen
            else 0
        ),
        "trend": trend,
        "hourly_bot_counts": {h: len(hourly_ips[h]) for h in sorted_hours[-24:]},
        "new_bots_per_hour": {h: new_per_hour[h] for h in sorted_hours[-24:]},
        "total_unique_bots": len(all_seen),
    }
