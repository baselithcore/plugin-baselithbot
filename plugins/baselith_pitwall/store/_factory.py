"""Backend selection for the :class:`PitwallStore`.

The in-memory backend is the zero-config default (and what the tests rely on).
Durable Postgres persistence is strictly opt-in — selected via plugin config
(``persistence: postgres``) or the ``BASELITH_PITWALL_PERSISTENCE`` env var — so
enabling it is a deliberate deployment choice that never changes default or test
behaviour.
"""

from __future__ import annotations

import os
from typing import Any

from core.observability.logging import get_logger

from ._memory import InMemoryPitwallStore
from ._postgres import PostgresPitwallStore
from ._protocol import PitwallStore

logger = get_logger(__name__)

_VALID = ("memory", "postgres")


def resolve_persistence(config: dict[str, Any] | None = None) -> str:
    """Resolve the persistence mode from config then env, defaulting to memory."""
    raw = ""
    if config:
        raw = str(config.get("persistence", "")).strip().lower()
    if raw not in _VALID:
        raw = os.getenv("BASELITH_PITWALL_PERSISTENCE", "").strip().lower()
    return raw if raw in _VALID else "memory"


def build_store(config: dict[str, Any] | None = None) -> PitwallStore:
    """Construct the configured store backend (does no I/O; call ``initialize``)."""
    mode = resolve_persistence(config)
    if mode == "postgres":
        logger.info("pitwall_store_backend", backend="postgres")
        return PostgresPitwallStore()
    logger.info("pitwall_store_backend", backend="memory")
    return InMemoryPitwallStore()


__all__ = ["build_store", "resolve_persistence"]
