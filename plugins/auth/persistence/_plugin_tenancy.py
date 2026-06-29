"""Persistence for per-plugin tenancy-mode overrides.

A plugin declares its tenancy model in its manifest (``shared`` | ``personal``);
this layer lets an operator override that at runtime from the admin console. A
present row wins over the manifest; an absent one means *inherit the manifest*.
Reads are tiny (one row per overridden plugin) and the whole set is fetched in a
single query for the resolver's hot path — see :mod:`plugins.auth.tenancy_overrides`.
"""

from __future__ import annotations

from typing import Optional

from psycopg.rows import dict_row

from core.db.connection import get_cursor
from core.observability.logging import get_logger

logger = get_logger(__name__)

#: The only modes a plugin may be scoped by (mirrors core.context constants).
VALID_MODES = ("shared", "personal")


class PluginTenancyOverrideMixin:
    """Read/write per-plugin tenancy-mode overrides."""

    def get_plugin_tenancy_overrides(self) -> dict[str, str]:
        """All overrides as ``{plugin_name: mode}`` (empty when none/DB down)."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT plugin_name, mode FROM auth_plugin_tenancy_override")
            return {r["plugin_name"]: r["mode"] for r in cur.fetchall()}

    def get_plugin_tenancy_override(self, plugin_name: str) -> Optional[str]:
        """A single plugin's override mode, or ``None`` when it inherits."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT mode FROM auth_plugin_tenancy_override WHERE plugin_name = %s",
                (plugin_name,),
            )
            row = cur.fetchone()
        return row["mode"] if row else None

    def set_plugin_tenancy_override(
        self, plugin_name: str, mode: str, updated_by: str
    ) -> None:
        """Upsert a plugin's tenancy override (``mode`` must be in VALID_MODES)."""
        if mode not in VALID_MODES:
            raise ValueError(f"invalid tenancy mode: {mode!r}")
        with get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO auth_plugin_tenancy_override
                    (plugin_name, mode, updated_by, updated_at)
                VALUES (%s, %s, %s, NOW())
                ON CONFLICT (plugin_name) DO UPDATE SET
                    mode = EXCLUDED.mode,
                    updated_by = EXCLUDED.updated_by,
                    updated_at = NOW()
                """,
                (plugin_name, mode, updated_by),
            )

    def delete_plugin_tenancy_override(self, plugin_name: str) -> None:
        """Clear a plugin's override so it reverts to the manifest-declared mode."""
        with get_cursor() as cur:
            cur.execute(
                "DELETE FROM auth_plugin_tenancy_override WHERE plugin_name = %s",
                (plugin_name,),
            )


__all__ = ["PluginTenancyOverrideMixin", "VALID_MODES"]
