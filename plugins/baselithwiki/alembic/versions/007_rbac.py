"""RBAC: roles, permissions, role_permissions, user_roles + seed system roles.

Modello fine-grained per autorizzazioni — sostituisce il check binario
``users.role IN ('admin','user')`` con permessi action.resource composabili.

Strategia rollout
=================

- Tabelle nuove. ``users.role`` resta come fallback per back-compat e
  come "ruolo primario" mostrato nelle UI legacy. Il dato autoritativo
  passa a ``user_roles`` (M:N).
- Seed system roles ``admin`` / ``editor`` / ``viewer`` con catalogo
  permessi cablato qui (single source of truth allineato a
  :mod:`llm_wiki.auth.permissions`).
- Backfill dati: ogni user esistente con ``role='admin'`` riceve
  ``user_roles → admin``; tutti gli altri ricevono ``viewer``. Idempotent.
- Tutte le tabelle RBAC sono **globali** (non tenant-scoped) per
  permettere ruoli condivisi tra tenant. Override per-tenant dei ruoli
  custom è possibile via ``roles.tenant_id NOT NULL``.

Per multi-wiki via gateway (vedi CLAUDE.md): la tabella
``user_domain_grants`` collega user → domain_slug → role_id. Lasciata
qui per future use; l'engine single-tenant ignora il claim ``domains``
se non popolato.

Revision ID: 007_rbac
Revises: 006_row_level_security
Create Date: 2026-05-02
"""

from collections.abc import Sequence
from typing import NamedTuple

import sqlalchemy as sa

from alembic import op

revision: str = "007_rbac"
down_revision: str | None = "006_row_level_security"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Catalogo permessi — DEVE restare in sync con
# ``llm_wiki/auth/permissions.py``. Manteniamo qui le stringhe seed
# perché la migration deve girare anche senza il modulo Python in path.
SEED_PERMISSIONS: tuple[tuple[str, str], ...] = (
    # Wiki content
    ("wiki.read", "Lettura pagine wiki"),
    ("wiki.write", "Modifica pagine wiki"),
    ("wiki.delete", "Eliminazione pagine wiki"),
    # Chat / RAG
    ("chat.use", "Uso interfaccia chat RAG"),
    # Ingest
    ("ingest.run", "Avvio ingestione documenti"),
    ("ingest.delete", "Rimozione raw / wiki sorgenti"),
    # Conversations
    ("conversation.read", "Lettura proprie conversazioni"),
    ("conversation.delete", "Eliminazione proprie conversazioni"),
    # Feedback
    ("feedback.write", "Invio feedback"),
    ("feedback.read", "Lettura feedback aggregati"),
    ("feedback.delete", "Moderazione feedback"),
    # Memories
    ("memory.read", "Lettura proprie memorie"),
    ("memory.write", "Scrittura memorie"),
    ("memory.delete", "Eliminazione memorie"),
    # Admin
    ("admin.scaffold", "Scaffold pack / setup wizard"),
    ("admin.tenant.manage", "Gestione tenants"),
    ("admin.user.manage", "Gestione utenti / ruoli"),
    ("admin.runtime", "Restart worker / runtime ops"),
    ("admin.audit.read", "Lettura audit log"),
)


class _RoleSeed(NamedTuple):
    slug: str
    name: str
    description: str
    permissions: list[str]


SEED_ROLES: tuple[_RoleSeed, ...] = (
    _RoleSeed(
        slug="admin",
        name="Amministratore",
        description="Accesso completo: gestione tenant, utenti, ruoli, scaffold.",
        permissions=[p for p, _ in SEED_PERMISSIONS],
    ),
    _RoleSeed(
        slug="editor",
        name="Editor",
        description="Crea/modifica wiki, avvia ingest, modera feedback.",
        permissions=[
            "wiki.read",
            "wiki.write",
            "chat.use",
            "ingest.run",
            "conversation.read",
            "conversation.delete",
            "feedback.write",
            "feedback.read",
            "memory.read",
            "memory.write",
            "memory.delete",
        ],
    ),
    _RoleSeed(
        slug="viewer",
        name="Lettore",
        description="Lettura wiki, uso chat, gestione propria memoria/feedback.",
        permissions=[
            "wiki.read",
            "chat.use",
            "conversation.read",
            "conversation.delete",
            "feedback.write",
            "memory.read",
            "memory.write",
            "memory.delete",
        ],
    ),
)


def upgrade() -> None:
    # --- Tabelle ----------------------------------------------------------

    # roles: globali (tenant_id NULL) o tenant-scoped per ruoli custom.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS roles (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            slug TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            is_system BOOLEAN NOT NULL DEFAULT FALSE,
            tenant_id UUID NULL REFERENCES tenants(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    # Slug unico per scope: globali condividono lo stesso namespace,
    # ruoli tenant-scoped hanno il proprio. Uniqueness su (tenant_id, slug)
    # con NULLS NOT DISTINCT (PG15+) per trattare NULL come valore.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_roles_scope_slug "
        "ON roles (tenant_id, slug) NULLS NOT DISTINCT"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_roles_system ON roles (is_system)")

    # permissions: catalogo. PK = slug stringa, niente UUID — i permessi
    # sono dati statici di codice, non risorse user-scoped.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS permissions (
            slug TEXT PRIMARY KEY,
            description TEXT NOT NULL DEFAULT ''
        )
        """
    )

    # role_permissions: M:N. ON DELETE CASCADE su entrambe le FK.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS role_permissions (
            role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            permission_slug TEXT NOT NULL REFERENCES permissions(slug) ON DELETE CASCADE,
            PRIMARY KEY (role_id, permission_slug)
        )
        """
    )

    # user_roles: M:N. ON DELETE CASCADE — soft delete utente non in scope qui.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_roles (
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            granted_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
            PRIMARY KEY (user_id, role_id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_roles_user ON user_roles (user_id)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_user_roles_role ON user_roles (role_id)")

    # user_domain_grants: per gateway multi-wiki. domain_slug arbitrario
    # (corrisponde a APP_DOMAIN del processo backend). NULL role_id =
    # sola lettura del dominio (placeholder semantico).
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_domain_grants (
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            domain_slug TEXT NOT NULL,
            role_id UUID NULL REFERENCES roles(id) ON DELETE SET NULL,
            granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            granted_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
            PRIMARY KEY (user_id, domain_slug)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_user_domain_grants_domain "
        "ON user_domain_grants (domain_slug)"
    )

    # Trigger updated_at su roles.
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_roles_updated_at ON roles;
        CREATE TRIGGER trg_roles_updated_at
        BEFORE UPDATE ON roles
        FOR EACH ROW EXECUTE FUNCTION set_updated_at_timestamp()
        """
    )

    # --- Seed permessi ----------------------------------------------------
    bind = op.get_bind()
    perm_stmt = sa.text(
        "INSERT INTO permissions (slug, description) VALUES (:slug, :description) "
        "ON CONFLICT (slug) DO UPDATE SET description = EXCLUDED.description"
    )
    for slug, desc in SEED_PERMISSIONS:
        bind.execute(perm_stmt, {"slug": slug, "description": desc})

    # --- Seed ruoli system + role_permissions -----------------------------
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

    # --- Backfill user_roles da users.role -------------------------------
    # users.role='admin' → role admin. Tutto il resto → role viewer.
    # editor non assegnato automaticamente: promotion manuale via admin UI.
    op.execute(
        """
        INSERT INTO user_roles (user_id, role_id)
        SELECT u.id, r.id
        FROM users u
        JOIN roles r ON r.slug = 'admin' AND r.tenant_id IS NULL
        WHERE u.role = 'admin'
        ON CONFLICT DO NOTHING
        """
    )
    op.execute(
        """
        INSERT INTO user_roles (user_id, role_id)
        SELECT u.id, r.id
        FROM users u
        JOIN roles r ON r.slug = 'viewer' AND r.tenant_id IS NULL
        WHERE u.role = 'user'
        ON CONFLICT DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_roles_updated_at ON roles")
    op.execute("DROP TABLE IF EXISTS user_domain_grants")
    op.execute("DROP TABLE IF EXISTS user_roles")
    op.execute("DROP TABLE IF EXISTS role_permissions")
    op.execute("DROP TABLE IF EXISTS permissions")
    op.execute("DROP INDEX IF EXISTS idx_roles_system")
    op.execute("DROP INDEX IF EXISTS uq_roles_scope_slug")
    op.execute("DROP TABLE IF EXISTS roles")
