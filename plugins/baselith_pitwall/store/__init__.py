"""Persistence package for the digital pit wall.

Exposes the :class:`PitwallStore` Protocol and a :func:`build_store` factory that
returns the in-memory default or the opt-in Postgres backend. Callers depend only
on the Protocol, never on a concrete backend.
"""

from __future__ import annotations

from ._factory import build_store, resolve_persistence
from ._memory import InMemoryPitwallStore
from ._postgres import PostgresPitwallStore
from ._protocol import (
    MAX_AUDIT_PER_SESSION,
    MAX_RECS_PER_SESSION,
    MAX_SNAPSHOTS_PER_CAR,
    PitwallStore,
)

__all__ = [
    "PitwallStore",
    "InMemoryPitwallStore",
    "PostgresPitwallStore",
    "build_store",
    "resolve_persistence",
    "MAX_RECS_PER_SESSION",
    "MAX_AUDIT_PER_SESSION",
    "MAX_SNAPSHOTS_PER_CAR",
]
