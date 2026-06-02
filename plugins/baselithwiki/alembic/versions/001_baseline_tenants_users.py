"""Baseline: extensions, tenants, users (1:1 invariant), helper indexes.

Modello multi-tenancy: 1 user ↔ 1 tenant (workspace privato). Allineato
ad agent-jira/005. Niente fasi intermedie con N utenti per tenant —
qui partiamo già con UNIQUE su users.tenant_id.

Revision ID: 001_baseline_tenants_users
Revises:
Create Date: 2026-05-01
"""

from collections.abc import Sequence

from alembic import op

revision: str = "001_baseline_tenants_users"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Estensioni: pgcrypto per gen_random_uuid(); citext per email
    # case-insensitive UNIQUE (evita duplicati Foo@x.com / foo@x.com).
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.execute("CREATE EXTENSION IF NOT EXISTS citext")

    # Tenants — workspace logico. UNIQUE su slug (URL-safe identifier).
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tenants (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            slug TEXT NOT NULL UNIQUE,
            plan TEXT NOT NULL DEFAULT 'free',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            settings JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_tenants_slug ON tenants (slug)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_tenants_active "
        "ON tenants (is_active) WHERE is_active = TRUE"
    )

    # Users — 1:1 con tenants enforced via UNIQUE + NOT NULL.
    # ON DELETE CASCADE: cancellare tenant cancella user proprietario.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email CITEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL DEFAULT '',
            tenant_id UUID NOT NULL UNIQUE
                REFERENCES tenants(id) ON DELETE CASCADE,
            role TEXT NOT NULL DEFAULT 'user'
                CHECK (role IN ('admin', 'user')),
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_login_at TIMESTAMPTZ
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)")
    # idx_users_tenant: già coperto dall'UNIQUE constraint, ma esplicito
    # per chiarezza nei query plan.
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_tenant ON users (tenant_id)")

    # Trigger updated_at su tenants — pattern standard per audit.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION set_updated_at_timestamp()
        RETURNS TRIGGER AS $$
        BEGIN
            NEW.updated_at = NOW();
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql
        """
    )
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_tenants_updated_at ON tenants;
        CREATE TRIGGER trg_tenants_updated_at
        BEFORE UPDATE ON tenants
        FOR EACH ROW EXECUTE FUNCTION set_updated_at_timestamp()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_tenants_updated_at ON tenants")
    op.execute("DROP FUNCTION IF EXISTS set_updated_at_timestamp()")
    op.execute("DROP INDEX IF EXISTS idx_users_tenant")
    op.execute("DROP INDEX IF EXISTS idx_users_email")
    op.execute("DROP TABLE IF EXISTS users")
    op.execute("DROP INDEX IF EXISTS idx_tenants_active")
    op.execute("DROP INDEX IF EXISTS idx_tenants_slug")
    op.execute("DROP TABLE IF EXISTS tenants")
    # Estensioni lasciate in piedi: potrebbero servire ad altre app.
