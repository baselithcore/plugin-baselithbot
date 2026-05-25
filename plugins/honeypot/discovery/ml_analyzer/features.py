"""Feature extraction logic for ML Analyzer."""

from collections import defaultdict
from typing import Any, Dict, List, Tuple

from ...models import AttackEvent
from .utils import parse_timestamp


def extract_features(events: List[AttackEvent]) -> Tuple[List[List[float]], List[str]]:
    """Extract numerical features from events for ML.

    Returns:
        Tuple of (feature matrix, IP mapping list)
    """
    # Aggregate features per IP
    ip_features: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {
            "event_count": 0,
            "unique_ports": set(),
            "protocols": set(),
            "severities": [],
            "timestamps": [],
            "payload_sizes": [],
        }
    )

    for event in events:
        ip = event.source_ip
        ip_features[ip]["event_count"] += 1
        ip_features[ip]["unique_ports"].add(event.source_port)
        ip_features[ip]["protocols"].add(
            event.protocol.value
            if hasattr(event.protocol, "value")
            else str(event.protocol)
        )
        ip_features[ip]["severities"].append(severity_to_num(event.severity))
        ts = parse_timestamp(event.timestamp)
        if ts:
            ip_features[ip]["timestamps"].append(ts)

        # Payload size
        payload_size = len(event.raw_data or "") + len(event.command or "")
        ip_features[ip]["payload_sizes"].append(payload_size)

    # Convert to feature vectors
    features = []
    ip_mapping = []

    for ip, data in ip_features.items():
        if data["event_count"] < 2:
            continue

        # Calculate inter-arrival time stats
        timestamps = sorted(data["timestamps"])
        if len(timestamps) >= 2:
            intervals = [
                (timestamps[i] - timestamps[i - 1]).total_seconds()
                for i in range(1, len(timestamps))
            ]
            mean_iat = sum(intervals) / len(intervals)
            var_iat = sum((i - mean_iat) ** 2 for i in intervals) / len(intervals)
        else:
            mean_iat = 0
            var_iat = 0

        # Build feature vector
        feature_vec = [
            data["event_count"],
            len(data["unique_ports"]),
            len(data["protocols"]),
            sum(data["severities"]) / len(data["severities"]),  # Avg severity
            mean_iat,
            var_iat,
            sum(data["payload_sizes"]) / len(data["payload_sizes"]),  # Avg payload
        ]

        features.append(feature_vec)
        ip_mapping.append(ip)

    return features, ip_mapping


def severity_to_num(severity: Any) -> float:
    """Convert severity to numerical value."""
    sev_str = severity.value if hasattr(severity, "value") else str(severity)
    mapping = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}
    return mapping.get(sev_str.lower(), 1)
