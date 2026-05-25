"""Base Notifier Implementation.

Provides abstract base class for different notification providers
with built-in retry logic and circuit breaker pattern.
"""

import abc
import asyncio
from core.observability.logging import get_logger

from .models import AttackNotification, NotificationResult, WebhookProvider

logger = get_logger(__name__)


class BaseNotifier(abc.ABC):
    """Abstract base notifier with resilience patterns."""

    def __init__(self, provider: WebhookProvider, max_retries: int = 3):
        self.provider = provider
        self.max_retries = max_retries
        self._circuit_open = False
        self._failures = 0
        self._circuit_reset_time = 0

    @abc.abstractmethod
    async def send(self, notification: AttackNotification) -> NotificationResult:
        """Send notification to the provider.

        Must be implemented by concrete classes.
        """
        pass

    async def _send_with_retry(self, func, *args, **kwargs) -> NotificationResult:
        """Execute send function with retry logic."""
        if self._circuit_open:
            import time

            if time.time() < self._circuit_reset_time:
                return NotificationResult(
                    provider=self.provider, success=False, error="Circuit breaker open"
                )
            self._circuit_open = False
            self._failures = 0

        start_time = asyncio.get_event_loop().time()

        for attempt in range(self.max_retries):
            try:
                result = await func(*args, **kwargs)
                if result:
                    self._failures = 0
                    duration = (asyncio.get_event_loop().time() - start_time) * 1000
                    return NotificationResult(
                        provider=self.provider, success=True, duration_ms=duration
                    )
            except Exception as e:
                logger.warning(
                    f"Notification attempt {attempt + 1} failed for {self.provider}: {e}"
                )
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2**attempt)  # Exponential backoff

        # If all retries fail
        self._failures += 1
        if self._failures >= 5:
            import time

            self._circuit_open = True
            self._circuit_reset_time = time.time() + 300  # 5 min cooldown
            logger.error(f"Circuit breaker opened for {self.provider}")

        return NotificationResult(
            provider=self.provider,
            success=False,
            error=f"Max retries ({self.max_retries}) exceeded",
        )
