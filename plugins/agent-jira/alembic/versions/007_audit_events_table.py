"""Tabella audit_events per tracciare modifiche sensibili (GDPR Art. 32).

Registra chi ha fatto cosa quando, utile per:
- investigazione breach
- compliance reporting SOC 2 / GDPR
- forensics post-incident

La tabella è append-only: nessun UPDATE, solo INSERT. La retention è
responsabilità operativa (job periodico che archivia/elimina record >N giorni).

Revision ID: 007
Revises: 006
Create Date: 2026-04-15
"""

from typing import Sequence, Union

from alembic import op

revision: str = "007"
down_revision: Union[str, None] = "006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_events (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            action TEXT NOT NULL,
            resource_type TEXT NOT NULL,
            resource_id TEXT,
            metadata JSONB NOT NULL DEFAULT '{}',
            ip_address INET,
            user_agent TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_tenant_time "
        "ON audit_events (tenant_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_user_time "
        "ON audit_events (user_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_action "
        "ON audit_events (action, created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_audit_action")
    op.execute("DROP INDEX IF EXISTS idx_audit_user_time")
    op.execute("DROP INDEX IF EXISTS idx_audit_tenant_time")
    op.execute("DROP TABLE IF EXISTS audit_events")
