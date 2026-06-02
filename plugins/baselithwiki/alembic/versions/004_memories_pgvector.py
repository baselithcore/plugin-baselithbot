"""Memorie utente con embedding pgvector — RAG personale.

Modello: ogni utente ha un proprio knowledge store ("ricorda che X",
preferenze, fatti dichiarati). Retrieval ibrido a runtime:

    wiki_collection (Qdrant, SHARED)  + user_memories (Qdrant, filter
    by tenant_id payload) → merge + rerank → context al LLM.

Perché embedding ANCHE in Postgres oltre che in Qdrant? Difesa in
profondità: Qdrant è source of truth performance-wise, Postgres tiene
la copia consistente con il resto dei dati tenant (transazioni
atomiche, RLS, backup unificato). Re-index Qdrant da Postgres se
collection persa.

Dimensione VECTOR(1024) = output BGE-M3 (default `EMBEDDER_MODEL`).
Override richiede migration nuova.

Revision ID: 004_memories_pgvector
Revises: 003_conversations_messages
Create Date: 2026-05-01
"""

from collections.abc import Sequence

from alembic import op

revision: str = "004_memories_pgvector"
down_revision: str | None = "003_conversations_messages"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # pgvector. L'immagine docker `pgvector/pgvector:pg16` ce l'ha
    # preinstallata; CREATE EXTENSION è no-op se già presente.
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS memories (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            -- kind: tassonomia leggera. 'note' = testo libero,
            -- 'fact' = affermazione dichiarativa, 'preference' = key/value.
            kind TEXT NOT NULL DEFAULT 'note'
                CHECK (kind IN ('note', 'fact', 'preference')),
            -- Per kind=preference: chiave normalizzata (es 'language',
            -- 'tone'). Null per note/fact.
            key TEXT,
            -- Contenuto raw che l'utente ha dichiarato.
            value TEXT NOT NULL,
            -- Embedding BGE-M3 (1024-dim). NULL accettato durante
            -- inserimento, popolato sincrono dal router POST /api/memories.
            embedding VECTOR(1024),
            -- Metadata opzionali (source: 'manual'|'auto-extracted', confidence).
            metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_memories_tenant_user "
        "ON memories (tenant_id, user_id, updated_at DESC)"
    )
    # ANN index per similarity search. HNSW: query veloce, build più
    # lento ma OK su decine di migliaia di memorie/utente. Cosine
    # distance allinea a normalizzazione BGE-M3.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_memories_embedding_hnsw "
        "ON memories USING hnsw (embedding vector_cosine_ops)"
    )
    # UNIQUE su (tenant_id, kind='preference', key) per dedup
    # preferenze (un solo valore per chiave per utente).
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_memories_preference_unique
        ON memories (tenant_id, key)
        WHERE kind = 'preference' AND key IS NOT NULL
        """
    )

    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_memories_updated_at ON memories;
        CREATE TRIGGER trg_memories_updated_at
        BEFORE UPDATE ON memories
        FOR EACH ROW EXECUTE FUNCTION set_updated_at_timestamp()
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_memories_updated_at ON memories")
    op.execute("DROP INDEX IF EXISTS idx_memories_preference_unique")
    op.execute("DROP INDEX IF EXISTS idx_memories_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_memories_tenant_user")
    op.execute("DROP TABLE IF EXISTS memories")
    # vector extension: lasciata, può servire ad altro.
