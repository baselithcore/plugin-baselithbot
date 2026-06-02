"""Postgres-backed store for scans and findings.

Single source of truth for the immutable scan/finding records. The
graph layer is a downstream projection optimized for traversal queries.

This package is the modular replacement for the prior monolithic
``scans.py``. Public API is preserved — callers continue to
``from plugins.red_agent.persistence.scans import RedAgentPersistence``
and ``from plugins.red_agent.persistence import RedAgentPersistence``.
"""

from __future__ import annotations

from psycopg.rows import DictRow

import psycopg

from core.observability.logging import get_logger

from .._conn import open_conn
from .._finding_lifecycle import FindingLifecycleMixin
from ._audit import AuditQueryMixin
from ._findings_query import FindingsQueryMixin
from ._scan_io import ScanIOMixin

logger = get_logger(__name__)

__all__ = ["RedAgentPersistence"]


class RedAgentPersistence(
    ScanIOMixin,
    AuditQueryMixin,
    FindingsQueryMixin,
    FindingLifecycleMixin,
):
    """Async psycopg wrapper for scan + finding tables.

    Tolerates a missing DSN or DB outage: read paths return empty
    collections, write paths log and no-op. The plugin therefore
    boots in dev environments without Postgres provisioned.
    """

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    async def _conn(self) -> psycopg.AsyncConnection[DictRow]:
        # Retained for sub-classes / external callers that grab a one-shot
        # connection. Internal hot paths now use ``acquire`` against the pool.
        return await open_conn(self.dsn)
