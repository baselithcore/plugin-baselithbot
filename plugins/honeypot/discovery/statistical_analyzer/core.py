"""Core Statistical Analyzer."""

from core.observability.logging import get_logger
from typing import Any, Dict, List, Tuple

from ...models import AttackEvent
from ..models import NetworkAnomaly
from .geo import detect_geo_clustering
from .iat import detect_iat_patterns
from .packet import detect_packet_size_clusters
from .ttl import detect_ttl_clustering

logger = get_logger(__name__)


class StatisticalAnalyzer:
    """Analyzes statistical indicators to detect coordinated botnet activity."""

    def __init__(
        self,
        ttl_tolerance: int = 5,
        packet_size_tolerance: float = 0.1,
        geo_cluster_threshold: int = 3,
        iat_bucket_ms: int = 100,
    ):
        """Initialize statistical analyzer.

        Args:
            ttl_tolerance: Maximum TTL difference for clustering
            packet_size_tolerance: Relative tolerance for packet size matching (0-1)
            geo_cluster_threshold: Minimum IPs for geographic cluster anomaly
            iat_bucket_ms: Bucket size in ms for inter-arrival time analysis
        """
        self.ttl_tolerance = ttl_tolerance
        self.packet_size_tolerance = packet_size_tolerance
        self.geo_cluster_threshold = geo_cluster_threshold
        self.iat_bucket_ms = iat_bucket_ms

        # Analysis results cache
        self._ttl_clusters: List[Dict] = []
        self._packet_clusters: List[Dict] = []
        self._iat_patterns: List[Dict] = []
        self._geo_clusters: List[Dict] = []

    def analyze_all(
        self, events: List[AttackEvent]
    ) -> Tuple[List[NetworkAnomaly], Dict[str, Any]]:
        """Run all statistical analyses.

        Args:
            events: List of attack events to analyze

        Returns:
            Tuple of (detected anomalies, analysis metadata)
        """
        if not events:
            return [], {}

        anomalies: List[NetworkAnomaly] = []
        metadata: Dict[str, Any] = {}

        # 1. TTL clustering
        ttl_anomalies = detect_ttl_clustering(events, self.ttl_tolerance)
        anomalies.extend(ttl_anomalies)
        self._ttl_clusters = [a.model_dump() for a in ttl_anomalies]
        metadata["ttl_clusters"] = len(ttl_anomalies)

        # 2. Packet size distribution
        packet_anomalies = detect_packet_size_clusters(
            events, self.packet_size_tolerance
        )
        anomalies.extend(packet_anomalies)
        self._packet_clusters = [a.model_dump() for a in packet_anomalies]
        metadata["packet_size_clusters"] = len(packet_anomalies)

        # 3. Inter-arrival time patterns
        iat_anomalies = detect_iat_patterns(events, self.iat_bucket_ms)
        anomalies.extend(iat_anomalies)
        self._iat_patterns = [a.model_dump() for a in iat_anomalies]
        metadata["iat_patterns"] = len(iat_anomalies)

        # 4. Geolocation clustering
        geo_anomalies = detect_geo_clustering(events, self.geo_cluster_threshold)
        anomalies.extend(geo_anomalies)
        self._geo_clusters = [a.model_dump() for a in geo_anomalies]
        metadata["geo_clusters"] = len(geo_anomalies)

        logger.info(
            f"Statistical analysis complete: {len(anomalies)} anomalies detected"
        )

        return anomalies, metadata

    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get summary of statistical analysis results."""
        return {
            "ttl_clusters": len(self._ttl_clusters),
            "packet_size_clusters": len(self._packet_clusters),
            "iat_patterns": len(self._iat_patterns),
            "geo_clusters": len(self._geo_clusters),
            "total_anomalies": (
                len(self._ttl_clusters)
                + len(self._packet_clusters)
                + len(self._iat_patterns)
                + len(self._geo_clusters)
            ),
        }
