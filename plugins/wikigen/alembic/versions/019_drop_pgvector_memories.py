"""Sposta vector storage memorie su Qdrant — drop pgvector da Postgres.

Refactor architetturale: le memorie utente passano a usare il
``VectorStoreService`` di core (Qdrant) per la similarity search; la
tabella ``memories`` in Postgres resta come **source of truth metadata**
(id, tenant, user, kind, key, value, metadata, timestamps) ma perde la
colonna ``embedding`` e gli indici HNSW collegati.

Motivazione:

- Riusa lo stack runtime baselithcore (Qdrant già presente) senza
  pretendere ``pgvector`` sull'immagine Postgres root.
- Architettura coerente con il resto del plugin: documenti wiki erano
  già su Qdrant; ora anche le memorie utente ci passano.
- Cleanup user resta atomico: ``ON DELETE CASCADE`` su Postgres elimina
  i metadati, lo store Qdrant viene pulito via
  ``MemoriesStore.delete()`` / ``cleanup_orphans`` worker.

Down-migration ricrea estensione + colonna + indice come prima della
019 — restore di un dump pre-019 funziona, ma la sincronizzazione con
Qdrant deve essere ricostruita a mano (reindex job).

Revision ID: 019_drop_pgvector_memories
Revises: 018_feedback_triage
Create Date: 2026-05-25
"""

from collections.abc import Sequence

from alembic import op

revision: str = "019_drop_pgvector_memories"
down_revision: str | None = "018_feedback_triage"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Ordine: indici prima della colonna; estensione per ultima così
    # un downgrade parziale può re-crearla senza ambiguità.
    op.execute("DROP INDEX IF EXISTS idx_memories_embedding_hnsw")
    op.execute("DROP INDEX IF EXISTS idx_memories_preference_unique")
    op.execute("ALTER TABLE memories DROP COLUMN IF EXISTS embedding")

    # Ricrea il vincolo "una preferenza per chiave per tenant" senza la
    # dipendenza dall'embedding (era nello stesso indice composito).
    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_memories_preference_unique
        ON memories (tenant_id, key)
        WHERE kind = 'preference' AND key IS NOT NULL
        """
    )

    # Estensione: best-effort drop. Se il role applicativo non è owner
    # dell'estensione (caso comune: installata da superuser baselithcore)
    # il DROP fallisce con InsufficientPrivilege — l'estensione resta
    # innocua nel DB ``llm_wiki``, semplicemente non più usata. Niente
    # impatto operativo.
    op.execute(
        """
        DO $$
        BEGIN
            BEGIN
                DROP EXTENSION IF EXISTS vector;
            EXCEPTION WHEN insufficient_privilege THEN
                RAISE NOTICE 'DROP EXTENSION vector skipped (not owner)';
            END;
        END
        $$
        """
    )


def downgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute("ALTER TABLE memories ADD COLUMN IF NOT EXISTS embedding VECTOR(1024)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_memories_embedding_hnsw "
        "ON memories USING hnsw (embedding vector_cosine_ops)"
    )
    # L'indice unique sulle preferenze era già ricreato da upgrade(),
    # quindi nulla da rifare qui — restano coerenti con la 018.
