"""Add users table for built-in auth.

Revision ID: 003
Revises: 002
Create Date: 2026-04-14
"""

from typing import Sequence, Union

from alembic import op

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            display_name TEXT NOT NULL DEFAULT '',
            tenant_id UUID REFERENCES tenants(id),
            role TEXT NOT NULL DEFAULT 'user',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            last_login_at TIMESTAMPTZ
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_email ON users (email)")
    op.execute("CREATE INDEX IF NOT EXISTS idx_users_tenant ON users (tenant_id)")


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_users_tenant")
    op.execute("DROP INDEX IF EXISTS idx_users_email")
    op.execute("DROP TABLE IF EXISTS users")
