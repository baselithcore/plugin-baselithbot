"""Core ML Analyzer logic."""

from core.observability.logging import get_logger
from typing import Any, Dict, List, Tuple

from ...models import AttackEvent
from ..models import NetworkAnomaly

from . import anomaly, clustering, sequence, timeseries
from .utils import HAS_SKLEARN

logger = get_logger(__name__)


class MLAnalyzer:
    """ML-based attack pattern analysis."""

    def __init__(
        self,
        dbscan_eps: float = 0.5,
        dbscan_min_samples: int = 3,
        kmeans_n_clusters: int = 5,
        isolation_contamination: float = 0.1,
        sequence_window: int = 5,
    ):
        """Initialize ML analyzer.

        Args:
            dbscan_eps: DBSCAN epsilon (neighborhood radius)
            dbscan_min_samples: Minimum samples for DBSCAN cluster
            kmeans_n_clusters: Number of clusters for K-means
            isolation_contamination: Expected outlier fraction for Isolation Forest
            sequence_window: Window size for sequence analysis
        """
        self.dbscan_eps = dbscan_eps
        self.dbscan_min_samples = dbscan_min_samples
        self.kmeans_n_clusters = kmeans_n_clusters
        self.isolation_contamination = isolation_contamination
        self.sequence_window = sequence_window

        # Results cache
        self._attack_clusters: List[Dict] = []
        self._anomalies: List[Dict] = []
        self._sequences: List[Dict] = []
        self._time_patterns: List[Dict] = []

    def analyze_all(
        self, events: List[AttackEvent]
    ) -> Tuple[List[NetworkAnomaly], Dict[str, Any]]:
        """Run all ML analyses.

        Args:
            events: Attack events to analyze

        Returns:
            Tuple of (detected anomalies, analysis metadata)
        """
        if not events or len(events) < 5:
            return [], {"error": "Insufficient data for ML analysis"}

        anomalies: List[NetworkAnomaly] = []
        metadata: Dict[str, Any] = {}

        # Check if sklearn is available
        if not HAS_SKLEARN:
            logger.warning("scikit-learn not installed, using fallback algorithms")
            # Run fallback implementations
            cluster_anomalies = clustering.fallback_clustering(events)
            anomalies.extend(cluster_anomalies)
            metadata["clustering"] = {
                "method": "fallback",
                "clusters": len(cluster_anomalies),
            }
        else:
            # 1. Attack clustering (DBSCAN)
            cluster_anomalies, cluster_meta = clustering.cluster_attacks_dbscan(
                events, eps=self.dbscan_eps, min_samples=self.dbscan_min_samples
            )
            anomalies.extend(cluster_anomalies)
            metadata["dbscan_clustering"] = cluster_meta
            if cluster_anomalies:
                self._attack_clusters = [a.model_dump() for a in cluster_anomalies]

            # 2. Anomaly detection (Isolation Forest)
            outlier_anomalies, outlier_meta = anomaly.detect_anomalies_isolation_forest(
                events, contamination=self.isolation_contamination
            )
            anomalies.extend(outlier_anomalies)
            metadata["isolation_forest"] = outlier_meta
            if outlier_anomalies:
                self._anomalies = [a.model_dump() for a in outlier_anomalies]

        # 3. Sequence analysis (no sklearn needed)
        sequence_anomalies, sequence_meta = sequence.analyze_attack_sequences(
            events, window_size=self.sequence_window
        )
        anomalies.extend(sequence_anomalies)
        metadata["sequence_analysis"] = sequence_meta
        if sequence_anomalies:
            self._sequences = [a.model_dump() for a in sequence_anomalies]

        # 4. Time series analysis (no sklearn needed)
        time_anomalies, time_meta = timeseries.analyze_time_patterns(events)
        anomalies.extend(time_anomalies)
        metadata["time_series"] = time_meta
        if time_anomalies:
            self._time_patterns = [a.model_dump() for a in time_anomalies]

        logger.info(f"ML analysis complete: {len(anomalies)} anomalies detected")

        return anomalies, metadata

    def get_analysis_summary(self) -> Dict[str, Any]:
        """Get summary of ML analysis results."""
        return {
            "attack_clusters": len(self._attack_clusters),
            "outliers_detected": len(self._anomalies),
            "attack_sequences": len(self._sequences),
            "time_patterns": len(self._time_patterns),
            "sklearn_available": HAS_SKLEARN,
        }
