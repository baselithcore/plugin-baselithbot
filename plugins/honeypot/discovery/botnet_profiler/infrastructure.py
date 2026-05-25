"""Infrastructure analysis for Botnet Profiler."""

import re
from collections import Counter
from typing import Any, Dict, List, Optional, Tuple

from ...models import AttackEvent
from ..models import BotnetCluster, HubNode


def analyze_cc_infrastructure(
    cluster: BotnetCluster,
    hub_nodes: Optional[List[HubNode]],
    events: List[AttackEvent],
) -> Dict[str, Any]:
    """Analyze C&C infrastructure for the cluster.

    Args:
        cluster: Botnet cluster
        hub_nodes: List of hub nodes
        events: List of events

    Returns:
        Dict describing C&C infrastructure
    """
    cc_servers: List[Dict] = []

    # Get cluster hub nodes
    if hub_nodes:
        cluster_hubs = [
            h for h in hub_nodes if h.ip in cluster.member_ips and h.is_confirmed_cc
        ]

        for hub in cluster_hubs:
            cc_servers.append(
                {
                    "ip": hub.ip,
                    "threat_score": hub.threat_score,
                    "connected_bots": hub.connected_bots,
                    "country": hub.country or hub.country_code,
                    "protocols": hub.protocols,
                    "is_confirmed": True,
                }
            )

    # Also check suspected CC from cluster
    if cluster.suspected_cc_ip and cluster.suspected_cc_ip not in [
        c["ip"] for c in cc_servers
    ]:
        cc_servers.append(
            {
                "ip": cluster.suspected_cc_ip,
                "threat_score": 50.0,  # Unknown, moderate score
                "connected_bots": cluster.size,
                "country": None,
                "protocols": cluster.common_protocols,
                "is_confirmed": False,
            }
        )

    # Extract domains from events
    domains = extract_cc_domains(events)

    return {
        "cc_servers": cc_servers,
        "cc_count": len(cc_servers),
        "detected_domains": domains,
        "infrastructure_type": classify_infrastructure(len(cc_servers), domains),
    }


def extract_cc_domains(events: List[AttackEvent]) -> List[str]:
    """Extract potential C&C domains from events."""
    domains = set()
    domain_pattern = r"(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}"

    for event in events:
        for field in [event.raw_data, event.command, event.http_path]:
            if field:
                matches = re.findall(domain_pattern, field)
                domains.update(m.lower() for m in matches)

    # Filter obvious safe domains
    safe = ["google", "microsoft", "amazon", "github", "localhost"]
    return [d for d in domains if not any(s in d for s in safe)][:10]


def classify_infrastructure(cc_count: int, domains: List[str]) -> str:
    """Classify C&C infrastructure type."""
    if cc_count == 0:
        return "unknown"
    if cc_count == 1 and len(domains) <= 1:
        return "centralized"
    if cc_count > 3 or len(domains) > 3:
        return "distributed"
    return "hybrid"


def analyze_infrastructure(events: List[AttackEvent]) -> Dict[str, Any]:
    """Analyze geographic and network infrastructure.

    Args:
        events: List of events

    Returns:
        Dict describing infrastructure
    """
    countries: Counter = Counter()
    cities: Counter = Counter()
    coords: List[Tuple[float, float]] = []

    for event in events:
        if event.geo:
            if event.geo.country_code:
                countries[event.geo.country_code] += 1
            if event.geo.city:
                cities[event.geo.city] += 1
            if event.geo.latitude and event.geo.longitude:
                coords.append((event.geo.latitude, event.geo.longitude))

    return {
        "country_distribution": dict(countries.most_common(10)),
        "top_country": countries.most_common(1)[0][0] if countries else None,
        "country_count": len(countries),
        "city_distribution": dict(cities.most_common(10)),
        "geographic_spread": calculate_geo_spread(coords),
        "hosting_analysis": {
            "likely_cloud": len(countries) >= 5,
            "likely_residential": len(countries) <= 2 and len(coords) < 10,
        },
    }


def calculate_geo_spread(coords: List[Tuple[float, float]]) -> str:
    """Calculate geographic spread of bots."""
    if len(coords) < 2:
        return "unknown"

    # Simple spread calculation (max distance)
    lats = [c[0] for c in coords]
    lons = [c[1] for c in coords]

    lat_spread = max(lats) - min(lats) if lats else 0
    lon_spread = max(lons) - min(lons) if lons else 0

    if lat_spread > 50 or lon_spread > 100:
        return "global"
    if lat_spread > 20 or lon_spread > 40:
        return "continental"
    return "regional"
