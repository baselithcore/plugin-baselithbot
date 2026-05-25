# Database, Migrazioni, pgvector

Riferimento dello schema Postgres + workflow Alembic + uso pgvector. Per setup → [`getting-started.md`](getting-started.md). Per modello sicurezza/RLS → [`auth-rbac.md`](auth-rbac.md).

## Stack

| Componente | Versione | Ruolo |
|-----------|----------|-------|
| PostgreSQL | 16 (immagine `pgvector/pgvector:pg16`) | RDBMS primario |
| pgvector | ≥ 0.7 | Embedding storage + similarity search |
| pgcrypto | bundled | `gen_random_uuid()` |
| citext | bundled | Email case-insensitive |
| psycopg | 3.1+ | Driver async-friendly + pool |
| Alembic | 1.13+ | Migrazioni versioned |

## Connection management

`llm_wiki/db/connection.py`:

- Pool psycopg (`psycopg_pool.ConnectionPool`), `min=POSTGRES_POOL_MIN`, `max=POSTGRES_POOL_MAX`.
- Health check: `SELECT 1` ogni connessione idle.
- Per-request: middleware setta `SET app.current_user_id = '<uuid>'` per attivare RLS.
- Ruolo applicativo: `app_runtime` (non-superuser). Migrations runnano con superuser.

```python
from llm_wiki.db.connection import get_pool

async with get_pool().connection() as conn:
    async with conn.cursor() as cur:
        await cur.execute("SELECT * FROM conversations WHERE user_id = %s", (uid,))
```

## Schema overview

```text
tenants
   │
   └── users (1:1 via UNIQUE(tenant_id))
         ├── refresh_tokens         (auth)
         ├── conversations
         │     └── messages
         ├── memories               (pgvector)
         ├── user_roles ─→ roles
         ├── user_domain_grants    (multi-wiki, futuro)
         └── audit_events          (anche tenant-level)

setup_invitations  (token_hash → email/role pre-create)

permissions
   ├── role_permissions ─→ roles
   └── (catalog 21 permissions)
```

## Migrazioni Alembic

Path: `alembic/versions/`. Tutte cumulative, no rollback distruttivi (`downgrade` minimale).

| # | File | Effetto |
|---|------|---------|
| 001 | `001_baseline_tenants_users.py` | Estensioni `pgcrypto`, `citext`. Tabelle `tenants` (slug UNIQUE, plan, is_active, settings JSONB) e `users` (email CITEXT UNIQUE, password_hash, tenant_id UNIQUE NOT NULL). Trigger `updated_at`. |
| 002 | `002_refresh_tokens.py` | `refresh_tokens` (token_hash UNIQUE, family_id, expires_at, used_at, revoked_at). Indici per replay detection. |
| 003 | `003_conversations_messages.py` | `conversations(user_id, title, created_at, updated_at)` + `messages(conversation_id, role, content, created_at)`. CASCADE su delete. |
| 004 | `004_memories_pgvector.py` | Estensione `vector`. `memories(user_id, content, embedding VECTOR(1024))`. Indice ivfflat L2. |
| 005 | `005_feedback_audit.py` | `audit_events(event_type, user_id, tenant_id, details JSONB, created_at)` + `feedback(conversation_id, message_id, direction CHAR(1))`. |
| 006 | `006_row_level_security.py` | Crea ruolo `app_runtime`. Abilita RLS + policy su `conversations`, `messages`, `memories`, `refresh_tokens`. Setting `app.current_user_id`. |
| 007 | `007_rbac.py` | `roles`, `permissions`, `role_permissions`, `user_roles`. Seed 21 permessi + ruoli `admin`/`editor`/`viewer`. |
| 008 | `008_rbac_hierarchy.py` | `user_domain_grants` (multi-wiki). Permessi `rbac.assign.*`. Ruoli `superuser`/`moderator`/`user`. |
| 009 | `009_invitations_and_password_change.py` | `setup_invitations(token_hash UNIQUE, email, role_slug, expires_at, used_at, created_by)` + `users.password_must_change BOOL`. |

### Comandi

```bash
# Stato corrente
alembic current

# Applica tutto
alembic upgrade head

# Step-by-step
alembic upgrade +1
alembic downgrade -1

# Storia
alembic history --verbose

# Genera nuova migrazione (autogenerate basato su SQLAlchemy models — non usato qui, scrivere a mano)
alembic revision -m "add new table"
```

### Convenzioni interne

- File numerati `NNN_descrizione.py` con `revision = "NNN_..."`, `down_revision = "..."`.
- DDL in raw SQL via `op.execute(...)` (no SQLAlchemy ORM in questo progetto).
- Tutte le PK sono `UUID DEFAULT gen_random_uuid()`.
- Timestamp `TIMESTAMPTZ DEFAULT NOW()`.
- Trigger `updated_at` standardizzato (vedi 001 per template).

## Tabelle

### `tenants`

```sql
id           UUID PK DEFAULT gen_random_uuid()
name         TEXT NOT NULL
slug         TEXT UNIQUE NOT NULL
plan         TEXT DEFAULT 'free'
is_active    BOOL DEFAULT TRUE
settings     JSONB DEFAULT '{}'::jsonb
created_at   TIMESTAMPTZ DEFAULT NOW()
updated_at   TIMESTAMPTZ DEFAULT NOW()
```

Indici: `idx_tenants_slug`, `idx_tenants_active`.

### `users`

```sql
id                     UUID PK
email                  CITEXT UNIQUE NOT NULL
password_hash          TEXT NOT NULL
display_name           TEXT
tenant_id              UUID UNIQUE NOT NULL REFERENCES tenants(id)
role                   TEXT  -- legacy single-role; ora si usa user_roles
is_active              BOOL DEFAULT TRUE
password_must_change   BOOL DEFAULT FALSE  -- mig 009
created_at, updated_at, last_login_at
```

`UNIQUE(tenant_id)` enforce 1:1.

### `refresh_tokens`

```sql
id           UUID PK
user_id      UUID NOT NULL REFERENCES users ON DELETE CASCADE
token_hash   TEXT UNIQUE NOT NULL  -- SHA256(plain)
family_id    UUID NOT NULL  -- per replay detection
expires_at   TIMESTAMPTZ NOT NULL
created_at   TIMESTAMPTZ DEFAULT NOW()
used_at      TIMESTAMPTZ  -- consumato
revoked_at   TIMESTAMPTZ
```

Replay: ricevi token con `used_at IS NOT NULL` → revoca tutta la `family_id`.

### `conversations` + `messages`

```sql
conversations(id UUID, user_id UUID FK CASCADE, title TEXT, created_at, updated_at)
messages(id UUID, conversation_id UUID FK CASCADE, role TEXT, content TEXT, created_at)
```

`role ∈ {'user','assistant','system'}`. RLS attivo.

### `memories` (pgvector)

```sql
memories(
  id UUID PK,
  user_id UUID FK CASCADE,
  content TEXT NOT NULL,
  embedding VECTOR(1024) NOT NULL,
  created_at, updated_at
)

CREATE INDEX idx_memories_embedding
  ON memories USING ivfflat (embedding vector_l2_ops)
  WITH (lists = 100);
```

Dimensione 1024 = output BGE-M3. Cambio embedder → `ALTER TABLE memories ALTER COLUMN embedding TYPE VECTOR(<new_dim>)` + reindex.

Query similarity:

```sql
SELECT id, content, embedding <-> %s AS distance
FROM memories
WHERE user_id = %s            -- + RLS implicito
ORDER BY embedding <-> %s
LIMIT %s;
```

Operatori utili pgvector:

| Op | Distanza | Note |
|----|----------|------|
| `<->` | L2 (Euclidea) | Default ivfflat. |
| `<=>` | Cosine | Più costoso, più qualità per embedding normalizzati. |
| `<#>` | Inner product (negato) | Solo per embedding normalizzati. |

### `audit_events`

```sql
audit_events(
  id UUID PK,
  event_type TEXT NOT NULL,
  user_id UUID NULL REFERENCES users ON DELETE SET NULL,  -- nullable per GDPR
  tenant_id UUID NULL,
  details JSONB DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ DEFAULT NOW()
)
```

Append-only convenzionale (nessun TRIGGER bloccante; rispettare lato app). Indici: `(created_at DESC)`, `(event_type)`, `(user_id)`.

### RBAC (`roles`, `permissions`, `user_roles`, `role_permissions`)

```sql
roles(
  id UUID PK,
  slug TEXT,
  name TEXT,
  description TEXT,
  is_system BOOL,
  tenant_id UUID NULL,    -- NULL = global, NOT NULL = tenant-scoped custom role
  created_at, updated_at
)
-- UNIQUE su (tenant_id, slug) NULLS NOT DISTINCT

permissions(id UUID PK, slug TEXT UNIQUE, description TEXT, created_at)

role_permissions(role_id, permission_id, PK(role_id, permission_id))

user_roles(user_id, role_id, created_at, PK(user_id, role_id))
```

Calcolo permessi effettivi:

```sql
SELECT DISTINCT p.slug
FROM user_roles ur
JOIN role_permissions rp ON rp.role_id = ur.role_id
JOIN permissions p ON p.id = rp.permission_id
WHERE ur.user_id = %s;
```

### `user_domain_grants` (mig 008, multi-wiki future)

```sql
user_domain_grants(
  user_id UUID FK,
  domain_slug TEXT,
  role_id UUID FK,
  created_at,
  PK(user_id, domain_slug)
)
```

Permette grant ruolo per-`APP_DOMAIN`. Oggi single-tenant per processo → tabella usata solo per pre-grant in deploy multi-domain.

### `setup_invitations` (mig 009)

```sql
setup_invitations(
  id UUID PK,
  token_hash TEXT UNIQUE NOT NULL,
  email CITEXT NOT NULL,
  role_slug TEXT,
  tenant_slug TEXT,
  display_name TEXT,
  note TEXT,
  expires_at TIMESTAMPTZ NOT NULL,
  used_at TIMESTAMPTZ NULL,
  created_by UUID FK,
  created_at TIMESTAMPTZ
)
```

Indice partial: `(expires_at) WHERE used_at IS NULL` per cleanup veloce.

## RLS

Tutte le policy sono `USING (user_id = current_setting('app.current_user_id')::uuid)`.

**Bypass legittimo** (admin):

```python
from llm_wiki.db.connection import with_admin_role

async with with_admin_role() as conn:
    # SET LOCAL ROLE postgres / superuser
    await conn.execute("SELECT * FROM conversations WHERE tenant_id = %s", (t,))
```

Riservato a route protette da `admin.audit.read` + audit log.

## Backup & restore

### Backup logico

```bash
pg_dump -h localhost -p 5433 -U llm_wiki \
  --format=custom --no-owner --no-privileges \
  --file=/backups/llm_wiki_$(date +%F).dump \
  llm_wiki
```

### Restore

```bash
pg_restore -h localhost -p 5433 -U llm_wiki \
  --clean --if-exists --no-owner --no-privileges \
  -d llm_wiki /backups/llm_wiki_2026-05-02.dump
```

⚠️ Estensioni (`vector`, `citext`, `pgcrypto`) devono esistere prima del restore — il volume Docker `pgvector/pgvector:pg16` le ha già.

### Backup fisico (PITR)

WAL archiving + `pg_basebackup` per snapshot consistenti. Vedi `operations.md`.

### pgvector caveat

L'indice `ivfflat` non è incluso completamente in `pg_dump` se i parametri (`lists`) cambiano. Dopo restore, `REINDEX TABLE memories;` se la performance crolla.

## Monitoring DB

Metriche esportate via `/metrics`:

- `pg_pool_connections{state="idle|active|waiting"}`
- `pg_query_duration_seconds{operation}`
- `pg_rls_violations_total` (se policy fallisce → log + counter)

Query lente: log su `LOG_LEVEL_CONSOLE=DEBUG` con threshold 500ms (configurabile in `db/connection.py`).

## Tuning consigliato

| Parametro Postgres | Valore consigliato | Motivo |
|--------------------|-------------------|--------|
| `shared_buffers` | 25% RAM | Cache pagine. |
| `effective_cache_size` | 75% RAM | Pianificatore. |
| `maintenance_work_mem` | 256–512MB | REINDEX + VACUUM. |
| `work_mem` | 16–32MB | Per connection. |
| `max_connections` | ≥ pool max × N processi + 20 | Avoid pool starvation. |
| `wal_compression` | `on` | Backup più piccoli. |

pgvector specific:

```sql
SET ivfflat.probes = 10;  -- più alto = più qualità, più costo. Default 1.
```

Settare in `db/connection.py` a livello session per query memorie.

## Cleanup periodico

Job consigliati (cron / Celery / pg_cron):

```sql
-- Refresh tokens scaduti
DELETE FROM refresh_tokens
 WHERE expires_at < NOW() - INTERVAL '7 days';

-- Inviti scaduti non consumati
DELETE FROM setup_invitations
 WHERE used_at IS NULL AND expires_at < NOW() - INTERVAL '30 days';

-- Audit retention 90gg (override via env)
DELETE FROM audit_events
 WHERE created_at < NOW() - INTERVAL '90 days';

-- VACUUM ANALYZE settimanale
VACUUM (ANALYZE, VERBOSE);
```

## Troubleshooting

| Sintomo | Diagnosi | Azione |
|---------|----------|--------|
| `permission denied for table conversations` | RLS attivo + `app.current_user_id` non settato | Verifica middleware `tenant_context.py` |
| Query memories lentissime | ivfflat index mancante / stale | `REINDEX TABLE memories;` + `ANALYZE memories;` |
| `relation "vector" does not exist` | pgvector non installato | `CREATE EXTENSION vector;` (immagine pgvector lo fa nel `init.d`) |
| Migration stuck | Lock tavolo | `SELECT * FROM pg_locks;` poi `pg_cancel_backend(pid)` |
| `tenant_id` UNIQUE violation | Tentativo creare 2° user nello stesso tenant | Errore atteso: ogni utente ha tenant proprio |
