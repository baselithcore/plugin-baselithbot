"""Temporal feature extraction."""

from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List

from ...models import AttackEvent
from .models import AttackFeatureVector
from .utils import parse_timestamp


def extract_temporal_features(
    features: AttackFeatureVector, events: List[AttackEvent]
) -> None:
    """Extract temporal frequency features."""
    features.event_count = len(events)

    # Parse timestamps
    timestamps: List[datetime] = []
    for event in events:
        ts = parse_timestamp(event.timestamp)
        if ts:
            timestamps.append(ts)

    if len(timestamps) < 2:
        return

    timestamps.sort()

    # Time spread
    time_spread = (timestamps[-1] - timestamps[0]).total_seconds() / 3600
    features.time_spread_hours = time_spread

    # Events per hour
    if time_spread > 0:
        features.events_per_hour = len(events) / time_spread
    else:
        features.events_per_hour = float(len(events))

    # Burst score (max events in any 5-minute window)
    window_counts: Dict[str, int] = defaultdict(int)
    for ts in timestamps:
        window_key = ts.strftime("%Y-%m-%d %H:%M")[:-1]  # 10-min buckets
        window_counts[window_key] += 1

    if window_counts:
        max_burst = max(window_counts.values())
        avg_rate = len(events) / len(window_counts)
        features.burst_score = max_burst / avg_rate if avg_rate > 0 else 0

    # Peak hour (hour with most events)
    hour_counts: Counter = Counter()
    for ts in timestamps:
        hour_counts[ts.hour] += 1

    if hour_counts:
        features.peak_hour = hour_counts.most_common(1)[0][0]
