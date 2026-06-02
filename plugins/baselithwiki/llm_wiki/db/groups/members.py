"""Group membership ops + ``get_user_groups`` per ``/api/auth/me``.

Cross-tenant guard: un utente di tenant B non può finire in un gruppo
di tenant A. Validazione applicativa qui (oltre alla RLS che già nega
la lettura cross-tenant) per dare un errore esplicito invece di
silent-skip.
"""

from __future__ import annotations

from typing import Any

from llm_wiki import config
from llm_wiki.db.connection import get_connection
from llm_wiki.db.groups.crud import CrossTenantError, GroupNotFoundError


def get_group_members(group_id: str) -> list[dict[str, Any]]:
    """Lista utenti del gruppo (id, email, display_name, role, is_active)."""
    if not config.POSTGRES_ENABLED:
        return []
    from psycopg.rows import dict_row

    with get_connection() as conn:
        try:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT u.id, u.email, u.display_name, u.role, u.is_active,
                           gm.added_at, gm.added_by
                    FROM group_members gm
                    JOIN users u ON u.id = gm.user_id
                    WHERE gm.group_id = %s
                    ORDER BY u.email ASC
                    """,
                    (group_id,),
                )
                rows = cur.fetchall()
        finally:
            conn.rollback()
    return [
        {
            "id": str(r["id"]),
            "email": r["email"],
            "display_name": r.get("display_name", ""),
            "role": r["role"],
            "is_active": bool(r["is_active"]),
            "added_at": r["added_at"].isoformat() if r.get("added_at") else None,
            "added_by": str(r["added_by"]) if r.get("added_by") else None,
        }
        for r in rows
    ]


def get_user_groups(user_id: str) -> list[dict[str, Any]]:
    """Gruppi di cui l'utente è membro. Esposto in ``/api/auth/me``."""
    if not config.POSTGRES_ENABLED:
        return []
    from psycopg.rows import dict_row

    with get_connection() as conn:
        try:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT g.id, g.slug, g.name, g.is_system, g.tenant_id
                    FROM group_members gm
                    JOIN groups g ON g.id = gm.group_id
                    WHERE gm.user_id = %s
                    ORDER BY g.is_system DESC, g.slug ASC
                    """,
                    (user_id,),
                )
                rows = cur.fetchall()
        finally:
            conn.rollback()
    return [
        {
            "id": str(r["id"]),
            "slug": r["slug"],
            "name": r["name"],
            "is_system": bool(r["is_system"]),
            "tenant_id": str(r["tenant_id"]) if r.get("tenant_id") else None,
        }
        for r in rows
    ]


def add_member(
    group_id: str,
    user_id: str,
    *,
    added_by: str | None = None,
) -> bool:
    """Aggiunge utente al gruppo. Idempotent: True solo se inserito.

    Valida che ``user.tenant_id == group.tenant_id`` — solleva
    :class:`CrossTenantError` altrimenti. Coerente col modello 1:1
    user↔tenant: un gruppo non può mescolare tenant.
    """
    if not config.POSTGRES_ENABLED:
        return False
    tenant_id = _validate_user_group_same_tenant(group_id, user_id)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO group_members (group_id, user_id, tenant_id, added_by)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (group_id, user_id, tenant_id, added_by),
            )
            inserted = cur.rowcount > 0
        conn.commit()
    return inserted


def add_members_bulk(
    group_id: str,
    user_ids: list[str],
    *,
    added_by: str | None = None,
) -> dict[str, list[str]]:
    """Bulk add con dedup. Ritorna ``{"added": [...], "skipped": [...]}``.

    ``skipped`` include sia duplicati (già membri) sia fallimenti
    cross-tenant. L'errore non aborta il batch: tutti gli id sbagliati
    finiscono in ``skipped`` in una sola passata.
    """
    if not config.POSTGRES_ENABLED:
        return {"added": [], "skipped": []}
    added: list[str] = []
    skipped: list[str] = []
    for uid in dict.fromkeys(user_ids):  # dedup preservando ordine
        try:
            if add_member(group_id, uid, added_by=added_by):
                added.append(uid)
            else:
                skipped.append(uid)
        except CrossTenantError:
            skipped.append(uid)
    return {"added": added, "skipped": skipped}


def remove_member(group_id: str, user_id: str) -> bool:
    if not config.POSTGRES_ENABLED:
        return False
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM group_members WHERE group_id = %s AND user_id = %s",
                (group_id, user_id),
            )
            removed = cur.rowcount > 0
        conn.commit()
    return removed


def _validate_user_group_same_tenant(group_id: str, user_id: str) -> str:
    """Verifica ``user.tenant_id == group.tenant_id``.

    Ritorna il ``tenant_id`` da denormalizzare nella riga
    ``group_members``. Solleva :class:`GroupNotFoundError` se il gruppo
    non esiste, :class:`CrossTenantError` su mismatch.
    """
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        (SELECT tenant_id FROM groups WHERE id = %s) AS group_tid,
                        (SELECT tenant_id FROM users WHERE id = %s)  AS user_tid
                    """,
                    (group_id, user_id),
                )
                row = cur.fetchone()
        finally:
            conn.rollback()
    if not row or row[0] is None:
        raise GroupNotFoundError(f"gruppo {group_id} non trovato")
    if row[1] is None:
        raise CrossTenantError(f"utente {user_id} non trovato o senza tenant")
    if str(row[0]) != str(row[1]):
        raise CrossTenantError(
            f"utente {user_id} (tenant {row[1]}) non appartiene al tenant "
            f"del gruppo {group_id} ({row[0]})"
        )
    return str(row[0])


__all__ = [
    "get_group_members",
    "get_user_groups",
    "add_member",
    "add_members_bulk",
    "remove_member",
]
