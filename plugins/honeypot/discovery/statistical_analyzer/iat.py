"""Inter-Arrival Time Analysis."""

import math
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from typing import Dict, List, Set, Tuple

from ...models import AttackEvent
from ..models import NetworkAnomaly
from .utils import parse_timestamp


def detect_iat_patterns(
    events: List[AttackEvent], iat_bucket_ms: int
) -> List[NetworkAnomaly]:
    """Detect IPs with identical inter-arrival time distributions.

    Bots controlled by the same C&C often have synchronized or
    patterned inter-arrival times between requests.
    """
    anomalies: List[NetworkAnomaly] = []

    # Calculate IAT distributions per IP
    ip_iats: Dict[str, List[float]] = defaultdict(list)

    ip_events: Dict[str, List[datetime]] = defaultdict(list)
    for event in events:
        ts = parse_timestamp(event.timestamp)
        if ts:
            ip_events[event.source_ip].append(ts)

    # Calculate inter-arrival times
    for ip, timestamps in ip_events.items():
        if len(timestamps) < 3:
            continue

        timestamps.sort()
        for i in range(1, len(timestamps)):
            iat_ms = (timestamps[i] - timestamps[i - 1]).total_seconds() * 1000
            if iat_ms < 60000:  # Only consider IATs under 1 minute
                ip_iats[ip].append(iat_ms)

    if len(ip_iats) < 2:
        return anomalies

    # Compute IAT fingerprint: (mode bucket, mean, std_dev)
    ip_iat_fingerprints: Dict[str, Tuple[int, float, float]] = {}

    for ip, iats in ip_iats.items():
        if len(iats) >= 3:
            # Bucket IATs
            buckets = [int(iat // iat_bucket_ms) for iat in iats]
            mode_bucket = Counter(buckets).most_common(1)[0][0]

            mean_iat = sum(iats) / len(iats)
            std_dev = math.sqrt(sum((i - mean_iat) ** 2 for i in iats) / len(iats))

            # Normalize std_dev to bucket
            std_bucket = int(std_dev // iat_bucket_ms)

            ip_iat_fingerprints[ip] = (mode_bucket, round(mean_iat, 0), std_bucket)

    # Group by similar fingerprints
    iat_groups: Dict[Tuple[int, float, float], Set[str]] = defaultdict(set)

    for ip, fingerprint in ip_iat_fingerprints.items():
        iat_groups[fingerprint].add(ip)

    # Report suspicious IAT patterns
    for fingerprint, ips in iat_groups.items():
        if len(ips) >= 3:
            mode_bucket, mean_iat, std_bucket = fingerprint

            anomaly = NetworkAnomaly(
                anomaly_id=str(uuid.uuid4())[:8],
                anomaly_type="iat_pattern",
                involved_ips=list(ips),
                description=(
                    f"{len(ips)} IPs with identical timing pattern "
                    f"(mean IAT: {mean_iat:.0f}ms) - possible synchronized bots"
                ),
                severity="medium" if len(ips) >= 5 else "low",
                confidence=0.8 if std_bucket < 5 else 0.5,
                detected_at=datetime.now(),
                metadata={
                    "mode_bucket_ms": mode_bucket * iat_bucket_ms,
                    "mean_iat_ms": mean_iat,
                    "std_dev_bucket": std_bucket,
                    "ip_count": len(ips),
                },
            )
            anomalies.append(anomaly)

    return anomalies
