"""Persistence layer for the digital twin (in-memory default, Postgres opt-in)."""

from __future__ import annotations

from ._factory import build_store
from ._memory import InMemoryTwinStore
from ._protocol import TwinStore

__all__ = ["TwinStore", "build_store", "InMemoryTwinStore"]
