"""Latency Modeler for Sophisticated Emulation.

Models realistic response latency patterns per OS and operation type
to defeat timing-based honeypot fingerprinting.

The latency model uses a truncated Gaussian distribution with
per-operation multipliers to simulate realistic system behavior.
"""

import asyncio
from core.observability.logging import get_logger
import random
from typing import Optional

from .models import FingerprintProfile, OperationType

logger = get_logger(__name__)


class LatencyModeler:
    """Models realistic latency patterns per OS and operation type.

    Prevents detection by timing-based fingerprinting through:
    - Gaussian distribution of response times
    - Operation-specific latency profiles
    - Configurable jitter and bounds

    Example:
        >>> modeler = LatencyModeler(profile)
        >>> await modeler.simulate(OperationType.FILESYSTEM_READ)
        # Applies realistic delay before returning
    """

    def __init__(
        self,
        profile: Optional[FingerprintProfile] = None,
        enabled: bool = True,
        multiplier: float = 1.0,
    ):
        """Initialize latency modeler.

        Args:
            profile: Fingerprint profile with latency parameters
            enabled: Whether to apply latency (for testing/debugging)
            multiplier: Global multiplier for all latencies
        """
        self.profile = profile or FingerprintProfile.get_default()
        self.enabled = enabled
        self.multiplier = multiplier

        # Cache operation multipliers
        self._op_multipliers = self.profile.latency_multipliers

        logger.debug(
            f"LatencyModeler initialized: mean={self.profile.latency_mean_ms}ms, "
            f"std={self.profile.latency_std_ms}ms, enabled={enabled}"
        )

    async def simulate(
        self,
        operation: OperationType = OperationType.GENERIC,
        custom_base_ms: Optional[float] = None,
    ) -> float:
        """Apply realistic delay before returning.

        Args:
            operation: Type of operation being simulated
            custom_base_ms: Override base delay (for per-command tuning)

        Returns:
            Actual delay applied in milliseconds
        """
        if not self.enabled:
            return 0.0

        # Calculate base delay
        if custom_base_ms is not None:
            base_delay = custom_base_ms
        else:
            base_delay = self._get_base_delay(operation)

        # Add Gaussian jitter
        jitter = random.gauss(0, self.profile.latency_std_ms)

        # Apply global multiplier
        total_delay = (base_delay + jitter) * self.multiplier

        # Clamp to bounds
        total_delay = max(
            self.profile.latency_min_ms, min(total_delay, self.profile.latency_max_ms)
        )

        # Apply delay
        if total_delay > 0:
            await asyncio.sleep(total_delay / 1000.0)

        logger.debug(
            f"Latency applied: operation={operation.value}, "
            f"base={base_delay:.1f}ms, total={total_delay:.1f}ms"
        )

        return total_delay

    def _get_base_delay(self, operation: OperationType) -> float:
        """Get base delay in ms for operation type.

        Args:
            operation: Operation type (enum or string)

        Returns:
            Base delay in milliseconds
        """
        # Handle both enum and string values
        op_value = operation.value if hasattr(operation, "value") else str(operation)
        multiplier = self._op_multipliers.get(
            op_value, self._op_multipliers.get("generic", 1.0)
        )
        return self.profile.latency_mean_ms * multiplier

    def estimate_delay(self, operation: OperationType) -> float:
        """Estimate delay without applying it (for planning).

        Args:
            operation: Operation type

        Returns:
            Estimated delay in milliseconds
        """
        return self._get_base_delay(operation) * self.multiplier

    def simulate_sync(self, operation: OperationType = OperationType.GENERIC) -> float:
        """Synchronous delay (blocking, for non-async contexts).

        Warning:
            This uses time.sleep which blocks the event loop.
            Use `simulate()` in async contexts.

        Args:
            operation: Operation type

        Returns:
            Actual delay applied in milliseconds
        """
        import time

        if not self.enabled:
            return 0.0

        base_delay = self._get_base_delay(operation)
        jitter = random.gauss(0, self.profile.latency_std_ms)
        total_delay = max(
            self.profile.latency_min_ms,
            min((base_delay + jitter) * self.multiplier, self.profile.latency_max_ms),
        )

        if total_delay > 0:
            time.sleep(total_delay / 1000.0)

        return total_delay

    def with_profile(self, profile: FingerprintProfile) -> "LatencyModeler":
        """Create new modeler with different profile.

        Args:
            profile: New fingerprint profile

        Returns:
            New LatencyModeler instance
        """
        return LatencyModeler(
            profile=profile,
            enabled=self.enabled,
            multiplier=self.multiplier,
        )

    def with_multiplier(self, multiplier: float) -> "LatencyModeler":
        """Create new modeler with different multiplier.

        Args:
            multiplier: New global multiplier

        Returns:
            New LatencyModeler instance
        """
        return LatencyModeler(
            profile=self.profile,
            enabled=self.enabled,
            multiplier=multiplier,
        )

    def disable(self) -> "LatencyModeler":
        """Create disabled copy (for testing).

        Returns:
            New LatencyModeler with enabled=False
        """
        return LatencyModeler(
            profile=self.profile,
            enabled=False,
            multiplier=self.multiplier,
        )


class AdaptiveLatencyModeler(LatencyModeler):
    """Extended latency modeler that adapts based on attacker behavior.

    If the attacker is moving quickly (automated tool), increase delays
    to slow them down and increase dwell time. If moving slowly (manual),
    keep delays minimal to avoid suspicion.
    """

    def __init__(
        self,
        profile: Optional[FingerprintProfile] = None,
        enabled: bool = True,
        multiplier: float = 1.0,
        adaptive_threshold_ms: float = 500.0,
    ):
        """Initialize adaptive latency modeler.

        Args:
            profile: Fingerprint profile
            enabled: Whether to apply latency
            multiplier: Base multiplier
            adaptive_threshold_ms: Threshold for adaptive behavior
        """
        super().__init__(profile, enabled, multiplier)
        self.adaptive_threshold_ms = adaptive_threshold_ms
        self._recent_command_times: list = []
        self._max_history = 10

    def record_command_timing(self, delay_since_last_ms: float) -> None:
        """Record timing of command for adaptive behavior.

        Args:
            delay_since_last_ms: Time since last command
        """
        self._recent_command_times.append(delay_since_last_ms)
        if len(self._recent_command_times) > self._max_history:
            self._recent_command_times.pop(0)

    def _get_adaptive_multiplier(self) -> float:
        """Calculate adaptive multiplier based on attacker speed.

        Returns:
            Multiplier to apply (1.0-3.0 range)
        """
        if len(self._recent_command_times) < 3:
            return 1.0

        avg_delay = sum(self._recent_command_times) / len(self._recent_command_times)

        if avg_delay < self.adaptive_threshold_ms:
            # Fast attacker (likely automated) - slow them down
            return min(3.0, self.adaptive_threshold_ms / max(avg_delay, 100))
        else:
            # Slow attacker (likely manual) - stay realistic
            return 1.0

    async def simulate(
        self,
        operation: OperationType = OperationType.GENERIC,
        custom_base_ms: Optional[float] = None,
    ) -> float:
        """Apply adaptive delay.

        Adjusts delay based on attacker's command frequency.
        """
        adaptive_mult = self._get_adaptive_multiplier()
        original_mult = self.multiplier

        try:
            self.multiplier = original_mult * adaptive_mult
            return await super().simulate(operation, custom_base_ms)
        finally:
            self.multiplier = original_mult
