"""TTL Clustering Analysis."""

import uuid
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Set

from ...models import AttackEvent
from ..models import NetworkAnomaly
from .utils import calculate_severity


def detect_ttl_clustering(
    events: List[AttackEvent], ttl_tolerance: int
) -> List[NetworkAnomaly]:
    """Detect IPs with similar TTL values indicating shared infrastructure.

    Bots behind the same ISP or hosted on the same cloud provider often
    have similar TTL values in their packets.

    Note: TTL data must be available in event metadata or raw_data.
    """
    anomalies: List[NetworkAnomaly] = []

    # Extract TTL values per IP
    ip_ttls: Dict[str, List[int]] = defaultdict(list)

    for event in events:
        ttl = _extract_ttl(event)
        if ttl is not None:
            ip_ttls[event.source_ip].append(ttl)

    if len(ip_ttls) < 2:
        return anomalies

    # Calculate average TTL per IP
    ip_avg_ttl: Dict[str, int] = {}
    for ip, ttls in ip_ttls.items():
        avg = sum(ttls) / len(ttls)
        # Round to nearest standard TTL (32, 64, 128, 255)
        ip_avg_ttl[ip] = _round_to_standard_ttl(avg)

    # Group IPs by TTL with tolerance
    ttl_groups: Dict[int, Set[str]] = defaultdict(set)
    for ip, ttl in ip_avg_ttl.items():
        # Normalize to bucket
        bucket = (ttl // ttl_tolerance) * ttl_tolerance
        ttl_groups[bucket].add(ip)

    # Report suspicious TTL clusters
    for ttl_bucket, ips in ttl_groups.items():
        if len(ips) >= 3:  # Minimum cluster size
            # Calculate infrastructure score
            infra_score = min(1.0, len(ips) / 10)

            anomaly = NetworkAnomaly(
                anomaly_id=str(uuid.uuid4())[:8],
                anomaly_type="ttl_cluster",
                involved_ips=list(ips),
                description=(
                    f"{len(ips)} IPs with similar TTL (~{ttl_bucket}) - "
                    f"possible shared infrastructure"
                ),
                severity=calculate_severity(len(ips), 3, 6, 10),
                confidence=infra_score,
                detected_at=datetime.now(),
                metadata={
                    "ttl_value": ttl_bucket,
                    "ip_count": len(ips),
                    "tolerance": ttl_tolerance,
                },
            )
            anomalies.append(anomaly)

    return anomalies


def _extract_ttl(event: AttackEvent) -> Optional[int]:
    """Extract TTL value from event.

    TTL can be in raw_data, headers, or bot_signals.
    Common TTL values: 32, 64, 128, 255 (decremented by hops)
    """
    # Try bot_signals first
    if event.bot_signals and "ttl" in event.bot_signals:
        try:
            return int(event.bot_signals["ttl"])
        except (ValueError, TypeError):
            pass

    # Try HTTP headers (X-Forwarded-For might have hop info)
    if event.http_headers:
        # Some proxies add TTL info
        for key in ["X-TTL", "X-Hop-Count"]:
            if key in event.http_headers:
                try:
                    return int(event.http_headers[key])
                except (ValueError, TypeError):
                    pass

    # Estimate from source port patterns or use simulated value
    # Higher source ports often correlate with certain OS/TTL defaults
    if event.source_port:
        # Linux typically uses high ports (32768-60999) and TTL 64
        # Windows uses various and TTL 128
        if 32768 <= event.source_port <= 60999:
            return 64  # Likely Linux
        elif event.source_port < 1024:
            return 128  # Likely Windows/privileged
        else:
            return 64  # Default assumption

    return None


def _round_to_standard_ttl(ttl: float) -> int:
    """Round TTL to nearest standard value."""
    standards = [32, 64, 128, 255]
    return min(standards, key=lambda x: abs(x - ttl))
