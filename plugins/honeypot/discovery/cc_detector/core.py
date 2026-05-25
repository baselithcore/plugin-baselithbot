"""C&C Detector Core Module."""

from core.observability.logging import get_logger
from typing import Any, Dict, List, Tuple

from ...models import AttackEvent
from ..models import NetworkAnomaly
from .beaconing import detect_beaconing
from .callback import detect_callback_ips
from .dga import detect_dga_domains
from .fastflux import detect_fastflux

logger = get_logger(__name__)


class CCDetector:
    """Detects Command & Control infrastructure patterns."""

    def __init__(
        self,
        dga_entropy_threshold: float = 3.5,
        dga_consonant_ratio: float = 0.7,
        beaconing_interval_tolerance: float = 0.1,
        beaconing_min_occurrences: int = 5,
        fastflux_time_window_seconds: int = 3600,
        fastflux_ip_threshold: int = 3,
    ):
        """Initialize C&C detector.

        Args:
            dga_entropy_threshold: Minimum entropy for DGA domain detection
            dga_consonant_ratio: Maximum consonant ratio for DGA detection
            beaconing_interval_tolerance: Tolerance for beaconing interval matching
            beaconing_min_occurrences: Minimum beacons to detect pattern
            fastflux_time_window_seconds: Time window for fast-flux detection
            fastflux_ip_threshold: Minimum IP changes for fast-flux
        """
        self.dga_entropy_threshold = dga_entropy_threshold
        self.dga_consonant_ratio = dga_consonant_ratio
        self.beaconing_interval_tolerance = beaconing_interval_tolerance
        self.beaconing_min_occurrences = beaconing_min_occurrences
        self.fastflux_time_window_seconds = fastflux_time_window_seconds
        self.fastflux_ip_threshold = fastflux_ip_threshold

        # Analysis results cache
        self._dga_suspects: List[Dict] = []
        self._beaconing_patterns: List[Dict] = []
        self._fastflux_domains: List[Dict] = []
        self._callback_ips: List[Dict] = []

    def analyze_all(
        self, events: List[AttackEvent]
    ) -> Tuple[List[NetworkAnomaly], Dict[str, Any]]:
        """Run all C&C detection analyses.

        Args:
            events: List of attack events to analyze

        Returns:
            Tuple of (detected anomalies, analysis metadata)
        """
        if not events:
            return [], {}

        anomalies: List[NetworkAnomaly] = []
        metadata: Dict[str, Any] = {}

        # 1. DGA detection
        dga_anomalies = detect_dga_domains(
            events, self.dga_entropy_threshold, self.dga_consonant_ratio
        )
        anomalies.extend(dga_anomalies)
        self._dga_suspects = [a.model_dump() for a in dga_anomalies]
        metadata["dga_suspects"] = len(dga_anomalies)

        # 2. Beaconing patterns
        beaconing_anomalies = detect_beaconing(
            events,
            self.beaconing_min_occurrences,
            self.beaconing_interval_tolerance,
        )
        anomalies.extend(beaconing_anomalies)
        self._beaconing_patterns = [a.model_dump() for a in beaconing_anomalies]
        metadata["beaconing_patterns"] = len(beaconing_anomalies)

        # 3. Fast-flux detection
        fastflux_anomalies = detect_fastflux(
            events, self.fastflux_ip_threshold, self.fastflux_time_window_seconds
        )
        anomalies.extend(fastflux_anomalies)
        self._fastflux_domains = [a.model_dump() for a in fastflux_anomalies]
        metadata["fastflux_domains"] = len(fastflux_anomalies)

        # 4. Callback IP detection
        callback_anomalies = detect_callback_ips(events)
        anomalies.extend(callback_anomalies)
        self._callback_ips = [a.model_dump() for a in callback_anomalies]
        metadata["callback_ips"] = len(callback_anomalies)

        logger.info(f"C&C detection complete: {len(anomalies)} indicators detected")

        return anomalies, metadata

    def get_detection_summary(self) -> Dict[str, Any]:
        """Get summary of C&C detection results."""
        return {
            "dga_suspects": len(self._dga_suspects),
            "beaconing_patterns": len(self._beaconing_patterns),
            "fastflux_domains": len(self._fastflux_domains),
            "callback_ips": len(self._callback_ips),
            "total_indicators": (
                len(self._dga_suspects)
                + len(self._beaconing_patterns)
                + len(self._fastflux_domains)
                + len(self._callback_ips)
            ),
        }
