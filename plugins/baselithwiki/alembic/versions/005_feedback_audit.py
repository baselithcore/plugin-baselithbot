"""Feedback per-tenant + audit_events append-only.

Sostituisce il JSONL globale `.feedback.jsonl` (vedi
`llm_wiki/api/routers/feedback.py:32` legacy). Ogni feedback è ora
linkato al `message_id` della tabella `messages` (FK SET NULL: messaggio
cancellato → feedback orfano resta per analytics).

Audit events: append-only, scoped per tenant ma con bypass admin per
viste cross-tenant (compliance / GDPR access).

Revision ID: 005_feedback_audit
Revises: 004_memories_pgvector
Create Date: 2026-05-01
"""

from collections.abc import Sequence

from alembic import op

revision: str = "005_feedback_audit"
down_revision: str | None = "004_memories_pgvector"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS feedback (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            -- SET NULL: cancellare il messaggio non perde la metrica.
            message_id UUID REFERENCES messages(id) ON DELETE SET NULL,
            rating TEXT NOT NULL CHECK (rating IN ('up', 'down')),
            reason TEXT,
            -- Snapshot Q/A al momento del feedback (anti-rewrite history).
            question TEXT,
            answer TEXT,
            sources JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_feedback_tenant_user "
        "ON feedback (tenant_id, user_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_feedback_message "
        "ON feedback (message_id) WHERE message_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_feedback_rating "
        "ON feedback (tenant_id, rating, created_at DESC)"
    )

    # audit_events — append-only. Niente UPDATE/DELETE da app code:
    # eventuale purge GDPR via job admin separato.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_events (
            id BIGSERIAL PRIMARY KEY,
            -- Tenant nullable: alcuni eventi (admin_bootstrap, scaffold)
            -- sono cross-tenant.
            tenant_id UUID REFERENCES tenants(id) ON DELETE SET NULL,
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            -- kind: vocabolario controllato ma esteso a runtime
            -- (es 'auth.login', 'auth.logout', 'auth.refresh.replay',
            --     'admin.bootstrap', 'admin.scaffold', 'memory.delete').
            kind TEXT NOT NULL,
            -- Payload JSONB libero — mai PII non strettamente necessaria.
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            ip_address INET,
            user_agent TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_events_tenant "
        "ON audit_events (tenant_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_audit_events_kind ON audit_events (kind, created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_audit_events_kind")
    op.execute("DROP INDEX IF EXISTS idx_audit_events_tenant")
    op.execute("DROP TABLE IF EXISTS audit_events")
    op.execute("DROP INDEX IF EXISTS idx_feedback_rating")
    op.execute("DROP INDEX IF EXISTS idx_feedback_message")
    op.execute("DROP INDEX IF EXISTS idx_feedback_tenant_user")
    op.execute("DROP TABLE IF EXISTS feedback")
