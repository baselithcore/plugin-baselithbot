"""Size estimation logic for Botnet Profiler."""

from datetime import datetime, timezone
from typing import Any, Dict, List

# plugins/honeypot/discovery/botnet_profiler/size.py -> ...models is plugins.honeypot.models
from ...models import AttackEvent
from ..models import BotnetCluster
from .utils import parse_timestamp


def calculate_size_metrics(
    cluster: BotnetCluster, events: List[AttackEvent]
) -> Dict[str, Any]:
    """Calculate botnet size metrics.

    Args:
        cluster: Botnet cluster
        events: List of attack events

    Returns:
        Dict containing size metrics
    """
    unique_ips = set(cluster.member_ips)

    # Count unique source ports (indicates different bot instances)
    source_ports = set()
    for event in events:
        source_ports.add((event.source_ip, event.source_port))

    # Activity metrics
    active_last_hour = set()
    active_last_day = set()
    now = datetime.now(timezone.utc)

    for event in events:
        ts = parse_timestamp(event.timestamp)
        if ts:
            if (now - ts).total_seconds() <= 3600:
                active_last_hour.add(event.source_ip)
            if (now - ts).total_seconds() <= 86400:
                active_last_day.add(event.source_ip)

    return {
        "total_unique_ips": len(unique_ips),
        "total_connections": len(source_ports),
        "active_last_hour": len(active_last_hour),
        "active_last_24h": len(active_last_day),
        "estimated_size": len(unique_ips),
        "size_classification": classify_size(len(unique_ips)),
    }


def classify_size(count: int) -> str:
    """Classify botnet size.

    Args:
        count: Number of unique bots

    Returns:
        Size classification string
    """
    if count >= 1000:
        return "large"
    if count >= 100:
        return "medium"
    if count >= 10:
        return "small"
    return "micro"
