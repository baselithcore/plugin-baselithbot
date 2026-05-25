"""Role assignment ops per gruppi.

Compatibility check: un ruolo tenant-scoped non può finire su gruppi
di tenant diversi (cross-tenant). Ruoli globali (``roles.tenant_id IS
NULL``) sempre ammessi su qualsiasi gruppo.
"""

from __future__ import annotations

from typing import Any

from llm_wiki import config
from llm_wiki.db.connection import get_connection
from llm_wiki.db.groups.crud import CrossTenantError, GroupNotFoundError


def get_group_roles(group_id: str) -> list[dict[str, Any]]:
    """Ruoli associati al gruppo (id, slug, name, is_system, tenant_id)."""
    if not config.POSTGRES_ENABLED:
        return []
    from psycopg.rows import dict_row

    with get_connection() as conn:
        try:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT r.id, r.slug, r.name, r.description, r.is_system,
                           r.tenant_id, gr.granted_at, gr.granted_by
                    FROM group_roles gr
                    JOIN roles r ON r.id = gr.role_id
                    WHERE gr.group_id = %s
                    ORDER BY r.is_system DESC, r.slug ASC
                    """,
                    (group_id,),
                )
                rows = cur.fetchall()
        finally:
            conn.rollback()
    return [
        {
            "id": str(r["id"]),
            "slug": r["slug"],
            "name": r["name"],
            "description": r.get("description", ""),
            "is_system": bool(r["is_system"]),
            "tenant_id": str(r["tenant_id"]) if r.get("tenant_id") else None,
            "granted_at": r["granted_at"].isoformat() if r.get("granted_at") else None,
            "granted_by": str(r["granted_by"]) if r.get("granted_by") else None,
        }
        for r in rows
    ]


def assign_role(
    group_id: str,
    role_id: str,
    *,
    granted_by: str | None = None,
) -> bool:
    """Associa ruolo al gruppo. Idempotent.

    Valida che il ruolo, se tenant-scoped, appartenga allo stesso
    tenant del gruppo. Ruoli globali (``tenant_id IS NULL``) sempre
    ammessi.
    """
    if not config.POSTGRES_ENABLED:
        return False
    tenant_id = _validate_role_group_compatible(group_id, role_id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO group_roles (group_id, role_id, tenant_id, granted_by)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (group_id, role_id, tenant_id, granted_by),
            )
            inserted = cur.rowcount > 0
        conn.commit()
    return inserted


def revoke_role(group_id: str, role_id: str) -> bool:
    if not config.POSTGRES_ENABLED:
        return False
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM group_roles WHERE group_id = %s AND role_id = %s",
                (group_id, role_id),
            )
            removed = cur.rowcount > 0
        conn.commit()
    return removed


def _validate_role_group_compatible(group_id: str, role_id: str) -> str:
    """Verifica compatibilità tenant ruolo↔gruppo.

    - ruolo globale (``roles.tenant_id IS NULL``) → ok per qualsiasi gruppo.
    - ruolo tenant-scoped → deve matchare ``group.tenant_id``.

    Ritorna il ``tenant_id`` del gruppo per la denormalizzazione.
    """
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        (SELECT tenant_id FROM groups WHERE id = %s) AS group_tid,
                        (SELECT tenant_id FROM roles WHERE id = %s)  AS role_tid
                    """,
                    (group_id, role_id),
                )
                row = cur.fetchone()
        finally:
            conn.rollback()
    if not row or row[0] is None:
        raise GroupNotFoundError(f"gruppo {group_id} non trovato")
    group_tid = str(row[0])
    role_tid = row[1]
    if role_tid is not None and str(role_tid) != group_tid:
        raise CrossTenantError(
            f"ruolo {role_id} (tenant {role_tid}) non assegnabile al gruppo "
            f"{group_id} (tenant {group_tid})"
        )
    return group_tid


__all__ = ["get_group_roles", "assign_role", "revoke_role"]
