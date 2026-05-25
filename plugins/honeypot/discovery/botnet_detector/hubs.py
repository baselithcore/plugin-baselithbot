"""Hub node identification logic for Botnet Detector."""

from core.observability.logging import get_logger
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List

try:
    import networkx as nx

    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    nx = None

from ..models import HubNode

logger = get_logger(__name__)


# ============================================================================
# Configuration Constants - Tune these to adjust C&C detection sensitivity
# ============================================================================

# Minimum number of connections to be considered a potential C&C
MIN_CONNECTIONS_FOR_HUB = 5

# Multiplier for average degree to calculate dynamic threshold
DEGREE_MULTIPLIER = 2.0

# For high-activity graphs (max_degree > this), use stricter thresholds
HIGH_ACTIVITY_THRESHOLD = 20
HIGH_ACTIVITY_MIN_CONNECTIONS = 8

# Minimum cluster size to consider for leader detection
MIN_CLUSTER_SIZE = 3

# Minimum connections for a cluster leader to be significant
MIN_LEADER_CONNECTIONS = 4

# Minimum cross-cluster connections for bridge leader detection
MIN_CROSS_CLUSTER_CONNECTIONS = 2

# Threat score threshold for confirmed C&C status
CONFIRMED_CC_THRESHOLD = 70.0


@dataclass
class ThreatScoreWeights:
    """Configurable weights for threat score calculation.

    Adjust these to change how different factors contribute to the final score.
    Total max score should be ~100 with default weights.
    """

    centrality_max: float = 30.0  # Max points from centrality
    degree_ratio_max: float = 25.0  # Max points from degree vs average
    cross_cluster_max: float = 15.0  # Max points from cross-cluster connections
    cross_cluster_multiplier: float = 5.0  # Points per cross-cluster connection
    leader_bonus: float = 10.0  # Bonus for being cluster leader
    multi_honeypot_bonus: float = 15.0  # Bonus for targeting multiple honeypots
    correlation_bonus_max: float = 10.0  # Max bonus from correlation count
    correlation_multiplier: float = 2.0  # Points per correlation


# Default weights instance
DEFAULT_WEIGHTS = ThreatScoreWeights()


def _to_native(value: Any) -> Any:
    """Convert numpy types to native Python types for JSON serialization."""
    if hasattr(value, "item"):
        return value.item()
    if hasattr(value, "tolist"):
        return value.tolist()
    return value


def identify_hub_nodes(
    G: "nx.Graph",
    partition: Dict[str, int],
    degree_centrality: Dict[str, float],
    betweenness_centrality: Dict[str, float],
    node_metadata: Dict[str, Dict[str, Any]],
    hub_threshold: float = 0.1,  # Restored to stricter threshold
) -> List[HubNode]:
    """Identify potential C&C servers based on centrality metrics.

    A C&C server should have significantly more connections than average
    and/or act as a communication bridge between different clusters.

    Args:
        G: NetworkX graph
        partition: Community partition from Louvain
        degree_centrality: Degree centrality scores
        betweenness_centrality: Betweenness centrality scores
        node_metadata: Metadata for each node
        hub_threshold: Minimum centrality to be considered a hub (default: 0.1)

    Returns:
        List of HubNode objects
    """
    hubs: List[HubNode] = []

    if not degree_centrality:
        logger.warning("Hub detection: No nodes with centrality data")
        return hubs

    # Calculate graph statistics
    centrality_values = [float(_to_native(v)) for v in degree_centrality.values()]
    max_cent = max(centrality_values) if centrality_values else 0
    avg_cent = (
        sum(centrality_values) / len(centrality_values) if centrality_values else 0
    )

    # Calculate degree statistics
    attacker_degrees = []
    for node_id in degree_centrality.keys():
        meta = node_metadata.get(node_id, {})
        if meta.get("type") != "honeypot" and G.has_node(node_id):
            attacker_degrees.append(G.degree(node_id))

    avg_degree = (
        sum(attacker_degrees) / len(attacker_degrees) if attacker_degrees else 0
    )
    max_degree = max(attacker_degrees) if attacker_degrees else 0

    # Determine if graph is sparse
    is_sparse_graph = len(degree_centrality) < 100 or avg_degree < 3.0

    logger.info(
        f"Hub detection: {len(degree_centrality)} nodes, "
        f"max_centrality={max_cent:.4f}, avg_centrality={avg_cent:.4f}, "
        f"avg_degree={avg_degree:.2f}, max_degree={max_degree}, sparse={is_sparse_graph}"
    )

    # STRICTER thresholds for hub detection
    # A C&C must have significantly more connections than average
    min_degree_for_hub = max(
        MIN_CONNECTIONS_FOR_HUB,
        int(avg_degree * DEGREE_MULTIPLIER),
    )

    # For very active graphs, require even more
    if max_degree > HIGH_ACTIVITY_THRESHOLD:
        min_degree_for_hub = max(min_degree_for_hub, HIGH_ACTIVITY_MIN_CONNECTIONS)

    logger.info(f"Hub detection: min_degree_for_hub={min_degree_for_hub}")

    # Identify cluster leaders (highest degree node in each cluster with significant connections)
    cluster_leaders: set = set()
    if partition:
        clusters: Dict[int, List[tuple]] = {}
        for node_id, cluster_id in partition.items():
            meta = node_metadata.get(node_id, {})
            if meta.get("type") == "honeypot":
                continue
            cluster_id_native = _to_native(cluster_id)
            if cluster_id_native not in clusters:
                clusters[cluster_id_native] = []
            raw_degree = G.degree(node_id) if G and G.has_node(node_id) else 0
            clusters[cluster_id_native].append((node_id, raw_degree))

        # Get leader from each cluster - but only if they have significant connections
        for cluster_id_key, members in clusters.items():
            if len(members) >= MIN_CLUSTER_SIZE:
                members.sort(key=lambda x: x[1], reverse=True)
                leader_id, leader_degree = members[0]
                if leader_degree >= MIN_LEADER_CONNECTIONS:
                    cluster_leaders.add(leader_id)

        if cluster_leaders:
            logger.info(f"Cluster leaders detected: {len(cluster_leaders)} nodes")

    # Build hub list with STRICT criteria
    for node_id, degree_cent in degree_centrality.items():
        meta = node_metadata.get(node_id, {})

        # Skip honeypot nodes
        if meta.get("type") == "honeypot":
            continue

        # Convert numpy types
        degree_cent_native = float(_to_native(degree_cent))
        betweenness_cent_native = float(
            _to_native(betweenness_centrality.get(node_id, 0.0))
        )

        raw_degree = G.degree(node_id) if G and G.has_node(node_id) else 0

        # Calculate how many different communities this node connects to
        neighbors = list(G.neighbors(node_id)) if G.has_node(node_id) else []
        neighbor_communities = set(
            _to_native(partition.get(n, -1))
            for n in neighbors
            if partition.get(n, -1) != -1
        )
        cross_cluster_connections = len(neighbor_communities)

        # STRICT hub criteria - must meet at least one:
        # 1. High absolute centrality (top performers)
        # 2. Many connections (>= min_degree_for_hub)
        # 3. Cluster leader with cross-cluster connections
        is_high_centrality = (
            degree_cent_native >= hub_threshold
            or betweenness_cent_native >= hub_threshold
        )
        is_high_degree = raw_degree >= min_degree_for_hub
        is_bridge_leader = (
            node_id in cluster_leaders
            and cross_cluster_connections >= MIN_CROSS_CLUSTER_CONNECTIONS
        )

        is_hub_candidate = is_high_centrality or is_high_degree or is_bridge_leader

        if is_hub_candidate:
            # Calculate threat score based on REAL metrics (0-100)
            # Uses configurable weights from ThreatScoreWeights dataclass
            weights = DEFAULT_WEIGHTS
            threat_score = 0.0

            # Base score from centrality
            centrality_score = (
                (degree_cent_native + betweenness_cent_native) / 2
            ) * 200
            threat_score += min(weights.centrality_max, centrality_score)

            # Score from degree relative to average
            if avg_degree > 0:
                degree_ratio = raw_degree / avg_degree
                degree_score = min(weights.degree_ratio_max, degree_ratio * 10)
                threat_score += degree_score

            # Bonus for cross-cluster connections
            cross_cluster_score = (
                cross_cluster_connections * weights.cross_cluster_multiplier
            )
            threat_score += min(weights.cross_cluster_max, cross_cluster_score)

            # Bonus for being cluster leader
            if node_id in cluster_leaders:
                threat_score += weights.leader_bonus

            # Bonus for multi-honeypot targeting (strong C&C indicator)
            if meta.get("multi_honeypot"):
                threat_score += weights.multi_honeypot_bonus
                targeted_count = len(meta.get("targeted_honeypots", []))
                # Extra bonus for each additional honeypot beyond 2
                if targeted_count > 2:
                    threat_score += min(5.0, (targeted_count - 2) * 2)

            # Bonus for high correlation count (indicates coordination)
            correlation_count = meta.get("correlation_count", 0)
            if correlation_count > 0:
                corr_bonus = correlation_count * weights.correlation_multiplier
                threat_score += min(weights.correlation_bonus_max, corr_bonus)

            # Cap at 100
            threat_score = min(100.0, threat_score)

            # Get cluster_id as native type
            raw_cluster = partition.get(node_id)
            cluster_id_str = (
                str(_to_native(raw_cluster)) if raw_cluster is not None else None
            )

            hub = HubNode(
                ip=node_id,
                degree_centrality=degree_cent_native,
                betweenness_centrality=betweenness_cent_native,
                connected_bots=int(raw_degree),
                is_confirmed_cc=threat_score >= CONFIRMED_CC_THRESHOLD,
                threat_score=float(threat_score),
                cluster_id=cluster_id_str,
                country_code=meta.get("country_code"),
                country=meta.get("country"),
                protocols=meta.get("protocols", []),
                first_seen=meta.get("first_seen", datetime.now(timezone.utc)),
                last_seen=meta.get("last_seen", datetime.now(timezone.utc)),
            )
            hubs.append(hub)
            logger.debug(
                f"Hub detected: {node_id} score={threat_score:.1f} "
                f"degree={raw_degree} centrality={degree_cent_native:.4f} "
                f"cross_cluster={cross_cluster_connections} leader={node_id in cluster_leaders}"
            )

    # Sort by threat score descending
    hubs.sort(key=lambda h: h.threat_score, reverse=True)

    logger.info(f"Hub detection complete: {len(hubs)} hubs identified")
    return hubs
