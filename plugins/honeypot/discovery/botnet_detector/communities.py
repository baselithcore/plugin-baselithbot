"""Community detection algorithms for Botnet Detector."""

from core.observability.logging import get_logger
from typing import Dict, Tuple

try:
    import networkx as nx

    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    nx = None

try:
    import community as community_louvain

    HAS_LOUVAIN = True
except ImportError:
    HAS_LOUVAIN = False
    community_louvain = None

logger = get_logger(__name__)


def detect_communities_louvain(
    G: "nx.Graph", resolution: float = 1.0
) -> Tuple[Dict[str, int], float]:
    """Detect communities using Louvain algorithm.

    Args:
        G: NetworkX graph
        resolution: Resolution parameter (higher = more communities)

    Returns:
        Tuple of (partition dict mapping node to community ID, modularity score)
    """
    if not HAS_NETWORKX:
        raise ImportError("NetworkX is required for community detection")

    if G is None or G.number_of_nodes() == 0:
        return {}, 0.0

    if HAS_LOUVAIN:
        # Use python-louvain library for best quality
        raw_partition = community_louvain.best_partition(G, resolution=resolution)
        # Convert numpy.int64 values to native Python int for JSON serialization
        partition = {
            k: int(v) if hasattr(v, "item") else int(v)
            for k, v in raw_partition.items()
        }
        modularity = float(community_louvain.modularity(raw_partition, G))
    else:
        # Fallback to NetworkX's greedy modularity communities
        try:
            from networkx.algorithms.community import greedy_modularity_communities

            communities = list(greedy_modularity_communities(G))
            partition = {}
            for i, comm in enumerate(communities):
                for node in comm:
                    partition[node] = i
            modularity = float(nx.algorithms.community.modularity(G, communities))
        except Exception as e:
            logger.warning(f"Community detection failed: {e}")
            return {}, 0.0

    logger.info(
        f"Detected {len(set(partition.values()))} communities "
        f"with modularity {modularity:.3f}"
    )

    return partition, modularity


def detect_communities_label_prop(G: "nx.Graph") -> Dict[str, int]:
    """Detect communities using Label Propagation (faster, less stable).

    Args:
        G: NetworkX graph

    Returns:
        Partition dict mapping node to community ID
    """
    if not HAS_NETWORKX:
        raise ImportError("NetworkX is required for community detection")

    if G is None or G.number_of_nodes() == 0:
        return {}

    try:
        from networkx.algorithms.community import label_propagation_communities

        communities = list(label_propagation_communities(G))
        partition = {}
        for i, comm in enumerate(communities):
            for node in comm:
                partition[node] = i
        return partition
    except Exception as e:
        logger.warning(f"Label propagation failed: {e}")
        return {}
