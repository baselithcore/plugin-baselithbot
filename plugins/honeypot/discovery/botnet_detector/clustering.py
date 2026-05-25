"""Clustering logic for Botnet Detector."""

import uuid
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Set

try:
    import networkx as nx

    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    nx = None

from ..models import BotnetCluster, HubNode


def build_clusters(
    G: "nx.Graph",
    partition: Dict[str, int],
    hub_nodes: List[HubNode],
    node_metadata: Dict[str, Dict[str, Any]],
    modularity: float,
    min_cluster_size: int = 2,
) -> List[BotnetCluster]:
    """Build BotnetCluster objects from community partition.

    Args:
        G: NetworkX graph
        partition: Community partition
        hub_nodes: Identified hub nodes
        node_metadata: Node metadata
        modularity: Modularity score of the partition
        min_cluster_size: Minimum cluster size to include

    Returns:
        List of BotnetCluster objects
    """
    if not partition:
        return []

    # Group nodes by community
    communities: Dict[int, List[str]] = defaultdict(list)
    for node_id, comm_id in partition.items():
        meta = node_metadata.get(node_id, {})
        # Only include attacker nodes in clusters
        if meta.get("type") != "honeypot":
            communities[comm_id].append(node_id)

    clusters: List[BotnetCluster] = []

    for comm_id, members in communities.items():
        if len(members) < min_cluster_size:
            continue

        # Find confirmed C&C IPs (hubs) related to this cluster
        # 1. Internal hubs (members of the cluster)
        cluster_internal_hubs = [h for h in hub_nodes if h.ip in members]

        # 2. External hubs (connected to cluster members)
        associated_hubs: Set[str] = set()
        hub_connection_counts: Dict[str, int] = defaultdict(int)

        # Add internal hubs first (strength = cluster size for now, or just mark as internal)
        for h in cluster_internal_hubs:
            associated_hubs.add(h.ip)
            hub_connection_counts[h.ip] = len(
                members
            )  # Internal hub connected to everyone effectively in this context

        # Check for connections to external hubs
        hub_ips = {h.ip for h in hub_nodes}
        for member in members:
            # Check neighbors of this member
            if HAS_NETWORKX and G.has_node(member):
                for neighbor in G.neighbors(member):
                    if neighbor in hub_ips and neighbor not in members:
                        associated_hubs.add(neighbor)
                        hub_connection_counts[neighbor] += 1

        # suspect C&C is the one with highest threat score / centrality
        # Preference: Confirmed C&C > High Threat Score > Internal
        sorted_candidates = []
        for hub_ip in associated_hubs:
            hub_data = next((h for h in hub_nodes if h.ip == hub_ip), None)
            if hub_data:
                score = (
                    (100 if hub_data.is_confirmed_cc else 0)
                    + hub_data.threat_score
                    + (50 if hub_ip in members else 0)
                )
                sorted_candidates.append((hub_ip, score))

        sorted_candidates.sort(key=lambda x: x[1], reverse=True)

        suspected_cc = sorted_candidates[0][0] if sorted_candidates else None

        # Build metadata
        cc_metadata = {}
        for ip in associated_hubs:
            count = hub_connection_counts.get(ip, 0)
            cc_metadata[ip] = {
                "connection_count": count,
                "confidence": min(1.0, count / len(members)) if members else 0.0,
            }

        # Gather protocols and targets
        protocols: Set[str] = set()
        targets: Set[str] = set()
        first_seen = datetime.now(timezone.utc)
        last_seen = datetime.now(timezone.utc)
        severities: Set[str] = set()

        for member in members:
            meta = node_metadata.get(member, {})
            protocols.update(meta.get("protocols", []))
            severities.update(meta.get("severities", []))

            # Get connected honeypot targets
            if G.has_node(member):
                for neighbor in G.neighbors(member):
                    nmeta = node_metadata.get(neighbor, {})
                    if nmeta.get("type") == "honeypot":
                        targets.add(neighbor)

            # Track time range
            fs = meta.get("first_seen")
            ls = meta.get("last_seen")
            if fs and (isinstance(fs, datetime) or isinstance(fs, str)):
                if isinstance(fs, str):
                    fs = datetime.fromisoformat(fs.replace("Z", "+00:00"))
                if fs < first_seen:
                    first_seen = fs
            if ls and (isinstance(ls, datetime) or isinstance(ls, str)):
                if isinstance(ls, str):
                    ls = datetime.fromisoformat(ls.replace("Z", "+00:00"))
                if ls > last_seen:
                    last_seen = ls

        # Calculate coordination score based on temporal clustering
        coordination_score = calculate_coordination_score(G, members)

        # Determine severity
        if "critical" in severities:
            severity = "critical"
        elif "high" in severities:
            severity = "high"
        elif "medium" in severities:
            severity = "medium"
        else:
            severity = "low"

        # Calculate confidence
        confidence = min(1.0, (len(members) / 10) * modularity * 2)

        cluster = BotnetCluster(
            cluster_id=str(uuid.uuid4())[:8],
            member_ips=members,
            suspected_cc_ip=suspected_cc,
            associated_cc_ips=list(associated_hubs),
            associated_cc_metadata=cc_metadata,
            size=len(members),
            attack_coordination_score=coordination_score,
            common_protocols=list(protocols),
            common_targets=list(targets),
            detection_confidence=confidence,
            first_detected=first_seen,
            last_activity=last_seen,
            severity=severity,
            modularity_score=modularity,
        )
        clusters.append(cluster)

    # Sort by size and threat level
    clusters.sort(key=lambda c: (c.size, c.attack_coordination_score), reverse=True)

    return clusters


def calculate_coordination_score(G: "nx.Graph", members: List[str]) -> float:
    """Calculate coordination score for a cluster.

    Based on edge density and correlation markers within the cluster.
    """
    if len(members) < 2:
        return 0.0

    # Count internal edges
    internal_edges = 0
    correlated_edges = 0

    for i, m1 in enumerate(members):
        for m2 in members[i + 1 :]:
            if G.has_edge(m1, m2):
                internal_edges += 1
                if G[m1][m2].get("correlated", False):
                    correlated_edges += 1

    # Maximum possible internal edges
    max_edges = len(members) * (len(members) - 1) / 2

    if max_edges == 0:
        return 0.0

    # Base score on edge density
    density_score = internal_edges / max_edges

    # Boost for correlated edges
    correlation_boost = (
        correlated_edges / max(1, internal_edges) if internal_edges > 0 else 0
    )

    return min(1.0, density_score * 0.6 + correlation_boost * 0.4)
