"""CVE Hunter Swarm Signals.

Pheromone signal definitions for swarm coordination.
Uses core/swarm/PheromoneSystem for inter-agent communication.
"""

from core.observability.logging import get_logger
from enum import Enum
from typing import Any, Dict, Optional

logger = get_logger(__name__)


# =============================================================================
# Signal Types
# =============================================================================


class CVESignalType(str, Enum):
    """CVE Hunter pheromone signal types."""

    # Discovery signals
    DISCOVERY_HOTSPOT = "discovery_hotspot"  # Area with active findings
    FALSE_POSITIVE = "false_positive"  # Pattern that's a known false positive
    HIGH_VALUE_TARGET = "high_value_target"  # Target worth investigating

    # Vulnerability signals
    EXPLOIT_AVAILABLE = "exploit_available"  # CVE has confirmed exploit
    ACTIVELY_EXPLOITED = "actively_exploited"  # CVE being exploited in wild
    PATCH_AVAILABLE = "patch_available"  # CVE has patch

    # Coordination signals
    NEED_HELP = "need_help"  # Agent requesting assistance
    TASK_COMPLETE = "task_complete"  # Task finished
    COOLDOWN = "cooldown"  # Source needs rate limit cooldown

    # Learning signals
    SUCCESS_PATTERN = "success_pattern"  # Successful discovery pattern
    FAILURE_PATTERN = "failure_pattern"  # Failed discovery pattern


# =============================================================================
# Signal Locations (contextual identifiers)
# =============================================================================


def cve_location(cve_id: str) -> str:
    """Create location identifier for a CVE."""
    return f"cve:{cve_id}"


def source_location(source_name: str) -> str:
    """Create location identifier for a data source."""
    return f"source:{source_name}"


def pattern_location(pattern: str) -> str:
    """Create location identifier for a vulnerability pattern."""
    return f"pattern:{pattern}"


def task_location(task_id: str) -> str:
    """Create location identifier for a task."""
    return f"task:{task_id}"


# =============================================================================
# Signal Manager
# =============================================================================


class CVESignalManager:
    """Manager for CVE Hunter pheromone signals.

    Wraps core/swarm/PheromoneSystem with CVE-specific signal handling.

    Example:
        ```python
        signals = CVESignalManager(colony.pheromones)
        signals.mark_exploit_available("CVE-2024-1234", intensity=1.0)
        if signals.has_exploit("CVE-2024-1234"):
            prioritize_cve()
        ```
    """

    def __init__(self, pheromone_system: Optional[Any] = None):
        """Initialize signal manager.

        Args:
            pheromone_system: PheromoneSystem instance from Colony
        """
        self._pheromones = pheromone_system
        self._local_signals: Dict[str, Dict[str, float]] = {}

    def set_pheromone_system(self, pheromone_system: Any) -> None:
        """Set the pheromone system (for late binding)."""
        self._pheromones = pheromone_system

    # =========================================================================
    # CVE Signals
    # =========================================================================

    def mark_exploit_available(self, cve_id: str, intensity: float = 1.0) -> None:
        """Mark a CVE as having an available exploit.

        Args:
            cve_id: CVE identifier
            intensity: Signal intensity (0.0-1.0)
        """
        self._deposit(
            CVESignalType.EXPLOIT_AVAILABLE,
            cve_location(cve_id),
            intensity,
        )

    def mark_actively_exploited(self, cve_id: str, intensity: float = 1.0) -> None:
        """Mark a CVE as being actively exploited.

        Args:
            cve_id: CVE identifier
            intensity: Signal intensity
        """
        self._deposit(
            CVESignalType.ACTIVELY_EXPLOITED,
            cve_location(cve_id),
            intensity,
        )

    def mark_patch_available(self, cve_id: str, intensity: float = 1.0) -> None:
        """Mark a CVE as having a patch available.

        Args:
            cve_id: CVE identifier
            intensity: Signal intensity
        """
        self._deposit(
            CVESignalType.PATCH_AVAILABLE,
            cve_location(cve_id),
            intensity,
        )

    def has_exploit(self, cve_id: str, threshold: float = 0.5) -> bool:
        """Check if a CVE has exploit signal.

        Args:
            cve_id: CVE identifier
            threshold: Minimum intensity to consider

        Returns:
            True if exploit signal is above threshold
        """
        signals = self._sense(cve_location(cve_id))
        return signals.get(CVESignalType.EXPLOIT_AVAILABLE.value, 0) >= threshold

    def is_actively_exploited(self, cve_id: str, threshold: float = 0.5) -> bool:
        """Check if a CVE is actively exploited.

        Args:
            cve_id: CVE identifier
            threshold: Minimum intensity

        Returns:
            True if actively exploited
        """
        signals = self._sense(cve_location(cve_id))
        return signals.get(CVESignalType.ACTIVELY_EXPLOITED.value, 0) >= threshold

    # =========================================================================
    # Discovery Signals
    # =========================================================================

    def mark_discovery_hotspot(self, location: str, intensity: float = 1.0) -> None:
        """Mark a location as having active discoveries.

        Args:
            location: Location identifier (source URL, pattern, etc.)
            intensity: Signal intensity
        """
        self._deposit(
            CVESignalType.DISCOVERY_HOTSPOT,
            pattern_location(location),
            intensity,
        )

    def mark_false_positive(self, pattern: str, intensity: float = 1.0) -> None:
        """Mark a pattern as a known false positive.

        Args:
            pattern: Vulnerability pattern
            intensity: Signal intensity
        """
        self._deposit(
            CVESignalType.FALSE_POSITIVE,
            pattern_location(pattern),
            intensity,
        )

    def is_false_positive(self, pattern: str, threshold: float = 0.7) -> bool:
        """Check if pattern is marked as false positive.

        Args:
            pattern: Vulnerability pattern
            threshold: Minimum intensity

        Returns:
            True if pattern is likely false positive
        """
        signals = self._sense(pattern_location(pattern))
        return signals.get(CVESignalType.FALSE_POSITIVE.value, 0) >= threshold

    def get_discovery_hotspots(self, limit: int = 5) -> list[str]:
        """Get locations with strongest discovery signals.

        Args:
            limit: Maximum locations to return

        Returns:
            List of location identifiers
        """
        if not self._pheromones:
            return []

        try:
            # Get all locations with discovery signals
            locations = []
            for loc, signals in self._get_all_signals().items():
                if CVESignalType.DISCOVERY_HOTSPOT.value in signals:
                    locations.append(
                        (loc, signals[CVESignalType.DISCOVERY_HOTSPOT.value])
                    )

            # Sort by intensity descending
            locations.sort(key=lambda x: x[1], reverse=True)
            return [loc for loc, _ in locations[:limit]]
        except Exception:
            return []

    # =========================================================================
    # Coordination Signals
    # =========================================================================

    def request_help(self, task_id: str, intensity: float = 1.0) -> None:
        """Signal that help is needed for a task.

        Args:
            task_id: Task identifier
            intensity: Urgency level
        """
        self._deposit(
            CVESignalType.NEED_HELP,
            task_location(task_id),
            intensity,
        )

    def mark_source_cooldown(self, source: str, intensity: float = 1.0) -> None:
        """Mark a source as needing rate limit cooldown.

        Args:
            source: Source name
            intensity: Cooldown severity
        """
        self._deposit(
            CVESignalType.COOLDOWN,
            source_location(source),
            intensity,
        )

    def is_source_cooling(self, source: str, threshold: float = 0.5) -> bool:
        """Check if source is in cooldown.

        Args:
            source: Source name
            threshold: Minimum intensity

        Returns:
            True if source is cooling down
        """
        signals = self._sense(source_location(source))
        return signals.get(CVESignalType.COOLDOWN.value, 0) >= threshold

    # =========================================================================
    # Learning Signals
    # =========================================================================

    def mark_success_pattern(self, pattern: str, intensity: float = 1.0) -> None:
        """Mark a pattern as successful for discovery.

        Args:
            pattern: Vulnerability pattern
            intensity: Success strength
        """
        self._deposit(
            CVESignalType.SUCCESS_PATTERN,
            pattern_location(pattern),
            intensity,
        )

    def mark_failure_pattern(self, pattern: str, intensity: float = 0.5) -> None:
        """Mark a pattern as failing for discovery.

        Args:
            pattern: Vulnerability pattern
            intensity: Failure strength
        """
        self._deposit(
            CVESignalType.FAILURE_PATTERN,
            pattern_location(pattern),
            intensity,
        )

    def get_successful_patterns(self, limit: int = 10) -> list[str]:
        """Get patterns with success signals.

        Args:
            limit: Maximum patterns to return

        Returns:
            List of successful pattern names
        """
        return self._get_top_locations(CVESignalType.SUCCESS_PATTERN, limit)

    # =========================================================================
    # Internal Methods
    # =========================================================================

    def _deposit(
        self, signal_type: CVESignalType, location: str, intensity: float
    ) -> None:
        """Deposit a pheromone signal.

        Args:
            signal_type: Type of signal
            location: Location identifier
            intensity: Signal intensity
        """
        if self._pheromones:
            try:
                self._pheromones.deposit(
                    signal_type.value, location, intensity=intensity
                )
            except Exception as e:
                logger.debug(f"Failed to deposit signal: {e}")
        else:
            # Fallback to local storage
            if location not in self._local_signals:
                self._local_signals[location] = {}
            current = self._local_signals[location].get(signal_type.value, 0)
            self._local_signals[location][signal_type.value] = min(
                current + intensity, 2.0
            )

    def _sense(self, location: str) -> Dict[str, float]:
        """Sense signals at a location.

        Args:
            location: Location identifier

        Returns:
            Dict of signal types to intensities
        """
        if self._pheromones:
            try:
                return self._pheromones.sense(location)
            except Exception:
                pass  # nosec B110
        return self._local_signals.get(location, {})

    def _get_all_signals(self) -> Dict[str, Dict[str, float]]:
        """Get all signals from all locations."""
        if self._pheromones:
            try:
                return dict(self._pheromones._pheromones)
            except Exception:
                pass  # nosec B110
        return self._local_signals

    def _get_top_locations(self, signal_type: CVESignalType, limit: int) -> list[str]:
        """Get top locations for a signal type.

        Args:
            signal_type: Type of signal
            limit: Maximum locations

        Returns:
            List of location identifiers
        """
        all_signals = self._get_all_signals()
        locations = []

        for loc, signals in all_signals.items():
            if signal_type.value in signals:
                locations.append((loc, signals[signal_type.value]))

        locations.sort(key=lambda x: x[1], reverse=True)
        return [loc for loc, _ in locations[:limit]]
