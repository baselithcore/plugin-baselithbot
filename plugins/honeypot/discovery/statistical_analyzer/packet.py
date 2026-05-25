"""Packet Size Analysis."""

import math
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Set, Tuple

from ...models import AttackEvent
from ..models import NetworkAnomaly
from .utils import calculate_severity


def detect_packet_size_clusters(
    events: List[AttackEvent], packet_size_tolerance: float
) -> List[NetworkAnomaly]:
    """Detect IPs with similar packet/payload sizes.

    Malware from the same family typically generates packets of
    consistent sizes due to shared code/protocol implementations.
    """
    anomalies: List[NetworkAnomaly] = []

    # Calculate payload sizes per IP
    ip_sizes: Dict[str, List[int]] = defaultdict(list)

    for event in events:
        size = _calculate_payload_size(event)
        if size > 0:
            ip_sizes[event.source_ip].append(size)

    if len(ip_sizes) < 2:
        return anomalies

    # Calculate size fingerprint per IP (median size, variance)
    ip_fingerprints: Dict[str, Tuple[int, float]] = {}

    for ip, sizes in ip_sizes.items():
        if len(sizes) >= 2:
            median = sorted(sizes)[len(sizes) // 2]
            variance = sum((s - median) ** 2 for s in sizes) / len(sizes)
            # Normalize variance to coefficient of variation
            cv = math.sqrt(variance) / median if median > 0 else 0
            ip_fingerprints[ip] = (median, round(cv, 2))

    # Group by similar fingerprints
    size_groups: Dict[Tuple[int, float], Set[str]] = defaultdict(set)

    for ip, (median, cv) in ip_fingerprints.items():
        # Bucket by size range (tolerance-based)
        bucket_size = max(10, int(median * packet_size_tolerance))
        size_bucket = (median // bucket_size) * bucket_size
        size_groups[(size_bucket, cv)].add(ip)

    # Report clusters
    for (size_bucket, cv), ips in size_groups.items():
        if len(ips) >= 3:
            anomaly = NetworkAnomaly(
                anomaly_id=str(uuid.uuid4())[:8],
                anomaly_type="packet_size_cluster",
                involved_ips=list(ips),
                description=(
                    f"{len(ips)} IPs with similar payload sizes (~{size_bucket} bytes) - "
                    f"possible same malware family"
                ),
                severity=calculate_severity(len(ips), 3, 5, 8),
                confidence=0.7
                if cv < 0.2
                else 0.5,  # Lower variance = higher confidence
                detected_at=datetime.now(),
                metadata={
                    "median_size_bytes": size_bucket,
                    "size_variance_cv": cv,
                    "ip_count": len(ips),
                },
            )
            anomalies.append(anomaly)

    return anomalies


def _calculate_payload_size(event: AttackEvent) -> int:
    """Calculate payload size from event data."""
    total = 0

    if event.raw_data:
        total += len(event.raw_data.encode("utf-8", errors="ignore"))

    if event.http_body:
        total += len(event.http_body.encode("utf-8", errors="ignore"))

    if event.command:
        total += len(event.command.encode("utf-8", errors="ignore"))

    return total
