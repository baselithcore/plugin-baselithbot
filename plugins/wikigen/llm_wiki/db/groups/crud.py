"""Groups CRUD + format helpers + shared exceptions."""

from __future__ import annotations

from typing import Any

from llm_wiki import config
from llm_wiki.db.connection import get_connection


class CrossTenantError(Exception):
    """Raised when a membership/role assignment crosses tenant boundaries."""


class GroupNotFoundError(Exception):
    """Raised when a group lookup by id misses."""


class SystemGroupProtected(Exception):
    """Raised when caller tries to delete a system group."""


def list_groups(tenant_id: str) -> list[dict[str, Any]]:
    """Tutti i gruppi del tenant + counts member/role."""
    if not config.POSTGRES_ENABLED:
        return []
    from psycopg.rows import dict_row

    with get_connection() as conn:
        try:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT g.id, g.slug, g.name, g.description, g.is_system,
                           g.tenant_id, g.created_at, g.updated_at,
                           (SELECT COUNT(*) FROM group_members gm
                              WHERE gm.group_id = g.id) AS member_count,
                           (SELECT COUNT(*) FROM group_roles gr
                              WHERE gr.group_id = g.id) AS role_count
                    FROM groups g
                    WHERE g.tenant_id = %s
                    ORDER BY g.is_system DESC, g.slug ASC
                    """,
                    (tenant_id,),
                )
                rows = cur.fetchall()
        finally:
            conn.rollback()
    return [format_group(row) for row in rows]


def get_group_by_id(group_id: str) -> dict[str, Any] | None:
    if not config.POSTGRES_ENABLED:
        return None
    from psycopg.rows import dict_row

    with get_connection() as conn:
        try:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT g.id, g.slug, g.name, g.description, g.is_system,
                           g.tenant_id, g.created_at, g.updated_at,
                           (SELECT COUNT(*) FROM group_members gm
                              WHERE gm.group_id = g.id) AS member_count,
                           (SELECT COUNT(*) FROM group_roles gr
                              WHERE gr.group_id = g.id) AS role_count
                    FROM groups g
                    WHERE g.id = %s
                    """,
                    (group_id,),
                )
                row = cur.fetchone()
        finally:
            conn.rollback()
    return format_group(row) if row else None


def create_group(
    *,
    tenant_id: str,
    slug: str,
    name: str,
    description: str = "",
    is_system: bool = False,
) -> dict[str, Any]:
    """Crea gruppo. Slug unico per tenant (UNIQUE INDEX in mig 015)."""
    if not config.POSTGRES_ENABLED:
        raise RuntimeError("Postgres disabilitato.")
    from psycopg.rows import dict_row

    with get_connection() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                INSERT INTO groups (slug, name, description, is_system, tenant_id)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id, slug, name, description, is_system, tenant_id,
                          created_at, updated_at
                """,
                (slug.strip(), name.strip(), description.strip(), is_system, tenant_id),
            )
            row = cur.fetchone()
        conn.commit()
    if not row:
        raise RuntimeError("INSERT groups non ha restituito righe")
    row["member_count"] = 0
    row["role_count"] = 0
    return format_group(row)


def update_group(
    group_id: str,
    *,
    name: str | None = None,
    description: str | None = None,
) -> dict[str, Any] | None:
    """Rinomina / aggiorna descrizione. Slug e is_system non mutabili."""
    if not config.POSTGRES_ENABLED:
        return None
    updates: list[str] = []
    params: list[Any] = []
    if name is not None:
        updates.append("name = %s")
        params.append(name.strip())
    if description is not None:
        updates.append("description = %s")
        params.append(description.strip())
    if not updates:
        return get_group_by_id(group_id)
    params.append(group_id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"UPDATE groups SET {', '.join(updates)} WHERE id = %s",  # nosec B608
                params,
            )
        conn.commit()
    return get_group_by_id(group_id)


def delete_group(group_id: str) -> bool:
    """Hard delete. CASCADE su ``group_members`` / ``group_roles``.

    Rifiuta gruppi ``is_system=True`` con :class:`SystemGroupProtected`.
    """
    if not config.POSTGRES_ENABLED:
        return False
    group = get_group_by_id(group_id)
    if not group:
        return False
    if group.get("is_system"):
        raise SystemGroupProtected(f"gruppo system '{group['slug']}' non eliminabile")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM groups WHERE id = %s", (group_id,))
            removed = cur.rowcount > 0
        conn.commit()
    return removed


def format_group(row: dict[str, Any]) -> dict[str, Any]:
    """Mapper riga DB → dict serializzabile JSON.

    Esposto perché gli altri sub-moduli del package (members/roles) lo
    riusano per format omogeneo.
    """
    out: dict[str, Any] = {
        "id": str(row["id"]),
        "slug": row["slug"],
        "name": row["name"],
        "description": row.get("description", ""),
        "is_system": bool(row["is_system"]),
        "tenant_id": str(row["tenant_id"]),
        "member_count": int(row.get("member_count") or 0),
        "role_count": int(row.get("role_count") or 0),
    }
    for key in ("created_at", "updated_at"):
        val = row.get(key)
        if val is not None and hasattr(val, "isoformat"):
            out[key] = val.isoformat()
        elif val is not None:
            out[key] = val
    return out


__all__ = [
    "CrossTenantError",
    "GroupNotFoundError",
    "SystemGroupProtected",
    "list_groups",
    "get_group_by_id",
    "create_group",
    "update_group",
    "delete_group",
    "format_group",
]
