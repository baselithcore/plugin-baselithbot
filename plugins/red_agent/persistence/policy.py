"""Singleton-row store for runtime policy overrides.

Overrides overlay env-driven RedAgentConfig defaults: env values still
win at boot, but operator edits via the UI persist here and are
re-applied to the live config (and on every plugin restart).
"""

from __future__ import annotations

import json
from typing import Any, cast

import psycopg
from psycopg.rows import DictRow

from core.observability.logging import get_logger

from ._conn import open_conn

logger = get_logger(__name__)


class PolicyStore:
    """Singleton-row store for runtime policy overrides."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    @property
    def available(self) -> bool:
        return bool(self.dsn)

    async def _conn(self) -> psycopg.AsyncConnection[DictRow]:
        return await open_conn(self.dsn)

    async def load(self) -> dict[str, Any]:
        if not self.available:
            return {}
        try:
            async with await self._conn() as conn:
                row = await (
                    await conn.execute(
                        "SELECT overrides FROM red_agent_policy WHERE id = 1"
                    )
                ).fetchone()
                if not row:
                    return {}
                payload = row["overrides"]
                if isinstance(payload, str):
                    return cast(dict[str, Any], json.loads(payload))
                return cast(dict[str, Any], payload or {})
        except Exception as e:  # noqa: BLE001
            logger.warning("red_agent.policy.load_failed", extra={"err": str(e)})
            return {}

    async def save(self, overrides: dict[str, Any], actor: str) -> None:
        if not self.available:
            logger.warning("red_agent.policy.save_skipped_no_dsn")
            return
        payload = json.dumps(overrides, default=str)
        async with await self._conn() as conn:
            await conn.execute(
                """
                INSERT INTO red_agent_policy (id, overrides, updated_by, updated_at)
                VALUES (1, %s::jsonb, %s, now())
                ON CONFLICT (id) DO UPDATE
                  SET overrides = EXCLUDED.overrides,
                      updated_by = EXCLUDED.updated_by,
                      updated_at = now()
                """,
                (payload, actor),
            )
            await conn.commit()
