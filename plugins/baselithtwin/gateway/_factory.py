"""Backend selection for the :class:`WhatsAppGateway`.

The fake loopback backend is the zero-config default (and what tests use). The
OpenWA REST backend is selected explicitly via plugin config so wiring a real
WhatsApp session is always a deliberate deployment choice.
"""

from __future__ import annotations

from core.observability.logging import get_logger

from ..config import GatewayKind, TwinConfig
from ._fake import FakeGateway
from ._openwa import OpenWAGateway
from ._protocol import WhatsAppGateway

logger = get_logger(__name__)


def build_gateway(config: TwinConfig) -> WhatsAppGateway:
    """Construct the configured gateway backend (does no I/O; call ``connect``)."""
    if config.gateway is GatewayKind.OPENWA:
        logger.info("twin_gateway_backend", backend="openwa")
        from ._resilient import ResilientGateway

        return ResilientGateway(
            OpenWAGateway(
                base_url=config.openwa_base_url,
                session=config.openwa_session,
                api_key=config.openwa_api_key.get_secret_value(),
            )
        )
    logger.info("twin_gateway_backend", backend="fake")
    return FakeGateway()


__all__ = ["build_gateway"]
