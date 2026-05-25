"""Clustering logic for ML Analyzer."""

import uuid
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Set, Tuple

from ...models import AttackEvent
from ..models import NetworkAnomaly
from .features import extract_features
from .utils import DBSCAN, HAS_SKLEARN, StandardScaler


def cluster_attacks_dbscan(
    events: List[AttackEvent],
    eps: float = 0.5,
    min_samples: int = 3,
) -> Tuple[List[NetworkAnomaly], Dict[str, Any]]:
    """Cluster attacks using DBSCAN algorithm.

    Clusters attacks based on feature similarity to identify
    coordinated attack campaigns.

    Args:
        events: Attack events to analyze
        eps: DBSCAN epsilon
        min_samples: DBSCAN minimum samples

    Returns:
        Tuple of (anomalies, metadata)
    """
    anomalies: List[NetworkAnomaly] = []

    if not HAS_SKLEARN or len(events) < min_samples:
        return anomalies, {"error": "Insufficient data or sklearn not available"}

    # Extract features
    features, ip_mapping = extract_features(events)

    if len(features) < min_samples:
        return anomalies, {"error": "Insufficient features"}

    # Normalize features
    scaler = StandardScaler()
    scaled_features = scaler.fit_transform(features)

    # Run DBSCAN
    dbscan = DBSCAN(eps=eps, min_samples=min_samples)
    labels = dbscan.fit_predict(scaled_features)

    # Analyze clusters
    cluster_ips: Dict[int, Set[str]] = defaultdict(set)
    for idx, label in enumerate(labels):
        if label != -1:  # -1 is noise
            ip = ip_mapping[idx]
            cluster_ips[label].add(ip)

    # Create anomalies for significant clusters
    for cluster_id, ips in cluster_ips.items():
        if len(ips) >= 3:
            anomaly = NetworkAnomaly(
                anomaly_id=str(uuid.uuid4())[:8],
                anomaly_type="ml_cluster",
                involved_ips=list(ips),
                description=(
                    f"ML-detected attack cluster: {len(ips)} IPs with similar behavior"
                ),
                severity="medium" if len(ips) >= 5 else "low",
                confidence=min(1.0, len(ips) / 10),
                detected_at=datetime.now(),
                metadata={
                    "cluster_id": cluster_id,
                    "method": "DBSCAN",
                    "ip_count": len(ips),
                },
            )
            anomalies.append(anomaly)

    # Count noise points
    noise_count = sum(1 for label in labels if label == -1)

    return anomalies, {
        "n_clusters": len(cluster_ips),
        "noise_points": noise_count,
        "total_samples": len(features),
    }


def fallback_clustering(events: List[AttackEvent]) -> List[NetworkAnomaly]:
    """Fallback clustering without sklearn."""
    anomalies = []

    # Simple heuristic clustering by behavior
    ip_behavior: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "protocols": set(), "categories": set()}
    )

    for event in events:
        ip = event.source_ip
        ip_behavior[ip]["count"] += 1
        ip_behavior[ip]["protocols"].add(
            event.protocol.value
            if hasattr(event.protocol, "value")
            else str(event.protocol)
        )
        ip_behavior[ip]["categories"].add(
            event.category.value
            if hasattr(event.category, "value")
            else str(event.category)
        )

    # Group by behavior fingerprint
    behavior_groups: Dict[str, Set[str]] = defaultdict(set)

    for ip, behavior in ip_behavior.items():
        # Create fingerprint
        fp = f"{','.join(sorted(behavior['protocols']))}|{','.join(sorted(behavior['categories']))}"
        behavior_groups[fp].add(ip)

    # Report groups with multiple IPs
    for fp, ips in behavior_groups.items():
        if len(ips) >= 3:
            anomaly = NetworkAnomaly(
                anomaly_id=str(uuid.uuid4())[:8],
                anomaly_type="behavior_cluster",
                involved_ips=list(ips),
                description=(
                    f"Behavior cluster: {len(ips)} IPs with identical attack pattern"
                ),
                severity="low",
                confidence=min(1.0, len(ips) / 10),
                detected_at=datetime.now(),
                metadata={
                    "behavior_fingerprint": fp,
                    "method": "heuristic",
                },
            )
            anomalies.append(anomaly)

    return anomalies
