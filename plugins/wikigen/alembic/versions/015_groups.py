"""Groups: collezioni di utenti a cui assegnare ruoli in bulk.

Modello AWS IAM Groups / Keycloak / Azure AD Groups portato sul layer
RBAC esistente:

- ``groups`` (tenant-scoped, flat — no nesting).
- ``group_members`` M:N user↔group, con denormalizzato ``tenant_id``
  per RLS efficiente (evita JOIN su ``groups`` nella policy).
- ``group_roles`` M:N group↔role; un utente eredita i permessi di
  tutti i ruoli associati ai gruppi a cui appartiene (UNION con i
  ruoli direttamente assegnati via ``user_roles``).

Strategia rollout
=================

- Tabelle nuove, additive: ``get_user_permissions`` aggiunge una UNION
  che ritorna lista vuota se l'utente non ha gruppi → zero regressioni
  per deploy esistenti.
- Nuovo permesso ``admin.group.manage`` seedato a ``superuser`` +
  ``admin``. Tutto il CRUD/management è gated da questo (separato da
  ``admin.user.manage`` per consentire profili admin più stretti in
  futuro, es. "group-admin" senza diritti su utenti/ruoli).
- RLS policies allineate a mig 006: USING + WITH CHECK su match
  ``tenant_id::text = current_setting('app.current_tenant_id', true)``.

Validazioni cross-tenant (group.tenant == user.tenant /
group.tenant == role.tenant OR role globale) sono fatte a livello
applicativo in :mod:`llm_wiki.db.groups` per coerenza con il resto del
codebase RBAC. La RLS già impedisce a un actor di tenant B di leggere/
scrivere gruppi di tenant A.

Revision ID: 015_groups
Revises: 014_ui_view_permissions
Create Date: 2026-05-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "015_groups"
down_revision: str | None = "014_ui_view_permissions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PERMISSION_SLUG = "admin.group.manage"
PERMISSION_DESC = "Gestione gruppi (creazione, membership, assegnazione ruoli)"
GRANT_TO_SLUGS = ("superuser", "admin")


def upgrade() -> None:
    # --- Tabelle ---------------------------------------------------------

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS groups (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            slug TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT NOT NULL DEFAULT '',
            is_system BOOLEAN NOT NULL DEFAULT FALSE,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    # Slug unico per tenant (no NULL — i gruppi sono sempre tenant-scoped).
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_groups_tenant_slug "
        "ON groups (tenant_id, slug)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_groups_tenant ON groups (tenant_id)")

    # group_members: tenant_id denormalizzato così la policy RLS è una
    # singola condizione senza JOIN (stessa logica della tabella
    # ``feedback`` in mig 005).
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS group_members (
            group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            added_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            added_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
            PRIMARY KEY (group_id, user_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_group_members_user ON group_members (user_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_group_members_group ON group_members (group_id)"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS group_roles (
            group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
            role_id UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            granted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            granted_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
            PRIMARY KEY (group_id, role_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_group_roles_group ON group_roles (group_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_group_roles_role ON group_roles (role_id)"
    )

    # Trigger updated_at su groups (riusa ``set_updated_at_timestamp`` di mig 001).
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_groups_updated_at ON groups;
        CREATE TRIGGER trg_groups_updated_at
        BEFORE UPDATE ON groups
        FOR EACH ROW EXECUTE FUNCTION set_updated_at_timestamp()
        """
    )

    # --- Row-Level Security ----------------------------------------------
    # Stesso pattern di mig 006: ENABLE (NOT FORCE) — superuser bypassa,
    # app_runtime applica.

    for table in ("groups", "group_members", "group_roles"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(
            f"""
            CREATE POLICY {table}_tenant_isolation ON {table}
            USING (
                tenant_id::text = current_setting('app.current_tenant_id', true)
            )
            WITH CHECK (
                tenant_id::text = current_setting('app.current_tenant_id', true)
            )
            """
        )

    # --- Seed permesso ---------------------------------------------------
    bind = op.get_bind()
    bind.execute(
        sa.text(
            "INSERT INTO permissions (slug, description) VALUES (:slug, :desc) "
            "ON CONFLICT (slug) DO UPDATE SET description = EXCLUDED.description"
        ),
        {"slug": PERMISSION_SLUG, "desc": PERMISSION_DESC},
    )
    grant_stmt = sa.text(
        """
        INSERT INTO role_permissions (role_id, permission_slug)
        SELECT id, :perm FROM roles
        WHERE slug = :slug AND tenant_id IS NULL AND is_system = TRUE
        ON CONFLICT DO NOTHING
        """
    )
    for role_slug in GRANT_TO_SLUGS:
        bind.execute(grant_stmt, {"perm": PERMISSION_SLUG, "slug": role_slug})


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text("DELETE FROM role_permissions WHERE permission_slug = :slug"),
        {"slug": PERMISSION_SLUG},
    )
    bind.execute(
        sa.text("DELETE FROM permissions WHERE slug = :slug"),
        {"slug": PERMISSION_SLUG},
    )
    for table in ("group_roles", "group_members", "groups"):
        op.execute(f"DROP POLICY IF EXISTS {table}_tenant_isolation ON {table}")
        op.execute(f"ALTER TABLE {table} DISABLE ROW LEVEL SECURITY")
    op.execute("DROP TRIGGER IF EXISTS trg_groups_updated_at ON groups")
    op.execute("DROP TABLE IF EXISTS group_roles")
    op.execute("DROP TABLE IF EXISTS group_members")
    op.execute("DROP INDEX IF EXISTS uq_groups_tenant_slug")
    op.execute("DROP TABLE IF EXISTS groups")
