"""Refresh token persistence (Sprint 11).

Pattern raccomandato OWASP: access token JWT breve (minuti) + refresh token
opaco persistito in DB con rotation e replay detection.

Schema:
- `token_hash`: SHA-256 del refresh token (MAI salvare il valore in chiaro)
- `family_id`: tutti i refresh emessi da un login condividono la family;
  se un refresh già ruotato viene riusato (replay → furto), invalidiamo
  l'intera famiglia
- `replaced_by`: puntatore al token successore (chain di rotation)
- `revoked_at`: soft-delete
- `user_agent`, `ip_address`: forensics

Revision ID: 008
Revises: 007
Create Date: 2026-04-15
"""

from typing import Sequence, Union

from alembic import op

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            token_hash TEXT NOT NULL UNIQUE,
            family_id UUID NOT NULL,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            issued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            expires_at TIMESTAMPTZ NOT NULL,
            revoked_at TIMESTAMPTZ,
            replaced_by UUID REFERENCES refresh_tokens(id) ON DELETE SET NULL,
            user_agent TEXT,
            ip_address INET
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_refresh_user ON refresh_tokens (user_id) "
        "WHERE revoked_at IS NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_refresh_family ON refresh_tokens (family_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_refresh_expires ON refresh_tokens (expires_at) "
        "WHERE revoked_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_refresh_expires")
    op.execute("DROP INDEX IF EXISTS idx_refresh_family")
    op.execute("DROP INDEX IF EXISTS idx_refresh_user")
    op.execute("DROP TABLE IF EXISTS refresh_tokens")
