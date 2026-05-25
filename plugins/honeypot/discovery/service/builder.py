"""Discovery Service Result Builder."""

from typing import Any, Dict, List, Optional

from .models import (
    BotnetCluster,
    DiscoveryGraphData,
    GraphEdgeData,
    GraphNodeData,
    HubNode,
    NetworkAnomaly,
)


def _to_native(value: Any) -> Any:
    """Convert numpy types to native Python types for JSON serialization."""
    # Handle numpy integer types
    if hasattr(value, "item"):
        return value.item()
    # Handle numpy arrays
    if hasattr(value, "tolist"):
        return value.tolist()
    return value


def get_max_severity(severities: List[str]) -> str:
    """Get maximum severity from list."""
    priority = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}
    if not severities:
        return "info"
    return max(severities, key=lambda s: priority.get(s, 0))


def build_graph_data(
    G: Any,  # NetworkX graph
    partition: Dict[str, int],
    hub_nodes: List[HubNode],
    degree_centrality: Dict[str, float],
    node_metadata: Dict[str, Dict[str, Any]],
) -> DiscoveryGraphData:
    """Build visualization graph data from analysis results."""
    hub_ips = {h.ip for h in hub_nodes}
    confirmed_cc_ips = {h.ip for h in hub_nodes if h.is_confirmed_cc}

    nodes: List[GraphNodeData] = []
    edges: List[GraphEdgeData] = []
    cluster_info: List[Dict[str, Any]] = []

    # Build node data
    for node_id in G.nodes():
        meta = node_metadata.get(node_id, {})
        node_type = meta.get("type", "attacker")

        # Determine if hub and if confirmed C&C
        is_hub = node_id in hub_ips
        is_confirmed = node_id in confirmed_cc_ips

        # Get cluster (convert numpy int to native int)
        raw_cluster = partition.get(node_id)
        cluster_id = str(_to_native(raw_cluster)) if raw_cluster is not None else None

        node_data = GraphNodeData(
            id=node_id,
            type="cc" if is_hub else node_type,
            cluster_id=cluster_id,
            degree=_to_native(G.degree(node_id)),
            centrality=float(_to_native(degree_centrality.get(node_id, 0.0))),
            country_code=meta.get("country_code"),
            country=meta.get("country"),
            protocols=meta.get("protocols", []),
            severity=get_max_severity(meta.get("severities", [])),
            attack_count=_to_native(meta.get("attack_count", 0)),
            is_hub=is_hub,
            is_confirmed_cc=is_confirmed,
        )
        nodes.append(node_data)

    # Build edge data
    for src, tgt, data in G.edges(data=True):
        src_cluster = partition.get(src)
        tgt_cluster = partition.get(tgt)

        edge_data = GraphEdgeData(
            source=src,
            target=tgt,
            weight=float(_to_native(data.get("weight", 1.0))),
            is_intra_cluster=src_cluster == tgt_cluster and src_cluster is not None,
        )
        edges.append(edge_data)

    # Build cluster metadata for coloring
    unique_clusters = set(partition.values())
    for cluster_id in unique_clusters:
        members = [n for n, c in partition.items() if c == cluster_id]
        cluster_info.append(
            {
                "id": str(_to_native(cluster_id)),
                "size": len(members),
            }
        )

    return DiscoveryGraphData(
        nodes=nodes,
        edges=edges,
        clusters=cluster_info,
    )


def build_summary(
    total_attackers: int,
    total_edges: int,
    botnets: List[BotnetCluster],
    hub_nodes: List[HubNode],
    anomalies: List[NetworkAnomaly],
    modularity: float,
    behavioral_meta: Optional[Dict[str, Any]] = None,
    statistical_meta: Optional[Dict[str, Any]] = None,
    cc_meta: Optional[Dict[str, Any]] = None,
    botnet_profiles: Optional[List[Dict[str, Any]]] = None,
    ml_meta: Optional[Dict[str, Any]] = None,
    feature_meta: Optional[Dict[str, Any]] = None,
    zeroday_meta: Optional[Dict[str, Any]] = None,
    exploit_meta: Optional[Dict[str, Any]] = None,
    intel_meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build analysis summary statistics."""
    summary = {
        "total_attackers": total_attackers,
        "total_connections": total_edges,
        "detected_botnets": len(botnets),
        "total_botnet_members": sum(c.size for c in botnets),
        "potential_cc_servers": len(hub_nodes),  # All hubs are potential C&C servers
        "hub_nodes": len(hub_nodes),
        "anomalies_detected": len(anomalies),
        "modularity_score": modularity,
        "high_severity_clusters": sum(
            1 for c in botnets if c.severity in ("high", "critical")
        ),
    }

    # Add behavioral correlation stats
    if behavioral_meta:
        summary["behavioral_correlations"] = behavioral_meta

    # Add statistical indicator stats
    if statistical_meta:
        summary["statistical_indicators"] = statistical_meta

    # Add C&C detection stats
    if cc_meta:
        summary["cc_detection"] = cc_meta

    # Add botnet profiles
    if botnet_profiles:
        summary["botnet_profiles"] = botnet_profiles
        # Extract malware families
        families = [
            p["malware_family"]["identified_family"]
            for p in botnet_profiles
            if p.get("malware_family", {}).get("identified_family")
        ]
        if families:
            summary["identified_malware_families"] = list(set(families))

    # Add ML analysis stats
    if ml_meta:
        summary["ml_analysis"] = ml_meta

    # Add feature extraction stats
    if feature_meta:
        summary["feature_meta"] = feature_meta

    # Add zero-day detection stats
    if zeroday_meta:
        summary["zeroday_detection"] = zeroday_meta

    # Add exploit analysis stats
    if exploit_meta:
        summary["exploit_patterns"] = exploit_meta

    # Add threat intel stats
    if intel_meta:
        summary["threat_intel"] = intel_meta

    return summary
