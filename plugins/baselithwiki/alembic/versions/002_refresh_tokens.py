"""Refresh tokens con family rotation + replay detection.

Modello: access JWT HS256 short-TTL + refresh opaque hashed in DB,
TTL 30d. Ogni rotation incatena `replaced_by`. Replay detect = chi
presenta token già rotato → revoca tutta la family (forza re-login
ovunque).

Revision ID: 002_refresh_tokens
Revises: 001_baseline_tenants_users
Create Date: 2026-05-01
"""

from collections.abc import Sequence

from alembic import op

revision: str = "002_refresh_tokens"
down_revision: str | None = "001_baseline_tenants_users"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            -- SHA-256 del token in chiaro. Mai salvato il valore raw.
            token_hash TEXT NOT NULL UNIQUE,
            -- Family per rotation chain: tutti i refresh derivati da
            -- una login condividono questo UUID. Replay → revoca family.
            family_id UUID NOT NULL,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            expires_at TIMESTAMPTZ NOT NULL,
            revoked_at TIMESTAMPTZ,
            -- replaced_by: id del token successore. Insieme a revoked_at
            -- forma la rotation chain ispezionabile per audit.
            replaced_by UUID REFERENCES refresh_tokens(id),
            user_agent TEXT,
            ip_address INET
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user "
        "ON refresh_tokens (user_id) WHERE revoked_at IS NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_refresh_tokens_family ON refresh_tokens (family_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires "
        "ON refresh_tokens (expires_at) WHERE revoked_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_refresh_tokens_expires")
    op.execute("DROP INDEX IF EXISTS idx_refresh_tokens_family")
    op.execute("DROP INDEX IF EXISTS idx_refresh_tokens_user")
    op.execute("DROP TABLE IF EXISTS refresh_tokens")
