"""Core BotnetProfiler logic."""

from core.observability.logging import get_logger
from datetime import datetime
from typing import Any, Dict, List, Optional

from ...models import AttackEvent
from ..models import BotnetCluster, HubNode

from . import evolution, infrastructure, malware, size, tactics
from .signatures import MALWARE_SIGNATURES

logger = get_logger(__name__)


class BotnetProfiler:
    """Provides detailed botnet profiling and characterization."""

    def __init__(self):
        """Initialize profiler with malware signature database."""
        self.signatures = MALWARE_SIGNATURES
        self._profiles: Dict[str, Dict] = {}

    def profile_cluster(
        self,
        cluster: BotnetCluster,
        events: List[AttackEvent],
        hub_nodes: Optional[List[HubNode]] = None,
    ) -> Dict[str, Any]:
        """Generate comprehensive profile for a botnet cluster.

        Args:
            cluster: Botnet cluster to profile
            events: All events (will filter by cluster IPs)
            hub_nodes: Optional hub nodes for C&C identification

        Returns:
            Complete botnet profile dictionary
        """
        # Filter events for this cluster
        cluster_ips = set(cluster.member_ips)
        cluster_events = [e for e in events if e.source_ip in cluster_ips]

        profile = {
            "cluster_id": cluster.cluster_id,
            "profile_generated_at": datetime.now().isoformat(),
            # Size metrics
            "size": size.calculate_size_metrics(cluster, cluster_events),
            # Malware identification
            "malware_family": malware.identify_malware_family(
                cluster_events, self.signatures
            ),
            # C&C infrastructure
            "cc_infrastructure": infrastructure.analyze_cc_infrastructure(
                cluster, hub_nodes, cluster_events
            ),
            # Geographic/ASN analysis
            "infrastructure": infrastructure.analyze_infrastructure(cluster_events),
            # Temporal evolution
            "temporal_evolution": evolution.analyze_temporal_evolution(cluster_events),
            # Attack tactics
            "tactics": tactics.identify_tactics(cluster_events),
            # Confidence score
            "confidence": cluster.detection_confidence,
        }

        self._profiles[cluster.cluster_id] = profile
        return profile

    def get_all_profiles(self) -> Dict[str, Dict]:
        """Get all generated profiles."""
        return self._profiles

    def get_profile(self, cluster_id: str) -> Optional[Dict]:
        """Get profile for specific cluster."""
        return self._profiles.get(cluster_id)
