"""Add tenants table and tenant_id to feedback.

Revision ID: 002
Revises: 001
Create Date: 2026-04-14
"""

from typing import Sequence, Union

from alembic import op

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tabella tenants
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS tenants (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL UNIQUE,
            slug TEXT NOT NULL UNIQUE,
            plan TEXT NOT NULL DEFAULT 'free',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            settings JSONB NOT NULL DEFAULT '{}',
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

    # Colonna tenant_id su feedback
    op.execute("ALTER TABLE feedback ADD COLUMN IF NOT EXISTS tenant_id TEXT")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_feedback_tenant_id "
        "ON feedback (tenant_id) WHERE tenant_id IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_feedback_tenant_id")
    op.execute("ALTER TABLE feedback DROP COLUMN IF EXISTS tenant_id")
    op.execute("DROP INDEX IF EXISTS idx_tenants_active")
    op.execute("DROP INDEX IF EXISTS idx_tenants_slug")
    op.execute("DROP TABLE IF EXISTS tenants")
