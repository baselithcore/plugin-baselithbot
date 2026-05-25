"""CRUD ruoli + permessi + assegnazioni.

Tabelle: ``roles``, ``permissions``, ``role_permissions``, ``user_roles``,
``user_domain_grants``. Schema in
``alembic/versions/007_rbac.py``.

Pattern allineato a :mod:`llm_wiki.db.users` — psycopg3 + dict_row,
``rollback()`` su read-only per non lasciare transazioni aperte nel
pool.

Tutte le funzioni sono no-op (return [] / 0 / False) se Postgres è
disabilitato — il caller deve già gestire questo invariant a livello
di endpoint.
"""

from __future__ import annotations

from typing import Any

from llm_wiki import config
from llm_wiki.db.connection import get_connection

# --- Lookup ---------------------------------------------------------------


def get_user_permissions(user_id: str, *, domain_slug: str | None = None) -> list[str]:
    """Permessi effettivi di un utente, aggregati da tutti i suoi ruoli.

    Modello per-wiki (008+) + group bundling (015+):

    - **Global perms**: derivano da ``user_roles`` (M:N con ``roles``).
      Valgono trasversalmente. Esempio: un superuser ha tutto ovunque.
    - **Group perms** (015+): derivano dai ruoli associati ai gruppi
      di cui l'utente è membro (``group_members`` → ``group_roles``
      → ``role_permissions``). Bundle-utenti AWS IAM-style — UNION-ati
      con i ruoli diretti, sempre attivi (indipendenti dal
      ``domain_slug``).
    - **Domain perms**: derivano da ``user_domain_grants.role_id`` per
      ``domain_slug == :domain_slug``. Promuovono un utente solo dentro
      una specifica wiki (es. moderator solo su ``legal``).

    Quando ``domain_slug`` è ``None`` saltiamo i domain perms (utile
    per UI admin / audit / contesti non scoped). Group e global perms
    restano sempre inclusi.

    Ritorna lista deduplicata + ordinata di slug permesso. Vuota se
    Postgres disabilitato o utente senza ruoli/gruppi/grant.
    """
    if not config.POSTGRES_ENABLED:
        return []
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                if domain_slug:
                    # UNION dei role_id da user_roles globali + grant
                    # del dominio (solo se role_id non NULL — un grant
                    # senza role è "accesso senza override perms") +
                    # ruoli via gruppi (015).
                    cur.execute(
                        """
                        SELECT DISTINCT rp.permission_slug
                        FROM (
                            SELECT role_id FROM user_roles WHERE user_id = %s
                            UNION
                            SELECT gr.role_id FROM group_roles gr
                            JOIN group_members gm ON gm.group_id = gr.group_id
                            WHERE gm.user_id = %s
                            UNION
                            SELECT role_id FROM user_domain_grants
                            WHERE user_id = %s
                              AND domain_slug = %s
                              AND role_id IS NOT NULL
                        ) effective_roles
                        JOIN role_permissions rp ON rp.role_id = effective_roles.role_id
                        """,
                        (user_id, user_id, user_id, domain_slug),
                    )
                else:
                    cur.execute(
                        """
                        SELECT DISTINCT rp.permission_slug
                        FROM (
                            SELECT role_id FROM user_roles WHERE user_id = %s
                            UNION
                            SELECT gr.role_id FROM group_roles gr
                            JOIN group_members gm ON gm.group_id = gr.group_id
                            WHERE gm.user_id = %s
                        ) effective_roles
                        JOIN role_permissions rp ON rp.role_id = effective_roles.role_id
                        """,
                        (user_id, user_id),
                    )
                rows = cur.fetchall()
        finally:
            conn.rollback()
    return sorted({row[0] for row in rows})


def get_user_roles(user_id: str) -> list[dict[str, Any]]:
    """Lista ruoli assegnati all'utente (id, slug, name, is_system)."""
    if not config.POSTGRES_ENABLED:
        return []
    from psycopg.rows import dict_row

    with get_connection() as conn:
        try:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT r.id, r.slug, r.name, r.is_system, r.tenant_id
                    FROM user_roles ur
                    JOIN roles r ON r.id = ur.role_id
                    WHERE ur.user_id = %s
                    ORDER BY r.is_system DESC, r.slug ASC
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


def get_user_domain_grants(user_id: str) -> list[str]:
    """Lista domain_slug accessibili all'utente (gateway multi-wiki).

    Vuota = nessun grant esplicito → l'engine single-tenant accetta
    qualsiasi APP_DOMAIN per back-compat. Quando popolata, il middleware
    valida che il dominio del processo sia incluso.

    Per ottenere anche il ``role_id`` / ``role_slug`` per ogni grant
    (utile a UI admin), usare :func:`get_user_domain_grants_detailed`.
    """
    if not config.POSTGRES_ENABLED:
        return []
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT domain_slug FROM user_domain_grants WHERE user_id = %s "
                    "ORDER BY domain_slug ASC",
                    (user_id,),
                )
                rows = cur.fetchall()
        finally:
            conn.rollback()
    return [row[0] for row in rows]


def get_user_domain_grants_detailed(user_id: str) -> list[dict[str, Any]]:
    """Lista grants con role_id + role_slug. Usato dall'API admin per
    mostrare il ruolo per-dominio nella UI ruoli.

    Ogni elemento: ``{"domain_slug": str, "role_id": str|None, "role_slug": str|None}``.
    """
    if not config.POSTGRES_ENABLED:
        return []
    from psycopg.rows import dict_row

    with get_connection() as conn:
        try:
            with conn.cursor(row_factory=dict_row) as cur:
                cur.execute(
                    """
                    SELECT udg.domain_slug,
                           udg.role_id,
                           r.slug AS role_slug
                    FROM user_domain_grants udg
                    LEFT JOIN roles r ON r.id = udg.role_id
                    WHERE udg.user_id = %s
                    ORDER BY udg.domain_slug ASC
                    """,
                    (user_id,),
                )
                rows = cur.fetchall()
        finally:
            conn.rollback()
    return [
        {
            "domain_slug": r["domain_slug"],
            "role_id": str(r["role_id"]) if r.get("role_id") else None,
            "role_slug": r.get("role_slug"),
        }
        for r in rows
    ]


def list_roles(tenant_id: str | None = None) -> list[dict[str, Any]]:
    """Ruoli globali (tenant_id=NULL) + opzionalmente quelli del tenant."""
    if not config.POSTGRES_ENABLED:
        return []
    from psycopg.rows import dict_row

    with get_connection() as conn:
        try:
            with conn.cursor(row_factory=dict_row) as cur:
                if tenant_id:
                    cur.execute(
                        """
                        SELECT id, slug, name, description, is_system, tenant_id
                        FROM roles
                        WHERE tenant_id IS NULL OR tenant_id = %s
                        ORDER BY is_system DESC, slug ASC
                        """,
                        (tenant_id,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, slug, name, description, is_system, tenant_id
                        FROM roles
                        WHERE tenant_id IS NULL
                        ORDER BY is_system DESC, slug ASC
                        """
                    )
                rows = cur.fetchall()
        finally:
            conn.rollback()
    return [
        {
            "id": str(r["id"]),
            "slug": r["slug"],
            "name": r["name"],
            "description": r["description"],
            "is_system": bool(r["is_system"]),
            "tenant_id": str(r["tenant_id"]) if r.get("tenant_id") else None,
        }
        for r in rows
    ]


def get_role_permissions(role_id: str) -> list[str]:
    if not config.POSTGRES_ENABLED:
        return []
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT permission_slug FROM role_permissions "
                    "WHERE role_id = %s ORDER BY permission_slug ASC",
                    (role_id,),
                )
                rows = cur.fetchall()
        finally:
            conn.rollback()
    return [row[0] for row in rows]


# --- Mutations ------------------------------------------------------------


def set_role_permissions(role_id: str, permissions: list[str]) -> dict[str, list[str]]:
    """Sostituisce atomicamente i permessi del ruolo.

    DELETE + INSERT in singola transazione. Idempotente sul set finale.
    Ritorna ``{"added": [...], "removed": [...]}`` per audit.
    Caller deve già aver validato che ogni slug esista in ``ALL_PERMISSIONS``
    e applicato eventuali invariant (es. superuser non può perdere perm).
    """
    if not config.POSTGRES_ENABLED:
        return {"added": [], "removed": []}
    target = sorted(set(permissions))
    current = set(get_role_permissions(role_id))
    added = sorted(set(target) - current)
    removed = sorted(current - set(target))
    if not added and not removed:
        return {"added": [], "removed": []}
    with get_connection() as conn:
        with conn.cursor() as cur:
            if removed:
                cur.execute(
                    "DELETE FROM role_permissions WHERE role_id = %s AND permission_slug = ANY(%s)",
                    (role_id, removed),
                )
            if added:
                cur.executemany(
                    "INSERT INTO role_permissions (role_id, permission_slug) "
                    "VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    [(role_id, slug) for slug in added],
                )
        conn.commit()
    return {"added": added, "removed": removed}


def assign_role_to_user(user_id: str, role_id: str, granted_by: str | None = None) -> bool:
    """Idempotent. Ritorna True se l'inserimento è avvenuto."""
    if not config.POSTGRES_ENABLED:
        return False
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_roles (user_id, role_id, granted_by)
                VALUES (%s, %s, %s)
                ON CONFLICT DO NOTHING
                """,
                (user_id, role_id, granted_by),
            )
            inserted = cur.rowcount > 0
        conn.commit()
    return inserted


class LastSuperuserError(Exception):
    """Sollevato quando una revoca lascerebbe il sistema senza superuser."""


def is_last_active_superuser(user_id: str) -> bool:
    """True se l'utente è l'unico superuser ATTIVO del sistema.

    Usato dai guard di delete/deactivate utente: rimuovere o
    disattivare l'ultimo superuser bloccherebbe l'accesso amministrativo
    al sistema. Check non-atomico (no FOR UPDATE): chi chiama deve
    accettare una piccola finestra race in cui due delete simultanei
    di superuser distinti possono entrambi vedersi "non ultimi" — ok
    per operazioni admin a bassa frequenza.

    Per la revoca di ruolo c'è la variante atomica in
    :func:`revoke_role_from_user` con ``FOR UPDATE``.
    """
    if not config.POSTGRES_ENABLED:
        return False
    with get_connection() as conn:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT EXISTS (
                        SELECT 1 FROM user_roles ur
                        JOIN roles r ON r.id = ur.role_id
                        JOIN users u ON u.id = ur.user_id
                        WHERE r.slug = 'superuser'
                          AND r.is_system = TRUE
                          AND u.id = %s
                          AND u.is_active = TRUE
                    ) AS is_super,
                    (
                        SELECT COUNT(*) FROM user_roles ur
                        JOIN roles r ON r.id = ur.role_id
                        JOIN users u ON u.id = ur.user_id
                        WHERE r.slug = 'superuser'
                          AND r.is_system = TRUE
                          AND u.is_active = TRUE
                          AND u.id <> %s
                    ) AS others
                    """,
                    (user_id, user_id),
                )
                row = cur.fetchone()
        finally:
            conn.rollback()
    if not row:
        return False
    return bool(row[0]) and int(row[1]) == 0


def revoke_role_from_user(
    user_id: str,
    role_id: str,
    *,
    protect_last_superuser: bool = True,
) -> bool:
    """Revoca un ruolo dall'utente.

    Se ``protect_last_superuser`` (default True) e il ruolo target è il
    system role ``superuser``, la DELETE è atomica e condizionata:
    rifiutata se non esistono ALTRI superuser oltre a ``user_id``. La
    serializzazione è garantita dal lock di riga (``FOR UPDATE``) sulle
    righe ``user_roles`` matching del ruolo, evitando la race
    "due revoche contemporanee passano entrambe il count check".

    Solleva :class:`LastSuperuserError` in caso di rifiuto.
    """
    if not config.POSTGRES_ENABLED:
        return False
    with get_connection() as conn:
        with conn.cursor() as cur:
            if protect_last_superuser:
                # Lock + count atomico: se il ruolo è superuser, blocca
                # la revoca quando ``user_id`` è l'ultimo possessore.
                # FOR UPDATE su user_roles serializza concorrenti su
                # questo ruolo: due revoche simultanee non possono
                # entrambe vedere count=2.
                cur.execute(
                    """
                    SELECT r.slug, r.is_system,
                           (SELECT COUNT(*)
                            FROM user_roles ur2
                            WHERE ur2.role_id = r.id
                              AND ur2.user_id <> %s) AS others
                    FROM roles r
                    WHERE r.id = %s
                    FOR UPDATE OF r
                    """,
                    (user_id, role_id),
                )
                row = cur.fetchone()
                if row and row[0] == "superuser" and row[1] and int(row[2]) == 0:
                    conn.rollback()
                    raise LastSuperuserError("impossibile revocare l'ultimo superuser")
            cur.execute(
                "DELETE FROM user_roles WHERE user_id = %s AND role_id = %s",
                (user_id, role_id),
            )
            removed = cur.rowcount > 0
        conn.commit()
    return removed


def grant_domain_access(
    user_id: str,
    domain_slug: str,
    *,
    role_id: str | None = None,
    granted_by: str | None = None,
) -> bool:
    if not config.POSTGRES_ENABLED:
        return False
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO user_domain_grants (user_id, domain_slug, role_id, granted_by)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (user_id, domain_slug) DO UPDATE
                    SET role_id = EXCLUDED.role_id,
                        granted_by = EXCLUDED.granted_by,
                        granted_at = NOW()
                """,
                (user_id, domain_slug, role_id, granted_by),
            )
            ok = cur.rowcount > 0
        conn.commit()
    return ok


def revoke_domain_access(user_id: str, domain_slug: str) -> bool:
    if not config.POSTGRES_ENABLED:
        return False
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_domain_grants WHERE user_id = %s AND domain_slug = %s",
                (user_id, domain_slug),
            )
            removed = cur.rowcount > 0
        conn.commit()
    return removed


__all__ = [
    "LastSuperuserError",
    "is_last_active_superuser",
    "get_user_permissions",
    "get_user_roles",
    "get_user_domain_grants",
    "get_user_domain_grants_detailed",
    "list_roles",
    "get_role_permissions",
    "set_role_permissions",
    "assign_role_to_user",
    "revoke_role_from_user",
    "grant_domain_access",
    "revoke_domain_access",
]
