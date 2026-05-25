"""Conversations + messages persistite per-tenant.

Sostituisce il `localStorage:llm-wiki:conversations` del frontend.
Source of truth = backend, cache locale browser è solo ottimizzazione.

`sources` JSONB contiene gli hit RAG citati dal turno assistant
(serializzazione di `RAGAgent.AnswerResult.sources`).

Revision ID: 003_conversations_messages
Revises: 002_refresh_tokens
Create Date: 2026-05-01
"""

from collections.abc import Sequence

from alembic import op

revision: str = "003_conversations_messages"
down_revision: str | None = "002_refresh_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS conversations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            title TEXT NOT NULL DEFAULT 'Nuova conversazione',
            -- title_locked: utente ha rinominato → non auto-derivare più
            -- dal primo messaggio (semantica conservata da useConversations).
            title_locked BOOLEAN NOT NULL DEFAULT FALSE,
            pinned BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_conversations_tenant_user "
        "ON conversations (tenant_id, user_id, updated_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_conversations_pinned "
        "ON conversations (tenant_id, user_id, pinned) WHERE pinned = TRUE"
    )

    # Trigger updated_at — riusa funzione creata in 001.
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_conversations_updated_at ON conversations;
        CREATE TRIGGER trg_conversations_updated_at
        BEFORE UPDATE ON conversations
        FOR EACH ROW EXECUTE FUNCTION set_updated_at_timestamp()
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            conversation_id UUID NOT NULL
                REFERENCES conversations(id) ON DELETE CASCADE,
            -- Tenant denormalizzato per RLS senza JOIN (policy può
            -- filtrare direttamente messages.tenant_id).
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            role TEXT NOT NULL CHECK (role IN ('user', 'assistant', 'system')),
            content TEXT NOT NULL,
            -- Hit RAG citati (assistant turn). Null per user/system.
            sources JSONB,
            -- Metadata opzionali (latenza, token usage, model).
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_conversation "
        "ON messages (conversation_id, created_at)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_tenant ON messages (tenant_id, created_at DESC)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_messages_tenant")
    op.execute("DROP INDEX IF EXISTS idx_messages_conversation")
    op.execute("DROP TABLE IF EXISTS messages")
    op.execute("DROP TRIGGER IF EXISTS trg_conversations_updated_at ON conversations")
    op.execute("DROP INDEX IF EXISTS idx_conversations_pinned")
    op.execute("DROP INDEX IF EXISTS idx_conversations_tenant_user")
    op.execute("DROP TABLE IF EXISTS conversations")
