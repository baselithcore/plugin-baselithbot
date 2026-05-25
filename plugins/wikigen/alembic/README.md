# Alembic migrations

Pattern allineato a `agent-jira`: migrations scritte a mano in SQL via
`op.execute(...)`. Niente autogenerate, niente modelli ORM in
`target_metadata` — sorgente di verità è lo script SQL.

## Comandi

```bash
# Genera nuova revision (numerazione manuale 001/002/.../NNN per leggibilità).
alembic revision -m "descrizione_breve" --rev-id=001_baseline_tenants_users

# Apply / downgrade.
alembic upgrade head
alembic downgrade -1
alembic current
alembic history

# Dry-run: emette SQL senza eseguire.
alembic upgrade head --sql > /tmp/migration.sql
```

## Connessione

Risolta da `llm_wiki/db/url.py:resolve_database_url()` (priorità
`DATABASE_URL` → composizione `POSTGRES_*`). Stesso codice usato dal
pool applicativo. `alembic/env.py` forza il driver `psycopg3`
(`postgresql+psycopg://`).

## Convenzioni

- Tutte le tabelle scoped per tenant hanno `tenant_id UUID NOT NULL`.
- Timestamps `TIMESTAMPTZ NOT NULL DEFAULT NOW()`.
- ID primari `UUID PRIMARY KEY DEFAULT gen_random_uuid()` (estensione
  `pgcrypto`, abilitata nel baseline).
- Vector embeddings in `memories.embedding VECTOR(1024)` via estensione
  `pgvector` (immagine docker `pgvector/pgvector:pg16` la include).
- Row-Level Security attivata in migration dedicata (006). Ruolo
  applicativo non-superuser `app_runtime` fornito da deploy.

## Pianificate (Fase 1)

- `001_baseline_tenants_users.py` — tenants, users, pgcrypto, indici
- `002_refresh_tokens.py` — refresh token table con family rotation
- `003_conversations_messages.py` — chat persistita per-tenant
- `004_memories_pgvector.py` — RAG personale (note + embeddings)
- `005_feedback_audit.py` — feedback per-tenant + audit_events
- `006_row_level_security.py` — policy RLS + ruolo `app_runtime`
