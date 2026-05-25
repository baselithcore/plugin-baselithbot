# Autenticazione, RBAC, Sicurezza

Modello concettuale e dettagli implementativi del sottosistema multi-tenant + sicurezza. Per setup pratico → [`getting-started.md`](getting-started.md). Per endpoint → [`api-reference.md`](api-reference.md).

## Modello di tenancy

**Single-tenant per processo**: un processo Python serve **un solo Domain Pack** (`APP_DOMAIN`). Verticali separati = processi separati.

**Multi-tenant per utente**: lo stesso processo serve N utenti distinti, ognuno legato a un proprio `tenant` con invariante 1:1 (`users.tenant_id UNIQUE`). La separazione fra utenti è enforced via Row-Level Security a livello Postgres.

```text
┌────────────────────── processo (APP_DOMAIN=legal) ──────────────────────┐
│                                                                          │
│   Domain Pack: domains/legal/  ← contenuto, prompt, schema, UI labels    │
│   Wiki vault:  vaults/legal/   ← contenuto condiviso (lettura tutti)     │
│                                                                          │
│   ┌─ user A (tenant a) ─┐  ┌─ user B (tenant b) ─┐                       │
│   │ conversations       │  │ conversations       │   ← isolate via RLS   │
│   │ memories            │  │ memories            │                       │
│   │ refresh_tokens      │  │ refresh_tokens      │                       │
│   │ roles assegnati     │  │ roles assegnati     │                       │
│   └─────────────────────┘  └─────────────────────┘                       │
└──────────────────────────────────────────────────────────────────────────┘
```

## 1. Autenticazione

### 1.1 Token

| Tipo | Formato | Lifetime | Storage client | Ruolo |
|------|---------|----------|----------------|-------|
| **Access** | JWT HS256 | `ACCESS_TOKEN_TTL_MINUTES` (24h def) | memoria React (mai localStorage) | Trasporta `user_id`, `tenant_id`, `perms[]` su ogni richiesta API. |
| **Refresh** | Opaco (32 byte random) | `REFRESH_TOKEN_TTL_DAYS` (30 def) | cookie `httpOnly`+`Secure`+`SameSite=Strict` | Solo invio su `/auth/refresh`. Hashato (SHA256) in DB; mai in plaintext. |

**Payload JWT** (`llm_wiki/auth/tokens.py`):

```json
{
  "sub": "<user_id uuid>",
  "tenant_id": "<tenant uuid>",
  "perms": ["wiki.read", "chat.use", "..."],
  "iat": 1700000000,
  "exp": 1700086400
}
```

`perms[]` è la **proiezione**: union di tutte le permission dei ruoli dell'utente, calcolata al login e cachata in JWT. Cambio ruolo → richiede refresh per propagarsi (max 5 min su default access TTL via auto-refresh frontend).

### 1.2 Rotation con replay detection

Ogni refresh genera un nuovo token e marca il precedente come `used_at NOT NULL`. I token sono raggruppati in `family_id`:

- Refresh **legittimo** (token unused): consuma + emette nuovo nella stessa famiglia.
- Refresh **già usato**: indizio di furto → revoca **tutta la famiglia** + log `auth.refresh.replay_detected`.

Implementazione: `tokens.rotate_refresh_token()` in transazione singola.

### 1.3 Password

`llm_wiki/auth/passwords.py`:

- Hash: **PBKDF2-SHA256, 260.000 iterazioni**, salt 16 byte random.
- Formato encoded: `pbkdf2_sha256$260000$<salt_hex>$<hash_hex>`.
- Verifica: comparazione constant-time.
- **Policy**: min 12 char, min 1 cifra + 1 maiuscola (configurabile). Validazione lato API + UI.

Flag `users.password_must_change`:

- `TRUE` su bootstrap (admin auto-generato).
- `TRUE` dopo reset admin.
- Frontend mostra `ForcePasswordChange` modal e blocca tutto finché non cambiata.

### 1.4 Flussi

```text
register / invite                 login                       refresh
   │                                │                            │
   ▼                                ▼                            ▼
[POST /auth/register]         [POST /auth/login]          [POST /auth/refresh]
[POST /auth/invite/accept]    rate-limit IP+email          rate-limit IP
   │                                │                            │
   crea tenant+user                verify password             read cookie
   1:1 atomic                      issue access+refresh        verify hash + family
   issue tokens                    set Set-Cookie              detect replay
   │                                │                            │
   ▼                                ▼                            ▼
{ access_token, user }       { access_token, user }       { access_token }
+ Set-Cookie refresh         + Set-Cookie refresh         + Set-Cookie refresh (rotated)
```

**Logout**:

- `POST /auth/logout` → revoca refresh corrente.
- `POST /auth/logout-all` → revoca tutti i refresh dell'utente (forza re-login su tutti i device).

### 1.5 Inviti (out-of-band)

Per ambienti dove `AUTH_PUBLIC_REGISTRATION=false`. Tabelle `setup_invitations` (mig 009).

Generazione (admin):

```bash
python -m llm_wiki invite --email user@example.com --role editor
# oppure POST /auth/invitations (futuro)
```

- Token = 32 byte random URL-safe.
- DB salva `SHA256(token)` only (single-use, time-bound `INVITATION_TTL_HOURS`).
- Plain token mostrato **una volta** in CLI/API → consegna out-of-band.

Consumo:

- `GET /auth/invite/{token}` → peek (email, expires_at) senza consumare.
- `POST /auth/invite/accept` con `{token, password, display_name}` → crea user+tenant, consuma invito, ritorna access+refresh.
- Reuse → 404.

## 2. RBAC

### 2.1 Ruoli di sistema

Migrazioni 007 + 008 stabiliscono gerarchia:

```text
superuser      ← global (tenant_id NULL); tutti i permessi; può assegnare qualsiasi ruolo
   │
   admin       ← per-tenant; gestione utenti, scaffold, audit; può assegnare moderator + user
   │
   moderator   ← per-tenant; moderazione feedback, supporto; può assegnare user
   │
   user        ← per-tenant; chat, conversazioni, memorie, feedback (write)
```

Ruoli **legacy** ancora seedati per compat: `editor`, `viewer`. In nuovi deploy preferire la gerarchia sopra.

### 2.2 Permessi (catalogo)

| Dominio | Slug | Descrizione |
|---------|------|-------------|
| Wiki | `wiki.read` / `wiki.write` / `wiki.delete` | Lettura/edit/cancellazione pagine. |
| Chat | `chat.use` | Esegue query RAG. |
| Ingest | `ingest.run` / `ingest.delete` | Pipeline PDF + cancellazione job. |
| Conversation | `conversation.read` / `conversation.write` / `conversation.delete` | RLS scope: solo proprie. ``write`` (mig 016) gate POST/PATCH + append messages. |
| Feedback | `feedback.write` / `feedback.read` / `feedback.delete` | Submit, aggregato, moderazione. |
| Memory | `memory.read` / `memory.write` / `memory.delete` | Memorie personali. |
| Admin | `admin.scaffold` / `admin.tenant.manage` / `admin.user.manage` / `admin.group.manage` / `admin.runtime` / `admin.audit.read` | Operazioni amministrative (group mgmt da mig 015). |
| Integrations | `obsidian.open` / `graph.read` | Apertura vault Obsidian + lettura knowledge graph. |
| UI Surface | `view.settings` / `view.help` / `view.command_palette` / `view.sources` / `view.status` / `view.editions` | Gating per-tab/modal su superfici UI senza CRUD naturale. |
| RBAC | `rbac.assign.superuser` / `rbac.assign.admin` / `rbac.assign.moderator` / `rbac.assign.user` | Hierarchy-aware role assignment. |

Lista canonica in `llm_wiki/auth/permissions.ALL_PERMISSIONS`; il test `test_seed_migrations_combined_match_python_catalog` rifiuta drift seed↔Python.

### 2.3 Hierarchy-aware assignment

`POST /api/admin/rbac/users/{id}/roles` rifiuta:

- Auto-promozione (assegnare un ruolo ≥ del proprio).
- Promozione laterale (utente A admin di tenant X non può toccare utente B su tenant Y senza superuser).

Implementazione: `permissions.can_assign(actor_perms, target_role)` in `auth/permissions.py`.

### 2.4 Enforcement nelle route

```python
from llm_wiki.auth.dependencies import require_permission

@router.post("/api/ingest/file")
async def ingest_file(
    file: UploadFile,
    user = Depends(require_permission("ingest.run")),
):
    ...
```

Frontend: componente `<Can permission="...">` nasconde elementi UI se mancante. **Non** sostituisce il check server-side.

### 2.5 Gruppi (mig 015)

Bundle utenti AWS IAM-style: un gruppo collega N utenti a M ruoli. Gli utenti membri ereditano i permessi UNION-ati con quelli assegnati direttamente via `user_roles`. Modello flat (no nesting), tenant-scoped (no cross-tenant membership).

**Tabelle** (`alembic/versions/015_groups.py`):

```text
groups          (id, slug, name, description, is_system, tenant_id, ...)
group_members   (group_id, user_id, tenant_id [denorm], added_at, added_by)
group_roles     (group_id, role_id, tenant_id [denorm], granted_at, granted_by)
```

Slug unico per `(tenant_id, slug)`. `tenant_id` denormalizzato su members/roles per RLS senza JOIN.

**Permission flow effettivo** — `db/roles.py:get_user_permissions` (post-015):

```sql
SELECT DISTINCT rp.permission_slug
FROM (
    SELECT role_id FROM user_roles WHERE user_id = :uid          -- ruoli diretti
    UNION
    SELECT gr.role_id FROM group_roles gr                        -- ruoli via gruppi
    JOIN group_members gm ON gm.group_id = gr.group_id
    WHERE gm.user_id = :uid
    UNION
    SELECT role_id FROM user_domain_grants                       -- override per-dominio
    WHERE user_id = :uid AND domain_slug = :domain
) effective_roles
JOIN role_permissions rp ON rp.role_id = effective_roles.role_id
```

**API** — prefix `/api/admin/rbac/groups`, gated `admin.group.manage`:

- `GET    /` — list (tenant del caller) + counts member/role
- `POST   /` — create `{slug, name, description?}`
- `GET    /{gid}` — detail (members + roles)
- `PATCH  /{gid}` — rename / desc
- `DELETE /{gid}` — rifiuta `is_system` con 409
- `POST   /{gid}/members` — bulk add `{user_ids: [...]}` → `{added, skipped}`
- `DELETE /{gid}/members/{uid}` — remove
- `POST   /{gid}/roles` — assign `{role_id}` (anti-escalation: richiede `rbac.assign.<slug>`)
- `DELETE /{gid}/roles/{rid}` — revoke (stesso guard)

**Validazioni cross-tenant** (`db/groups/`):

- Membership rifiutata se `user.tenant_id != group.tenant_id` → `CrossTenantError` (409).
- Role assign rifiutata se ruolo tenant-scoped non matcha `group.tenant_id`. Ruoli globali (`roles.tenant_id IS NULL`) sempre permessi.
- `add_members_bulk` partiziona output in `added` / `skipped` senza abortire il batch.

**Audit kinds**: `group.created`, `group.updated`, `group.deleted`, `group.member.added`, `group.member.removed`, `group.role.granted`, `group.role.revoked`.

**Permission seed**: `admin.group.manage` granted a `superuser` + `admin` (NON a moderator/user). Separato da `admin.user.manage` per consentire profili admin più stretti in futuro (es. "group-admin" senza diritti su utenti diretti).

**Esposizione FE** — `/api/auth/me.groups: GroupRef[]` (read-only). Il gating UI passa sempre da `permissions` (già aggregati). Admin page `/admin/groups` (`AdminGroupsPage.tsx`) per gestione.

## 3. Row-Level Security (RLS)

Migrazione 006 abilita RLS su `conversations`, `messages`, `memories`, `refresh_tokens` (più `users`, `feedback`, `audit_events`, `tenants` con varianti self/optional). Migrazione 015 estende lo stesso pattern a `groups`, `group_members`, `group_roles`.

Pattern policy:

```sql
ALTER TABLE conversations ENABLE ROW LEVEL SECURITY;

CREATE POLICY conversations_isolation
  ON conversations
  USING (user_id = current_setting('app.current_user_id')::uuid);
```

Il pool psycopg setta `SET app.current_user_id = ...` all'inizio di ogni transazione (middleware). Connessione applicativa usa ruolo `app_runtime` (non-superuser) → RLS sempre attivo.

**Conseguenza importante**: se vuoi query cross-tenant (es. dashboard admin), serve permesso `admin.audit.read` + connessione con role privilegiato. Vedi `db/connection.py:with_admin_role()`.

## 4. Audit trail

Tabella `audit_events` (mig 005). Append-only, immutabile.

| Event type | Trigger |
|-----------|---------|
| `auth.login.success` / `.failed` | `/auth/login` |
| `auth.logout` / `.logout_all` | logout |
| `auth.refresh.success` / `.replay_detected` | `/auth/refresh` |
| `auth.password.change` | `/auth/password` |
| `auth.invite.create` / `.accept` | invito |
| `group.created` / `.updated` / `.deleted` | `/api/admin/rbac/groups/*` (mig 015) |
| `group.member.added` / `.removed` | membership mutation |
| `group.role.granted` / `.revoked` | role attach/detach al gruppo |
| `admin.user.create` | `POST /api/admin/rbac/users` (admin-driven create + `password_must_change=true`) |
| `admin.user.activate` / `.deactivate` | `PATCH /api/admin/rbac/users/{id}` (lifecycle) |
| `admin.user.delete` | `DELETE /api/admin/rbac/users/{id}` (hard delete admin-driven) |
| `rbac.role.assign` / `.revoke` | RBAC ops |
| `admin.scaffold.preview` / `.apply` | wizard |
| `admin.tenant.activate` / `.deactivate` | pack switch |
| `ingest.start` / `.complete` / `.failed` | pipeline |
| `chat.turn` | RAG turn |
| `feedback.submit` | thumbs up/down |
| `runtime.restart` | worker restart |

Schema: `(id, event_type, user_id, tenant_id, details JSONB, created_at)`. Indice su `created_at`, `event_type`, `user_id`.

Retention default: **90 giorni** (configurabile via job di pulizia in `operations.md`).

## 5. Rate limiting

`llm_wiki/auth/rate_limit.py` — sliding window 60s.

| Scope | Default | Variabile |
|-------|---------|-----------|
| Login per IP | 10/min | `RATE_LIMIT_LOGIN_PER_MIN_IP` |
| Login per email | 5/min | `RATE_LIMIT_LOGIN_PER_MIN_EMAIL` |
| Register per IP | 5/h | `RATE_LIMIT_REGISTER_PER_HOUR_IP` |
| Refresh per IP | 30/min | `RATE_LIMIT_REFRESH_PER_MIN_IP` |
| User ops | 120/min | `RATE_LIMIT_USER_PER_MINUTE` |
| Admin ops | 60/min | `RATE_LIMIT_ADMIN_PER_MINUTE` |
| Ingest | 30/min | `RATE_LIMIT_JOB_PER_MINUTE` |

Backend: `memory` (single-instance) o `redis` (distribuito). Headers su 429: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset` (unix ts).

## 6. Hardening HTTP

Middleware (attivati con `SECURITY_HEADERS_ENABLED=true`):

| Header | Valore |
|--------|--------|
| `Content-Security-Policy` | `default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'` (override via `CONTENT_SECURITY_POLICY`) |
| `X-Frame-Options` | `DENY` |
| `X-Content-Type-Options` | `nosniff` |
| `Referrer-Policy` | `strict-origin-when-cross-origin` |
| `Permissions-Policy` | `camera=(), microphone=(), geolocation=()` |
| `Strict-Transport-Security` | `max-age=31536000; includeSubDomains` (solo se `ENABLE_HSTS=true`) |

CORS: `CORS_ALLOW_ORIGINS` whitelist. `Allow-Credentials=true` per cookie refresh.

## 7. Admin API gating

L'admin API (`/api/admin/*`) ha **due gate** indipendenti:

1. **Network-level** — `_AdminLoopbackGuard` middleware: rifiuta clients non-loopback **prima** che l'handler giri (`ADMIN_API_LOOPBACK_ONLY=true` di default).
2. **Permission-level** — `require_permission("admin.*")` per RBAC.

Pattern produzione:

- `ADMIN_API_LOOPBACK_ONLY=true` sempre → admin solo via SSH+curl o reverse proxy interno.
- Alternativa zero-trust: `ADMIN_API_ENABLED=false` + uso esclusivo CLI sull'host.

## 8. Secrets management

| Secret | Dove | Rotation |
|--------|------|----------|
| `SECRET_KEY` (JWT) | `.env`, **mai in git** | Rotation invalida tutti i JWT in flight (utenti devono re-login). |
| `POSTGRES_PASSWORD` | `.env` / vault esterno | Rotation richiede ALTER USER + restart. |
| `OPENAI_API_KEY` | `.env` | Rotation: rimpiazzo a caldo, restart raccomandato. |
| Refresh tokens | DB (hash) | Auto-rotation ogni `/auth/refresh`. |
| Bootstrap admin password | stderr (una volta) o `ADMIN_BOOTSTRAP_PASSWORD` | Forzato al primo login. |
| Invitation tokens | DB (hash) | TTL 24h default. |

Pre-commit hook + `ruff` controllano per pattern secret hardcoded.

## 9. Modelli di minaccia coperti

| Minaccia | Mitigazione |
|----------|-------------|
| Brute force login | Rate limit IP+email + delay incrementale. |
| Credential stuffing | Stesso + audit log per detection. |
| Token theft (XSS) | Access token in memory only; refresh in `httpOnly` cookie. |
| CSRF | Refresh `SameSite=Strict`, no auth via cookie. |
| Replay refresh token | Family-based revocation. |
| SQL injection | psycopg parametrizzato; nessuna concat. |
| Tenant cross-read | RLS policy server-side; ruolo applicativo non-superuser. |
| Privilege escalation | Hierarchy-aware role assignment + audit. |
| Path traversal (uploads) | Whitelist filename + sanitize; raw upload va in tmp validato. |
| Admin endpoint exposure | Loopback guard + RBAC. |
| Markdown XSS | Renderer rehype-sanitize lato frontend. |
| Sensitive log leak | Logger filter su `password`, `token`, `Authorization`. |

## 10. Compliance hooks

- **GDPR right to erasure**: `DELETE /api/admin/users/{id}` cascade su conversations, messages, memories, refresh_tokens. Audit events conservati anonimizzati (`user_id=NULL`).
- **GDPR data export**: `GET /api/me/export` (futuro) — bundle ZIP user-scoped.
- **SOC2 audit trail**: `audit_events` retention configurabile.
- **Data residency**: nessun egress non controllato; LLM esterno (OpenAI) opzionale.

## Riferimenti codice

| Componente | File |
|-----------|------|
| Token issue/rotate | `llm_wiki/auth/tokens.py` |
| Password hashing | `llm_wiki/auth/passwords.py` |
| Permission catalog | `llm_wiki/auth/permissions.py` |
| Rate limiter | `llm_wiki/auth/rate_limit.py` |
| Invitations | `llm_wiki/auth/invitations.py` |
| Audit | `llm_wiki/auth/audit.py` |
| Bootstrap admin | `llm_wiki/auth/bootstrap.py` |
| FastAPI deps | `llm_wiki/auth/dependencies.py` |
| Tenant context middleware | `llm_wiki/auth/tenant_context.py` + `auth/middleware.py` |
| Auth router | `llm_wiki/api/routers/auth.py` |
| RBAC router | `llm_wiki/api/routers/rbac.py` |
| Migrations RBAC/RLS | `alembic/versions/006*`, `007*`, `008*`, `009*` |
