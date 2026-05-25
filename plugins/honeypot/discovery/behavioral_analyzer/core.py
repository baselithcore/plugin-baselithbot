"""Behavioral Analyzer Core Module."""

from core.observability.logging import get_logger
from typing import Any, Dict, List, Tuple

from ...models import AttackEvent
from ..models import NetworkAnomaly
from .command import detect_command_sequences
from .payload import compute_payload_hash, compute_similarity, detect_payload_similarity
from .scan import detect_scan_patterns
from .target import detect_target_correlation
from .timing import detect_timing_sync

logger = get_logger(__name__)


class BehavioralAnalyzer:
    """Analyzes behavioral patterns to detect coordinated attack activity."""

    def __init__(
        self,
        timing_window_seconds: int = 30,
        payload_similarity_threshold: float = 0.9,
        min_correlation_group_size: int = 2,
    ):
        """Initialize behavioral analyzer.

        Args:
            timing_window_seconds: Time window for synchronized attack detection
            payload_similarity_threshold: Minimum similarity for payload matching (0-1)
            min_correlation_group_size: Minimum IPs to form a correlation group
        """
        self.timing_window_seconds = timing_window_seconds
        self.payload_similarity_threshold = payload_similarity_threshold
        self.min_correlation_group_size = min_correlation_group_size

        # Cache for analysis results
        self._timing_correlations: List[Dict] = []
        self._payload_clusters: List[Dict] = []
        self._target_correlations: List[Dict] = []
        self._scan_patterns: List[Dict] = []
        self._command_sequences: List[Dict] = []

    def analyze_all(
        self, events: List[AttackEvent]
    ) -> Tuple[List[NetworkAnomaly], Dict[str, Any]]:
        """Run all behavioral correlation analyses.

        Args:
            events: List of attack events to analyze

        Returns:
            Tuple of (detected anomalies, correlation metadata)
        """
        if not events:
            return [], {}

        anomalies: List[NetworkAnomaly] = []
        metadata: Dict[str, Any] = {}

        # 1. Timing analysis
        timing_anomalies = detect_timing_sync(
            events, self.timing_window_seconds, self.min_correlation_group_size
        )
        anomalies.extend(timing_anomalies)
        self._timing_correlations = [a.model_dump() for a in timing_anomalies]
        metadata["timing_correlations"] = len(timing_anomalies)

        # 2. Payload similarity
        payload_anomalies = detect_payload_similarity(
            events,
            self.payload_similarity_threshold,
            self.min_correlation_group_size,
        )
        anomalies.extend(payload_anomalies)
        self._payload_clusters = [a.model_dump() for a in payload_anomalies]
        metadata["payload_clusters"] = len(payload_anomalies)

        # 3. Target correlation
        target_anomalies = detect_target_correlation(
            events, self.min_correlation_group_size
        )
        anomalies.extend(target_anomalies)
        self._target_correlations = [a.model_dump() for a in target_anomalies]
        metadata["target_correlations"] = len(target_anomalies)

        # 4. Scan patterns
        scan_anomalies = detect_scan_patterns(events, self.min_correlation_group_size)
        anomalies.extend(scan_anomalies)
        self._scan_patterns = [a.model_dump() for a in scan_anomalies]
        metadata["scan_patterns"] = len(scan_anomalies)

        # 5. Command sequences
        command_anomalies = detect_command_sequences(
            events, self.min_correlation_group_size
        )
        anomalies.extend(command_anomalies)
        self._command_sequences = [a.model_dump() for a in command_anomalies]
        metadata["command_sequences"] = len(command_anomalies)

        logger.info(
            f"Behavioral analysis complete: {len(anomalies)} total anomalies detected"
        )

        return anomalies, metadata

    def get_correlation_summary(self) -> Dict[str, Any]:
        """Get summary of all detected correlations."""
        return {
            "timing_correlations": len(self._timing_correlations),
            "payload_clusters": len(self._payload_clusters),
            "target_correlations": len(self._target_correlations),
            "scan_patterns": len(self._scan_patterns),
            "command_sequences": len(self._command_sequences),
            "total_anomalies": (
                len(self._timing_correlations)
                + len(self._payload_clusters)
                + len(self._target_correlations)
                + len(self._scan_patterns)
                + len(self._command_sequences)
            ),
        }

    # Proxy methods to keep backward compatibility or expose functionality
    def _compute_similarity(self, payload1: str, payload2: str) -> float:
        """Proxy for compute_similarity."""
        return compute_similarity(payload1, payload2)

    def _compute_payload_hash(self, payload: str) -> str:
        """Proxy for compute_payload_hash."""
        return compute_payload_hash(payload)
