"""Core Botnet Detector module."""

from core.observability.logging import get_logger
from typing import Any, Dict, List, Tuple

try:
    import networkx as nx

    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    nx = None

from ..models import BotnetCluster, HubNode, NetworkAnomaly
from .anomalies import detect_anomalies
from .clustering import build_clusters
from .communities import detect_communities_label_prop, detect_communities_louvain
from .hubs import identify_hub_nodes

logger = get_logger(__name__)


class BotnetDetector:
    """Detects botnets using graph-based community detection algorithms."""

    def __init__(self):
        """Initialize detector."""
        self._communities: Dict[str, int] = {}
        self._modularity: float = 0.0

    def detect_communities_louvain(
        self, G: "nx.Graph", resolution: float = 1.0
    ) -> Tuple[Dict[str, int], float]:
        """Detect communities using Louvain algorithm.

        Args:
            G: NetworkX graph
            resolution: Resolution parameter (higher = more communities)

        Returns:
            Tuple of (partition dict mapping node to community ID, modularity score)
        """
        partition, modularity = detect_communities_louvain(G, resolution)
        self._communities = partition
        self._modularity = modularity
        return partition, modularity

    def detect_communities_label_prop(self, G: "nx.Graph") -> Dict[str, int]:
        """Detect communities using Label Propagation (faster, less stable).

        Args:
            G: NetworkX graph

        Returns:
            Partition dict mapping node to community ID
        """
        return detect_communities_label_prop(G)

    def identify_hub_nodes(
        self,
        G: "nx.Graph",
        partition: Dict[str, int],
        degree_centrality: Dict[str, float],
        betweenness_centrality: Dict[str, float],
        node_metadata: Dict[str, Dict[str, Any]],
        hub_threshold: float = 0.1,
    ) -> List[HubNode]:
        """Identify potential C&C servers based on centrality metrics.

        Args:
            G: NetworkX graph
            partition: Community partition from Louvain
            degree_centrality: Degree centrality scores
            betweenness_centrality: Betweenness centrality scores
            node_metadata: Metadata for each node
            hub_threshold: Minimum centrality to be considered a hub

        Returns:
            List of HubNode objects
        """
        return identify_hub_nodes(
            G,
            partition,
            degree_centrality,
            betweenness_centrality,
            node_metadata,
            hub_threshold,
        )

    def build_clusters(
        self,
        G: "nx.Graph",
        partition: Dict[str, int],
        hub_nodes: List[HubNode],
        node_metadata: Dict[str, Dict[str, Any]],
        min_cluster_size: int = 2,
    ) -> List[BotnetCluster]:
        """Build BotnetCluster objects from community partition.

        Args:
            G: NetworkX graph
            partition: Community partition
            hub_nodes: Identified hub nodes
            node_metadata: Node metadata
            min_cluster_size: Minimum cluster size to include

        Returns:
            List of BotnetCluster objects
        """
        return build_clusters(
            G,
            partition,
            hub_nodes,
            node_metadata,
            self._modularity,
            min_cluster_size,
        )

    def detect_anomalies(
        self,
        G: "nx.Graph",
        partition: Dict[str, int],
        node_metadata: Dict[str, Dict[str, Any]],
    ) -> List[NetworkAnomaly]:
        """Detect network behavior anomalies.

        Looks for:
        - Geographic clustering anomalies
        - Timing synchronization patterns
        - Unusual protocol distributions
        """
        return detect_anomalies(partition, node_metadata)
