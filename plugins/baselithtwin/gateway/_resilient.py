"""A resilience decorator for any :class:`WhatsAppGateway`.

Wraps a concrete gateway (e.g. OpenWA) with the framework's circuit breaker and
exponential-backoff retry so a flapping WhatsApp sidecar can't wedge the ingest
path or silently drop sends. Composition, not inheritance: the wrapper satisfies
the same Protocol and delegates lifecycle calls untouched, hardening only
``send`` — the one network mutation that matters.

A send that the underlying gateway reports as failed is raised internally so the
breaker can observe it; once retries are exhausted (or the breaker is open) the
wrapper degrades to a failed :class:`SendReceipt`, never raising into the caller.
"""

from __future__ import annotations

from core.observability.logging import get_logger
from core.resilience.circuit_breaker import CircuitBreakerConfig, get_circuit_breaker
from core.resilience.retry import retry

from ._protocol import WhatsAppGateway
from .models import OutboundMessage, SendReceipt

logger = get_logger(__name__)


class _SendError(RuntimeError):
    """Internal signal that an underlying send failed (drives retry/breaker)."""


class ResilientGateway:
    """Decorates a gateway with circuit-breaking + retry around ``send``."""

    def __init__(
        self,
        inner: WhatsAppGateway,
        *,
        name: str = "twin_gateway",
        max_attempts: int = 3,
        fail_max: int = 5,
        reset_timeout: int = 30,
    ) -> None:
        self._inner = inner
        self._max_attempts = max_attempts
        self._breaker = get_circuit_breaker(
            name, CircuitBreakerConfig(fail_max=fail_max, reset_timeout=reset_timeout)
        )

    async def connect(self) -> None:
        await self._inner.connect()

    async def disconnect(self) -> None:
        await self._inner.disconnect()

    async def is_connected(self) -> bool:
        return await self._inner.is_connected()

    async def send(self, message: OutboundMessage) -> SendReceipt:
        """Send with breaker + retry; degrade to a failed receipt on exhaustion."""

        @retry(max_attempts=self._max_attempts, retryable_exceptions=(_SendError,))
        async def _attempt() -> SendReceipt:
            receipt = await self._inner.send(message)
            if not receipt.ok:
                raise _SendError(receipt.error or "send failed")
            return receipt

        try:
            return await self._breaker.async_call(_attempt)
        except Exception as exc:  # noqa: BLE001 — never raise into ingest/HITL
            logger.warning("twin_gateway_send_exhausted", error=str(exc))
            return SendReceipt(ok=False, error=str(exc))


__all__ = ["ResilientGateway"]
