"""Backend selection for the BOP :class:`ProcessStore`.

The in-memory backend is the zero-config default (and what the tests rely on).
Durable Postgres persistence is strictly opt-in — selected via plugin config
(``persistence: postgres``) or the ``BASELITH_BOP_PERSISTENCE`` env var — so
enabling it is a deliberate deployment choice that never changes default or test
behaviour.
"""

from __future__ import annotations

import os
from typing import Any

from core.observability.logging import get_logger

from ._memory import InMemoryProcessStore
from ._postgres import PostgresProcessStore
from ._protocol import ProcessStore

logger = get_logger(__name__)

_VALID = ("memory", "postgres")


def resolve_persistence(config: dict[str, Any] | None = None) -> str:
    """Resolve the persistence mode from config then env, defaulting to memory."""
    raw = ""
    if config:
        raw = str(config.get("persistence", "")).strip().lower()
    if raw not in _VALID:
        raw = os.getenv("BASELITH_BOP_PERSISTENCE", "").strip().lower()
    return raw if raw in _VALID else "memory"


def build_store(config: dict[str, Any] | None = None) -> ProcessStore:
    """Construct the configured store backend (does no I/O; call ``initialize``)."""
    mode = resolve_persistence(config)
    if mode == "postgres":
        logger.info("bop_store_backend", backend="postgres")
        return PostgresProcessStore()
    logger.info("bop_store_backend", backend="memory")
    return InMemoryProcessStore()


__all__ = ["build_store", "resolve_persistence"]
