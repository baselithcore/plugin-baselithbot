"""Anomaly detection logic for Botnet Detector."""

import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List

from ..models import NetworkAnomaly


def detect_anomalies(
    partition: Dict[str, int],
    node_metadata: Dict[str, Dict[str, Any]],
) -> List[NetworkAnomaly]:
    """Detect network behavior anomalies.

    Looks for:
    - Geographic clustering anomalies
    """
    anomalies: List[NetworkAnomaly] = []

    # Detect geographic clustering (many IPs from same country attacking together)
    geo_clusters = detect_geo_clustering(partition, node_metadata)
    anomalies.extend(geo_clusters)

    return anomalies


def detect_geo_clustering(
    partition: Dict[str, int],
    node_metadata: Dict[str, Dict[str, Any]],
) -> List[NetworkAnomaly]:
    """Detect unusual geographic clustering within communities."""
    anomalies = []

    # Group by community and country
    comm_countries: Dict[int, Dict[str, List[str]]] = defaultdict(
        lambda: defaultdict(list)
    )

    for node_id, comm_id in partition.items():
        meta = node_metadata.get(node_id, {})
        if meta.get("type") == "honeypot":
            continue
        country = meta.get("country_code", "unknown")
        comm_countries[comm_id][country].append(node_id)

    for comm_id, countries in comm_countries.items():
        for country, ips in countries.items():
            if len(ips) >= 3 and country != "unknown":
                # Unusual concentration from single country
                anomaly = NetworkAnomaly(
                    anomaly_id=str(uuid.uuid4())[:8],
                    anomaly_type="geo_cluster",
                    involved_ips=ips,
                    description=f"Cluster of {len(ips)} IPs from {country} in community {comm_id}",
                    severity="medium" if len(ips) >= 5 else "low",
                    confidence=min(1.0, len(ips) / 10),
                    detected_at=datetime.now(),
                    metadata={"country": country, "community_id": comm_id},
                )
                anomalies.append(anomaly)

    return anomalies
