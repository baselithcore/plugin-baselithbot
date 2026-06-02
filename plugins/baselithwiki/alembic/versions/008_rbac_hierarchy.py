"""RBAC: hierarchy reseed (superuser / admin / moderator / user).

Sostituisce la triade ``admin / editor / viewer`` di
:mod:`alembic.versions.007_rbac` con la gerarchia richiesta:

- ``superuser``  → tutti i permessi, incluso ``rbac.assign.admin`` e
                   ``rbac.assign.superuser`` (escalation impossibile via
                   UI; il primo superuser nasce dal bootstrap admin).
- ``admin``      → gestione wiki + scaffold + nominare moderatori/user.
                   NON può promuovere altri admin né superuser.
- ``moderator``  → cura contenuti (wiki.write, feedback.delete) +
                   nominare user. NON può nominare moderatori o admin.
- ``user``       → end-user: lettura wiki, chat, propria memoria/feedback.

Permessi nuovi
==============

``rbac.assign.<slug>`` — gating granulare sull'endpoint
``POST /api/admin/rbac/users/{id}/roles``. L'actor deve possedere il
permesso corrispondente al ruolo target. Pattern NIST RBAC2 (admin
review): nessuna escalation implicita.

Backfill
========

- Utenti con il vecchio ruolo system ``admin`` → ``superuser``.
- Utenti con il vecchio ``editor``           → ``admin``.
- Utenti con il vecchio ``viewer``           → ``user``.
- Vecchi ruoli system rimossi (CASCADE → role_permissions /
  user_roles ridondanti già rimappati).

La colonna legacy ``users.role`` (CHECK 'admin'/'user') NON viene
toccata per non rompere la coerenza JWT-issuance esistente. RBAC è la
fonte autoritativa; ``users.role`` resta come fallback di display.

Revision ID: 008_rbac_hierarchy
Revises: 007_rbac
Create Date: 2026-05-02
"""

from collections.abc import Sequence
from typing import NamedTuple

import sqlalchemy as sa

from alembic import op

revision: str = "008_rbac_hierarchy"
down_revision: str | None = "007_rbac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Catalogo nuovo (estende 007 con `rbac.assign.*`).
NEW_PERMISSIONS: tuple[tuple[str, str], ...] = (
    ("rbac.assign.superuser", "Promuovere a superuser (bootstrap-only)"),
    ("rbac.assign.admin", "Nominare admin"),
    ("rbac.assign.moderator", "Nominare moderatori"),
    ("rbac.assign.user", "Nominare utenti standard"),
)


class _RoleSeed(NamedTuple):
    slug: str
    name: str
    description: str
    permissions: list[str]


# Permessi base per categoria (riusati nelle definizioni ruolo).
WIKI_READ = ["wiki.read"]
WIKI_WRITE = ["wiki.read", "wiki.write"]
WIKI_FULL = ["wiki.read", "wiki.write", "wiki.delete"]

CHAT = ["chat.use"]
CONV_OWN = ["conversation.read", "conversation.delete"]
MEMORY_OWN = ["memory.read", "memory.write", "memory.delete"]
FEEDBACK_USER = ["feedback.write"]
FEEDBACK_MOD = ["feedback.write", "feedback.read", "feedback.delete"]
INGEST_FULL = ["ingest.run", "ingest.delete"]
ADMIN_USER_MANAGE = ["admin.user.manage"]
ADMIN_TENANT = ["admin.tenant.manage", "admin.scaffold"]
ADMIN_RUNTIME = ["admin.runtime"]
AUDIT = ["admin.audit.read"]


SEED_ROLES: tuple[_RoleSeed, ...] = (
    _RoleSeed(
        slug="superuser",
        name="Superuser",
        description="Accesso completo. Vede e gestisce tutto: utenti, wiki, ruoli, runtime.",
        permissions=[
            *WIKI_FULL,
            *CHAT,
            *INGEST_FULL,
            *CONV_OWN,
            *MEMORY_OWN,
            *FEEDBACK_MOD,
            *ADMIN_USER_MANAGE,
            *ADMIN_TENANT,
            *ADMIN_RUNTIME,
            *AUDIT,
            "rbac.assign.superuser",
            "rbac.assign.admin",
            "rbac.assign.moderator",
            "rbac.assign.user",
        ],
    ),
    _RoleSeed(
        slug="admin",
        name="Amministratore",
        description=(
            "Gestione di una o più wiki. Può scaffoldare pack, "
            "ingestare documenti, nominare moderatori e utenti."
        ),
        permissions=[
            *WIKI_FULL,
            *CHAT,
            *INGEST_FULL,
            *CONV_OWN,
            *MEMORY_OWN,
            *FEEDBACK_MOD,
            *ADMIN_USER_MANAGE,
            *ADMIN_TENANT,
            *AUDIT,
            "rbac.assign.moderator",
            "rbac.assign.user",
        ],
    ),
    _RoleSeed(
        slug="moderator",
        name="Moderatore",
        description=(
            "Cura contenuti wiki, modera feedback. Può nominare utenti ma non altri moderatori."
        ),
        permissions=[
            *WIKI_WRITE,
            *CHAT,
            *CONV_OWN,
            *MEMORY_OWN,
            *FEEDBACK_MOD,
            "rbac.assign.user",
        ],
    ),
    _RoleSeed(
        slug="user",
        name="Utente",
        description="End-user: lettura wiki, chat, gestione propria memoria/feedback.",
        permissions=[
            *WIKI_READ,
            *CHAT,
            *CONV_OWN,
            *MEMORY_OWN,
            *FEEDBACK_USER,
        ],
    ),
)


# Slug dei ruoli system pre-008 da rimappare poi rimuovere.
LEGACY_ROLE_REMAP: tuple[tuple[str, str], ...] = (
    ("admin", "superuser"),
    ("editor", "admin"),
    ("viewer", "user"),
)


def upgrade() -> None:
    bind = op.get_bind()

    # 1. Inserisci nuovi permessi (catalogo 007 + nuovi).
    perm_stmt = sa.text(
        "INSERT INTO permissions (slug, description) VALUES (:slug, :description) "
        "ON CONFLICT (slug) DO UPDATE SET description = EXCLUDED.description"
    )
    for slug, desc in NEW_PERMISSIONS:
        bind.execute(perm_stmt, {"slug": slug, "description": desc})

    # 2. Rinomina i ruoli legacy in slug temporanei (`<slug>__legacy_008`)
    #    così possiamo creare i nuovi senza collisione su UNIQUE
    #    (tenant_id NULLS NOT DISTINCT, slug). Lo facciamo SOLO sui ruoli
    #    system globali — i custom per-tenant restano intatti.
    bind.execute(
        sa.text(
            """
            UPDATE roles
            SET slug = slug || '__legacy_008'
            WHERE is_system = TRUE
              AND tenant_id IS NULL
              AND slug IN ('admin', 'editor', 'viewer')
            """
        )
    )

    # 3. Crea i nuovi ruoli con permessi pieni.
    role_upsert = sa.text(
        """
        INSERT INTO roles (slug, name, description, is_system, tenant_id)
        VALUES (:slug, :name, :description, TRUE, NULL)
        ON CONFLICT (tenant_id, slug) DO UPDATE
            SET name = EXCLUDED.name,
                description = EXCLUDED.description,
                is_system = TRUE
        """
    )
    role_perm_reset = sa.text(
        "DELETE FROM role_permissions "
        "WHERE role_id = (SELECT id FROM roles WHERE slug = :slug AND tenant_id IS NULL)"
    )
    role_perm_insert = sa.text(
        """
        INSERT INTO role_permissions (role_id, permission_slug)
        SELECT id, :perm FROM roles WHERE slug = :slug AND tenant_id IS NULL
        ON CONFLICT DO NOTHING
        """
    )
    for role_def in SEED_ROLES:
        bind.execute(
            role_upsert,
            {
                "slug": role_def.slug,
                "name": role_def.name,
                "description": role_def.description,
            },
        )
        bind.execute(role_perm_reset, {"slug": role_def.slug})
        for perm in role_def.permissions:
            bind.execute(role_perm_insert, {"perm": perm, "slug": role_def.slug})

    # 4. Rimappa user_roles: chiunque avesse il ruolo legacy riceve il
    #    nuovo equivalente. Idempotent — duplicati impediti dalla PK
    #    (user_id, role_id).
    remap_user_roles = sa.text(
        """
        INSERT INTO user_roles (user_id, role_id)
        SELECT ur.user_id, new_r.id
        FROM user_roles ur
        JOIN roles old_r ON old_r.id = ur.role_id
                        AND old_r.is_system = TRUE
                        AND old_r.tenant_id IS NULL
                        AND old_r.slug = :legacy_slug
        JOIN roles new_r ON new_r.is_system = TRUE
                        AND new_r.tenant_id IS NULL
                        AND new_r.slug = :new_slug
        ON CONFLICT DO NOTHING
        """
    )
    for legacy_slug, new_slug in LEGACY_ROLE_REMAP:
        bind.execute(
            remap_user_roles,
            {
                "legacy_slug": f"{legacy_slug}__legacy_008",
                "new_slug": new_slug,
            },
        )

    # 5. Drop dei ruoli legacy. CASCADE rimuove role_permissions e
    #    user_roles vecchi (le assegnazioni nuove sono già state
    #    inserite al punto 4).
    bind.execute(
        sa.text(
            """
            DELETE FROM roles
            WHERE is_system = TRUE
              AND tenant_id IS NULL
              AND slug IN ('admin__legacy_008', 'editor__legacy_008', 'viewer__legacy_008')
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()

    # Reverse: rinomina superuser/admin/moderator/user in slug temporanei
    # poi reinserisci admin/editor/viewer (subset 007). NON ripristina i
    # permessi esatti del 007 — un downgrade completo richiederebbe
    # rieseguire il seed di 007. Best-effort: ricrea con stessi permessi.
    bind.execute(
        sa.text(
            """
            UPDATE roles
            SET slug = slug || '__rollback_008'
            WHERE is_system = TRUE
              AND tenant_id IS NULL
              AND slug IN ('superuser', 'admin', 'moderator', 'user')
            """
        )
    )
    # Rollback minimal: ricrea i 3 vecchi ruoli vuoti — operatore deve
    # rifare alembic upgrade head per ripopolarli da 007.
    for slug, name in (
        ("admin", "Amministratore"),
        ("editor", "Editor"),
        ("viewer", "Lettore"),
    ):
        bind.execute(
            sa.text(
                """
                INSERT INTO roles (slug, name, is_system, tenant_id)
                VALUES (:slug, :name, TRUE, NULL)
                ON CONFLICT (tenant_id, slug) DO NOTHING
                """
            ),
            {"slug": slug, "name": name},
        )
    # Drop i nuovi ruoli (slug rinominato).
    bind.execute(
        sa.text(
            """
            DELETE FROM roles
            WHERE is_system = TRUE
              AND tenant_id IS NULL
              AND slug LIKE '%__rollback_008'
            """
        )
    )
    # Drop nuovi permessi.
    for slug, _ in NEW_PERMISSIONS:
        bind.execute(
            sa.text("DELETE FROM permissions WHERE slug = :slug"),
            {"slug": slug},
        )
