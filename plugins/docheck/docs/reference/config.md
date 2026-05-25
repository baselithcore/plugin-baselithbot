# Configuration Reference

Variabili d'ambiente `DOCHECK_*` consumate dall'engine. Source: [docheck-engine/src/docheck/core/config.py](../../docheck-engine/src/docheck/core/config.py) (Pydantic Settings).

Loading order:

1. Process environment.
2. `.env` file in CWD del processo engine.
3. Default in `Settings` class.

## Core

| Var | Default | Note |
|-----|---------|------|
| `DOCHECK_DEBUG` | `false` | Verbose log + uvicorn reload (dev only). |
| `DOCHECK_STORAGE_ROOT` | `./storage` | Root per docs/, chroma/, sqlite, audit key. |
| `DOCHECK_DB_PATH` | `./storage/docheck.db` | SQLite file (single-tenant). |
| `DOCHECK_SOCKET_PATH` | `./storage/docheck.sock` | Unix socket bind path. |
| `DOCHECK_BIND_TCP` | unset | Es. `127.0.0.1:8765` per dev browser-based. **Mai non-loopback in prod**. |

## Database

| Var | Default | Note |
|-----|---------|------|
| `DOCHECK_DB_BACKEND` | `sqlite` | `sqlite` (single-tenant) o `postgres` (multi-tenant). |
| `DOCHECK_POSTGRES_DSN` | `""` | `postgresql+asyncpg://user:pw@host/db`. Required se `DB_BACKEND=postgres`. |
| `DOCHECK_DB_ENCRYPTION_ENABLED` | `false` | Attiva SQLCipher (cipher_page_size=4096, kdf_iter=256000, HMAC_SHA512). |
| `DOCHECK_DB_KEY_KEYRING_SERVICE` | `docheck` | Service name in OS keychain per master DB key. |
| `DOCHECK_DB_KEY_KEYRING_USER` | `master` | User name in OS keychain. |

## LLM

| Var | Default | Note |
|-----|---------|------|
| `DOCHECK_LLM_PROVIDER` | `ollama` | `ollama` \| `vllm` \| `openai-compatible`. |
| `DOCHECK_LLM_BASE_URL` | `http://127.0.0.1:11434/v1` | OpenAI-compatible endpoint. |
| `DOCHECK_LLM_API_KEY` | `ollama` | Placeholder per server locali. |
| `DOCHECK_LLM_PRIMARY_MODEL` | `llama3.1:8b` | Production: `llama-3.3-70b-instruct-q4_k_m` (vLLM). |
| `DOCHECK_LLM_FALLBACK_MODEL` | `qwen2.5:3b` | Usato se primary timeout/error. |
| `DOCHECK_LLM_TEMPERATURE` | `0.1` | Determinismo. Non aumentare oltre 0.3 per compliance. |
| `DOCHECK_LLM_TOP_P` | `0.9` | |
| `DOCHECK_LLM_REQUEST_TIMEOUT_S` | `120.0` | Per request. |

## Embedding & Vector

| Var | Default | Note |
|-----|---------|------|
| `DOCHECK_EMBEDDING_MODEL` | `BAAI/bge-m3` | Multilingue IT+EN. ~570M params. |
| `DOCHECK_VECTOR_BACKEND` | `chroma` | `chroma` \| `qdrant`. |
| `DOCHECK_CHROMA_PERSIST_DIR` | `./storage/chroma` | Persistent dir. |
| `DOCHECK_QDRANT_URL` | `""` | Es. `http://qdrant:6333`. Required se `VECTOR_BACKEND=qdrant`. |

## OCR

| Var | Default | Note |
|-----|---------|------|
| `DOCHECK_OCR_ENGINE` | `paddleocr` | `paddleocr` \| `tesseract`. Fallback su PDF scanned. |

## Audit

| Var | Default | Note |
|-----|---------|------|
| `DOCHECK_AUDIT_SIGNING_KEY_PATH` | `./storage/audit_ed25519.key` | File mode 0600. Production: keychain. |

## Retention

| Var | Default | Note |
|-----|---------|------|
| `DOCHECK_RETENTION_DEFAULT_DAYS` | `365` | TTL default per documenti caricati (purge job). |

## Multi-tenant

| Var | Default | Note |
|-----|---------|------|
| `DOCHECK_MULTITENANT_ENABLED` | `false` | Attiva tenant context resolution + RLS hook. |

## OIDC

Attivato quando `DOCHECK_OIDC_ISSUER` è settato.

| Var | Default | Note |
|-----|---------|------|
| `DOCHECK_OIDC_ISSUER` | `""` | Issuer URL (es. Keycloak realm). |
| `DOCHECK_OIDC_AUDIENCE` | `docheck` | `aud` claim atteso. |
| `DOCHECK_OIDC_JWKS_URI` | `""` | Override; default discovery via `${issuer}/.well-known/openid-configuration`. |

## Built-in policy controls

`DocCheck_Builtin` è policy deterministica baseline read-only sempre applicata.

| Var | Formato | Esempio |
|-----|---------|---------|
| `DOCHECK_BUILTIN_DISABLED_RULES` | CSV rule_id | `FORMAT-DATE-ISO,ID-CF-CHECKSUM` |
| `DOCHECK_BUILTIN_SEVERITY_OVERRIDES` | `RULE=SEVERITY,...` | `FORMAT-DATE-ISO=INFO,DEADLINE-STRICT=WARN` |

## Esempio `.env` completo

```dotenv
# Core
DOCHECK_DEBUG=false
DOCHECK_STORAGE_ROOT=./storage
DOCHECK_DB_PATH=./storage/docheck.db
DOCHECK_SOCKET_PATH=./storage/docheck.sock
# DOCHECK_BIND_TCP=127.0.0.1:8765    # opt-in dev browser

# DB (multi-tenant Postgres)
# DOCHECK_DB_BACKEND=postgres
# DOCHECK_POSTGRES_DSN=postgresql+asyncpg://docheck:secret@postgres/docheck
# DOCHECK_MULTITENANT_ENABLED=true

# Encryption at-rest (production single-tenant)
# DOCHECK_DB_ENCRYPTION_ENABLED=true
# DOCHECK_DB_KEY_KEYRING_SERVICE=docheck
# DOCHECK_DB_KEY_KEYRING_USER=master

# LLM (production vLLM)
DOCHECK_LLM_PROVIDER=vllm
DOCHECK_LLM_BASE_URL=http://vllm:8000/v1
DOCHECK_LLM_PRIMARY_MODEL=llama-3.3-70b-instruct-q4_k_m
DOCHECK_LLM_FALLBACK_MODEL=llama-3.1-8b-instruct
DOCHECK_LLM_TEMPERATURE=0.1
DOCHECK_LLM_REQUEST_TIMEOUT_S=180

# Embedding / Vector
DOCHECK_EMBEDDING_MODEL=BAAI/bge-m3
DOCHECK_VECTOR_BACKEND=chroma
DOCHECK_CHROMA_PERSIST_DIR=./storage/chroma
# DOCHECK_VECTOR_BACKEND=qdrant
# DOCHECK_QDRANT_URL=http://qdrant:6333

# OCR
DOCHECK_OCR_ENGINE=paddleocr

# Retention
DOCHECK_RETENTION_DEFAULT_DAYS=365

# OIDC (production)
# DOCHECK_OIDC_ISSUER=https://kc.example.invalid/realms/docheck
# DOCHECK_OIDC_AUDIENCE=docheck
```

## Validation

`Settings` è Pydantic Settings: tipo errato → `ValidationError` allo startup, container fail-fast. Niente default magici a runtime.

## Vedi anche

- [api/endpoints.md](../api/endpoints.md) — uso runtime delle config.
- [runbooks/setup-dev.md](../runbooks/setup-dev.md) — setup dev `.env`.
- [runbooks/deploy-dgx.md](../runbooks/deploy-dgx.md) — env production.
