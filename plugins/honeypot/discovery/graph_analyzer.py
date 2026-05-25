"""Graph Analyzer - Core graph analysis utilities.

Builds attack graphs from honeypot data and provides centrality metrics.
Includes advanced attacker correlation detection for botnet identification.
"""

from typing import Any, Dict, List, Optional, Set, Tuple, TYPE_CHECKING
from core.observability.logging import get_logger
from collections import defaultdict

try:
    import networkx as nx

    HAS_NETWORKX = True
except ImportError:
    HAS_NETWORKX = False
    nx = None

from ..models import AttackEvent
from .correlation_analyzer import CorrelationAnalyzer

if TYPE_CHECKING:
    from ..persistence import HoneypotDAO

logger = get_logger(__name__)


class GraphAnalyzer:
    """Analyzes attack patterns using graph-based algorithms.

    Includes advanced correlation detection for identifying coordinated attacks.
    """

    def __init__(self, dao: Optional["HoneypotDAO"] = None):
        """Initialize analyzer with data access object."""
        self.dao = dao
        self._graph: Optional[Any] = None  # NetworkX graph
        self._node_metadata: Dict[str, Dict[str, Any]] = {}
        self._events: List[AttackEvent] = []  # Cache events for behavioral analysis
        self._correlation_analyzer = CorrelationAnalyzer()
        self._correlation_metadata: Dict[str, Any] = {}

        if not HAS_NETWORKX:
            logger.warning(
                "NetworkX not installed. Install with: pip install networkx python-louvain"
            )

    def _ensure_networkx(self) -> bool:
        """Check if NetworkX is available."""
        if not HAS_NETWORKX:
            raise ImportError(
                "NetworkX is required for graph analysis. "
                "Install with: pip install networkx python-louvain"
            )
        return True

    async def build_attack_graph(
        self,
        events: Optional[List[AttackEvent]] = None,
        honeypot_id: Optional[str] = None,
        time_window_hours: int = 24,
    ) -> "nx.Graph":
        """Build a NetworkX graph from attack events.

        Nodes: IP addresses (attackers) and honeypot IDs
        Edges: Attack connections weighted by frequency

        Args:
            events: Optional list of events (fetched if not provided)
            honeypot_id: Filter events by honeypot
            time_window_hours: Time window for event analysis

        Returns:
            NetworkX Graph object
        """
        self._ensure_networkx()

        if events is None and self.dao:
            # Fetch recent events from database
            events = await self._fetch_events(honeypot_id, time_window_hours)
        elif events is None:
            events = []

        # Cache events for behavioral analysis
        self._events = events

        G = nx.Graph()
        self._node_metadata = {}

        # Track edge weights (connection counts)
        edge_weights: Dict[Tuple[str, str], int] = defaultdict(int)

        # Build graph from events
        for event in events:
            source_ip = event.source_ip
            target_id = event.honeypot_id

            # Add attacker node with metadata
            if source_ip not in self._node_metadata:
                self._node_metadata[source_ip] = {
                    "type": "attacker",
                    "protocols": set(),
                    "severities": set(),
                    "attack_count": 0,
                    "country_code": event.geo.country_code if event.geo else None,
                    "country": event.geo.country if event.geo else None,
                    "first_seen": event.timestamp,
                    "last_seen": event.timestamp,
                }
            else:
                # Update timestamps
                if event.timestamp < self._node_metadata[source_ip]["first_seen"]:
                    self._node_metadata[source_ip]["first_seen"] = event.timestamp
                if event.timestamp > self._node_metadata[source_ip]["last_seen"]:
                    self._node_metadata[source_ip]["last_seen"] = event.timestamp

            self._node_metadata[source_ip]["protocols"].add(
                event.protocol.value
                if hasattr(event.protocol, "value")
                else str(event.protocol)
            )
            self._node_metadata[source_ip]["severities"].add(
                event.severity.value
                if hasattr(event.severity, "value")
                else str(event.severity)
            )
            self._node_metadata[source_ip]["attack_count"] += 1

            # Add honeypot node
            if target_id not in self._node_metadata:
                self._node_metadata[target_id] = {
                    "type": "honeypot",
                    "protocols": set(),
                }
            self._node_metadata[target_id]["protocols"].add(
                event.protocol.value
                if hasattr(event.protocol, "value")
                else str(event.protocol)
            )

            # Track edge weight
            edge_key = tuple(sorted([source_ip, target_id]))
            edge_weights[edge_key] += 1

            # Also track attacker-to-attacker connections based on timing
            # (Attackers hitting same target within a time window may be coordinated)

        # Add nodes to graph
        for node_id, metadata in self._node_metadata.items():
            # Convert sets to lists for serialization
            meta_copy = metadata.copy()
            if "protocols" in meta_copy:
                meta_copy["protocols"] = list(meta_copy["protocols"])
            if "severities" in meta_copy:
                meta_copy["severities"] = list(meta_copy["severities"])
            G.add_node(node_id, **meta_copy)

        # Add edges with weights
        for (src, tgt), weight in edge_weights.items():
            G.add_edge(src, tgt, weight=weight)

        # Build attacker co-occurrence graph (attackers targeting same honeypot)
        self._add_attacker_correlations(G, events)

        self._graph = G
        logger.info(
            f"Built attack graph: {G.number_of_nodes()} nodes, {G.number_of_edges()} edges"
        )

        return G

    def _add_attacker_correlations(
        self, G: "nx.Graph", events: List[AttackEvent]
    ) -> None:
        """Add edges between correlated attackers using advanced correlation detection.

        Uses CorrelationAnalyzer to detect:
        - Timing correlations (same target, similar time)
        - Pattern correlations (similar commands/payloads)
        - Cross-honeypot correlations (targeting multiple honeypots)
        - Infrastructure correlations (same subnet)
        """
        if not events:
            return

        # Run correlation analysis
        correlations, metadata = self._correlation_analyzer.analyze(events)
        self._correlation_metadata = metadata

        # Add attacker-attacker edges based on correlations
        for corr in correlations:
            ip1, ip2 = corr.source_ip, corr.target_ip

            # Skip if either node isn't in graph (shouldn't happen, but safe)
            if not G.has_node(ip1) or not G.has_node(ip2):
                continue

            if G.has_edge(ip1, ip2):
                # Update existing edge
                G[ip1][ip2]["weight"] += 1
                G[ip1][ip2]["correlated"] = True
                # Keep highest confidence
                if corr.confidence > G[ip1][ip2].get("correlation_confidence", 0):
                    G[ip1][ip2]["correlation_confidence"] = corr.confidence
                    G[ip1][ip2]["correlation_type"] = corr.correlation_type.value
            else:
                # Add new edge
                G.add_edge(
                    ip1,
                    ip2,
                    weight=1,
                    correlated=True,
                    correlation_type=corr.correlation_type.value,
                    correlation_confidence=corr.confidence,
                )

        # Enrich node metadata with cross-honeypot targeting info
        multi_hp_ips = self._correlation_analyzer.get_multi_honeypot_ips()
        for ip, honeypots in multi_hp_ips.items():
            if ip in self._node_metadata:
                self._node_metadata[ip]["targeted_honeypots"] = list(honeypots)
                self._node_metadata[ip]["multi_honeypot"] = True

        # Add correlation counts to nodes for threat scoring
        corr_counts = self._correlation_analyzer.get_ip_correlation_count()
        for ip, count in corr_counts.items():
            if ip in self._node_metadata:
                self._node_metadata[ip]["correlation_count"] = count

        logger.info(
            f"Added {len(correlations)} attacker correlations to graph "
            f"({metadata.get('timing_correlations', 0)} timing, "
            f"{metadata.get('pattern_correlations', 0)} pattern, "
            f"{metadata.get('cross_honeypot_correlations', 0)} cross-HP)"
        )

    async def _fetch_events(
        self, honeypot_id: Optional[str], hours: int
    ) -> List[AttackEvent]:
        """Fetch events from database."""
        if not self.dao:
            logger.warning("No DAO configured, cannot fetch events")
            return []

        try:
            # Calculate start time based on window
            from datetime import timedelta, datetime, timezone

            start_time = datetime.now(timezone.utc) - timedelta(hours=hours)
            logger.info(
                f"Fetching events: honeypot_id={honeypot_id}, hours={hours}, start_time={start_time}"
            )

            result = await self.dao.get_events(
                page=1, page_size=10000, honeypot_id=honeypot_id, start_time=start_time
            )

            if isinstance(result, tuple):
                events, total = result
                logger.info(f"Fetched {len(events)} events (total in DB: {total})")
                return events
            else:
                items = result.get("items", [])
                logger.info(f"Fetched {len(items)} events (dict format)")
                return items
        except Exception as e:
            logger.error(f"Failed to fetch events: {e}", exc_info=True)
            return []

    def compute_degree_centrality(
        self, G: Optional["nx.Graph"] = None
    ) -> Dict[str, float]:
        """Compute degree centrality for all nodes.

        Higher values indicate nodes with many connections (potential C&C servers).
        """
        self._ensure_networkx()
        G = G or self._graph
        if G is None:
            return {}

        return nx.degree_centrality(G)

    def compute_betweenness_centrality(
        self, G: Optional["nx.Graph"] = None
    ) -> Dict[str, float]:
        """Compute betweenness centrality for all nodes.

        Higher values indicate nodes that act as bridges/communication hubs.
        """
        self._ensure_networkx()
        G = G or self._graph
        if G is None:
            return {}

        return nx.betweenness_centrality(G, weight="weight")

    def find_dense_subgraphs(
        self, G: Optional["nx.Graph"] = None, min_density: float = 0.5
    ) -> List[Set[str]]:
        """Find dense subgraphs (potential coordinated bot clusters).

        Uses k-core decomposition to find densely connected regions.
        """
        self._ensure_networkx()
        G = G or self._graph
        if G is None:
            return []

        dense_subgraphs = []

        # Find k-cores (maximal subgraphs where each node has >= k neighbors)
        for k in range(2, 10):
            try:
                core = nx.k_core(G, k=k)
                if core.number_of_nodes() >= 3:
                    # Check density
                    density = nx.density(core)
                    if density >= min_density:
                        dense_subgraphs.append(set(core.nodes()))
            except nx.NetworkXError:
                break

        return dense_subgraphs

    def get_node_metadata(self, node_id: str) -> Dict[str, Any]:
        """Get metadata for a specific node."""
        return self._node_metadata.get(node_id, {})

    def get_graph(self) -> Optional["nx.Graph"]:
        """Get the current graph."""
        return self._graph

    def get_attacker_nodes(self) -> List[str]:
        """Get list of attacker node IDs."""
        return [
            node_id
            for node_id, meta in self._node_metadata.items()
            if meta.get("type") == "attacker"
        ]

    def generate_embeddings(self) -> Dict[str, List[float]]:
        """
        Generate feature vectors (embeddings) for all nodes (GNN-ready).

        Features:
        1. Threat Score (normalized)
        2. JA4 Fingerprint Hash (integer representation)
        3. Request Rate Variance
        4. Degree Centrality
        5. Betweenness Centrality
        """
        self._ensure_networkx()
        if not self._graph:
            return {}

        embeddings = {}
        degree_cent = nx.degree_centrality(self._graph)

        # Calculate betweenness efficiently (k=100 for approx) if graph is large
        try:
            between_cent = nx.betweenness_centrality(
                self._graph, k=min(100, len(self._graph))
            )
        except Exception:
            between_cent = {n: 0.0 for n in self._graph.nodes()}

        for node in self._graph.nodes():
            meta = self._node_metadata.get(node, {})

            # 1. Threat Score (Placeholder, default 0.5)
            threat_score = (
                meta.get("threat_score", 0.0) / 100.0
            )  # Normalize 0-100 -> 0-1

            # 2. JA4 Hash (Simple numeric hash of the string)
            ja4 = meta.get("ja4_fingerprint", "")
            ja4_val = (hash(ja4) % 1000) / 1000.0 if ja4 else 0.0

            # 3. Variance (Placeholder)
            variance = 0.0  # meta.get("request_variance", 0.0)

            # 4. Topology capabilities
            deg = degree_cent.get(node, 0.0)
            bet = between_cent.get(node, 0.0)

            # Vector
            embeddings[node] = [threat_score, ja4_val, variance, deg, bet]

        return embeddings

    def detect_communities(self) -> Dict[str, int]:
        """
        Detect communities/clusters using Louvain algorithm.
        Returns: {node_id: community_id}
        """
        self._ensure_networkx()
        if not self._graph:
            return {}

        try:
            import community.community_louvain as community_louvain
        except ImportError:
            logger.warning(
                "python-louvain not installed. Skipping community detection."
            )
            return {n: 0 for n in self._graph.nodes()}

        try:
            # Louvain requires undirected graph
            partition = community_louvain.best_partition(self._graph)
            logger.info(
                f"Detected {len(set(partition.values()))} communities using Louvain"
            )
            return partition
        except Exception as e:
            logger.error(f"Community detection failed: {e}")
            return {n: 0 for n in self._graph.nodes()}

    def get_events(self) -> List[AttackEvent]:
        """Get cached events from last graph build."""
        return self._events
