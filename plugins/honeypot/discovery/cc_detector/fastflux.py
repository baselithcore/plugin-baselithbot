"""Fast-flux Detection logic."""

import uuid
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Set

from ...models import AttackEvent
from ..models import NetworkAnomaly
from .utils import extract_domains, parse_timestamp


def detect_fastflux(
    events: List[AttackEvent],
    fastflux_ip_threshold: int,
    fastflux_time_window_seconds: int,
) -> List[NetworkAnomaly]:
    """Detect fast-flux network patterns.

    Args:
        events: Attack events to analyze
        fastflux_ip_threshold: Minimum IP changes for fast-flux
        fastflux_time_window_seconds: Time window for fast-flux detection

    Returns:
        List of fast-flux related anomalies
    """
    anomalies: List[NetworkAnomaly] = []

    # Track domain -> IPs over time
    domain_ips: Dict[str, Dict[str, datetime]] = defaultdict(dict)

    for event in events:
        ts = parse_timestamp(event.timestamp)
        if not ts:
            continue

        domains = extract_domains(event)
        for domain in domains:
            domain_ips[domain][event.source_ip] = ts

    # Analyze domains with multiple associated IPs
    for domain, ip_times in domain_ips.items():
        if len(ip_times) < fastflux_ip_threshold:
            continue

        # Check if IPs changed within time window
        sorted_entries = sorted(ip_times.items(), key=lambda x: x[1])
        ips_in_window: Set[str] = set()
        window_start = sorted_entries[0][1]

        for ip, ts in sorted_entries:
            if (ts - window_start).total_seconds() <= fastflux_time_window_seconds:
                ips_in_window.add(ip)
            else:
                # Check if we have enough IPs in this window
                if len(ips_in_window) >= fastflux_ip_threshold:
                    break
                # Slide window
                window_start = ts
                ips_in_window = {ip}

        if len(ips_in_window) >= fastflux_ip_threshold:
            anomaly = NetworkAnomaly(
                anomaly_id=str(uuid.uuid4())[:8],
                anomaly_type="fastflux",
                involved_ips=list(ips_in_window),
                description=(
                    f"Possible fast-flux domain: {domain} - "
                    f"{len(ips_in_window)} IPs associated within "
                    f"{fastflux_time_window_seconds // 60}min"
                ),
                severity="high",
                confidence=min(1.0, len(ips_in_window) / 10),
                detected_at=datetime.now(),
                metadata={
                    "domain": domain,
                    "associated_ips": list(ips_in_window),
                    "time_window_seconds": fastflux_time_window_seconds,
                },
            )
            anomalies.append(anomaly)

    return anomalies
