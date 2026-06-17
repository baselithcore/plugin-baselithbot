"""Backend selection for the :class:`TwinStore`.

In-memory is the zero-config default (and the test target). Durable Postgres is
strictly opt-in via plugin config (``persistence: postgres``) so enabling it is
a deliberate deployment choice that never changes default or test behaviour.
"""

from __future__ import annotations

from core.observability.logging import get_logger

from ..config import PersistenceKind, TwinConfig
from ._memory import InMemoryTwinStore
from ._protocol import TwinStore

logger = get_logger(__name__)


def build_store(config: TwinConfig) -> TwinStore:
    """Construct the configured store backend (does no I/O; call ``initialize``)."""
    if config.persistence is PersistenceKind.POSTGRES:
        from ._postgres import PostgresTwinStore

        logger.info("twin_store_backend", backend="postgres")
        return PostgresTwinStore()
    logger.info("twin_store_backend", backend="memory")
    return InMemoryTwinStore()


__all__ = ["build_store"]
