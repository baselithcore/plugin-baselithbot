"""Callback IP Detection logic."""

import re
import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List

from ...models import AttackEvent
from ..models import NetworkAnomaly


def detect_callback_ips(events: List[AttackEvent]) -> List[NetworkAnomaly]:
    """Detect potential C&C callback IP addresses.

    Args:
        events: Attack events to analyze

    Returns:
        List of callback IP anomalies
    """
    anomalies: List[NetworkAnomaly] = []

    # Extract callback candidates from event data
    callback_candidates: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"source_ips": set(), "contexts": []}
    )

    ip_pattern = r"\b(?:\d{1,3}\.){3}\d{1,3}\b"

    for event in events:
        # Skip the event's own source IP
        source_ip = event.source_ip

        # Search for IPs in payload/command data
        search_fields = [
            (event.raw_data, "raw_data"),
            (event.command, "command"),
            (event.http_body, "http_body"),
        ]

        for field_content, field_name in search_fields:
            if not field_content:
                continue

            found_ips = re.findall(ip_pattern, field_content)
            for found_ip in found_ips:
                # Skip private/local IPs and source IP
                if is_callback_candidate(found_ip) and found_ip != source_ip:
                    callback_candidates[found_ip]["source_ips"].add(source_ip)
                    callback_candidates[found_ip]["contexts"].append(
                        {
                            "field": field_name,
                            "source_ip": source_ip,
                        }
                    )

    # Report callback IPs seen from multiple sources
    for callback_ip, info in callback_candidates.items():
        source_count = len(info["source_ips"])

        if source_count >= 2:  # Referenced by at least 2 different bots
            anomaly = NetworkAnomaly(
                anomaly_id=str(uuid.uuid4())[:8],
                anomaly_type="callback_ip",
                involved_ips=list(info["source_ips"]),
                description=(
                    f"Potential C&C callback IP: {callback_ip} - "
                    f"referenced by {source_count} source IPs"
                ),
                severity="critical" if source_count >= 5 else "high",
                confidence=min(1.0, source_count / 5),
                detected_at=datetime.now(),
                metadata={
                    "callback_ip": callback_ip,
                    "source_ips": list(info["source_ips"]),
                    "source_count": source_count,
                    "context_samples": info["contexts"][:5],
                },
            )
            anomalies.append(anomaly)

    return anomalies


def is_callback_candidate(ip: str) -> bool:
    """Check if IP is a valid callback candidate (not private/local)."""
    parts = ip.split(".")
    if len(parts) != 4:
        return False

    try:
        octets = [int(p) for p in parts]
    except ValueError:
        return False

    # Skip private ranges
    if octets[0] == 10:  # 10.0.0.0/8
        return False
    # 172.16.0.0/12
    if octets[0] == 172 and 16 <= octets[1] <= 31:
        return False
    # 192.168.0.0/16
    if octets[0] == 192 and octets[1] == 168:
        return False
    # Loopback
    if octets[0] == 127:
        return False
    # Reserved
    if octets[0] == 0 or octets[0] >= 224:
        return False

    return True
