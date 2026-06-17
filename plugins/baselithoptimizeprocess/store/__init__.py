"""Persistence seam for BOP state.

The domain depends only on the :class:`ProcessStore` Protocol; concrete backends
plug in behind it. :class:`InMemoryProcessStore` is the zero-config default;
:class:`PostgresProcessStore` adds durable, restart-surviving persistence. Use
:func:`build_store` to pick the backend from config/env, then ``await
store.initialize()`` once before use.
"""

from __future__ import annotations

from ._factory import build_store, resolve_persistence
from ._memory import InMemoryProcessStore
from ._postgres import PostgresProcessStore
from ._protocol import (
    MAX_FIRINGS_PER_PROCESS,
    MAX_SAMPLES_PER_SERIES,
    ProcessStore,
)

__all__ = [
    "ProcessStore",
    "InMemoryProcessStore",
    "PostgresProcessStore",
    "build_store",
    "resolve_persistence",
    "MAX_SAMPLES_PER_SERIES",
    "MAX_FIRINGS_PER_PROCESS",
]
