# Configuration Reference

Catalogo esaustivo delle variabili d'ambiente. Tutte vengono lette in `llm_wiki/config.py` all'import; i default sono pensati per **sviluppo locale**. In produzione → vedi [`deployment.md`](deployment.md).

## Convenzioni

- File: `.env` nella repo root (caricato con `python-dotenv`, `override=False`).
- **Shell exports vincono su `.env`** — `_warn_shell_env_conflicts()` logga warning in caso di drift.
- `_drop_stale_empty_inheritance()` rimuove pre-load `APP_DOMAIN`/`WIKI_ROOT`/`DOMAIN_PACK_DIR` vuoti ereditati dal parent (fix worker uvicorn `--reload`).
- Boolean: `true|false`, case-insensitive.
- Path: assoluti consigliati; relativi sono risolti rispetto a repo root.

## 1. Domain Pack

| Variabile | Default | Note |
|-----------|---------|------|
| `APP_DOMAIN` | `""` (setup mode) | Verticale attivo. Vuoto = setup mode (admin loopback abilitato, RAG disabilitato). |
| `WIKI_ROOT` | repo root | Vault condiviso. Risoluzione: esplicito → `WIKI_ROOT_<APP_DOMAIN>` legacy → repo root. |
| `WIKI_ROOT_<DOMAIN>` | — | Override per pack (scritto dal Wizard). `<DOMAIN>` in MAIUSCOLO. |
| `WIKI_DIR` | `wiki` | Subdir generata dall'engine. |
| `RAW_DIR` | `raw` | Subdir read-only (sorgenti PDF). Scrittura → `RawDirWriteAttempt`. |
| `DOMAIN_PACK_DIR` | `domains/<APP_DOMAIN>` | Override path del pack. |

## 2. LLM Provider

| Variabile | Default | Note |
|-----------|---------|------|
| `LLM_VENDOR` | `ollama` | `ollama` \| `openai`. |
| `OLLAMA_URL` | `http://localhost:11434` | — |
| `OLLAMA_MODEL` | `llama3.1:8b` | Modello RAG. |
| `INGEST_OLLAMA_MODEL` | `llama3.2:latest` | Modello ingest (più piccolo). |
| `OPENAI_API_KEY` | — | Solo per vendor `openai`. |
| `OPENAI_MODEL` | `gpt-4o-mini` | RAG. |
| `INGEST_OPENAI_MODEL` | `gpt-4o-mini` | Ingest. |
| `LLM_TIMEOUT` | `600.0` | Secondi. |
| `LLM_KEEP_ALIVE` | `30m` | Solo Ollama; tiene il modello in VRAM. |
| `INGEST_MAX_CONCURRENT` | `1` | Ollama serializza inferenza single-model. **Aumenta solo su multi-GPU.** |
| `INGEST_OLLAMA_NUM_CTX` | `8192` | Default Ollama 2048 troppo basso per ingest. |
| `INGEST_LOOSE_JSON` | `true` | `format="json"` invece di JSON-schema constrained (più veloce). |
| `INGEST_BATCH_CLASSIFY_PLAN` | `true` | Unisce classify+plan in una call (-30÷90s). Disattiva su modelli ≤3B. |
| `INGEST_CRITIC_MAX_ITER` | `1` | Max loop linter→critic. Aumenta solo su API remote veloci. |
| `SYNTHESIS_MODEL` | derivato | Override modello per prompt synthesizer (vedi `architecture.md`). |

## 3. Embedding & Retrieval

| Variabile | Default | Note |
|-----------|---------|------|
| `EMBEDDER_MODEL` | `BAAI/bge-m3` | Dense + lexical (1024 dim). |
| `EMBEDDER_DEVICE` | `auto` | `cuda` \| `cpu` \| `mps`. |
| `EMBEDDER_BATCH_SIZE` | `32` | — |
| `RERANKER_ENABLED` | `true` | Cross-encoder post-retrieval. |
| `RERANKER_MODEL` | `BAAI/bge-reranker-v2-m3` | — |
| `HYBRID_ENABLED` | `true` | Dense + BM25. |
| `HYBRID_USE_COLBERT` | `true` | Late-interaction; più lento, più qualità. |
| `HYBRID_PREFETCH_LIMIT` | `50` | Candidati pre-fusione. |
| `MMR_ENABLED` | `true` | Diversifica top-K. |
| `MMR_LAMBDA` | `0.7` | 1.0=rilevanza, 0.0=diversità. |
| `RETRIEVAL_TOP_K` | `8` | Chunk in contesto RAG. |
| `CHUNK_SIZE` | `700` | Caratteri. |
| `CHUNK_OVERLAP` | `120` | — |
| `CITATION_VALIDATION_ENABLED` | `true` | Estrae `[[folder/slug]]` e valida. |
| `CITATION_STRICT_GROUNDING` | `true` | Citazioni devono essere nei doc retrievati. |
| `CITATION_REPAIR_ENABLED` | `false` | Rigenera (+1 LLM call) se invalide. |
| `HYDE_ENABLED` | `false` | Hypothetical Document Embeddings. |
| `QUERY_DECOMPOSITION_ENABLED` | `false` | Multi-slot. |
| `CONTEXTUAL_ENABLED` | `false` | Contextual retrieval (Anthropic-style). |

## 4. Vector Store (Qdrant)

| Variabile | Default | Note |
|-----------|---------|------|
| `QDRANT_MODE` | `server` | `embedded` \| `server`. |
| `QDRANT_URL` | `http://localhost:6333` | Server mode. |
| `QDRANT_API_KEY` | — | Cluster managed. |
| `COLLECTION_NAME` | `<APP_DOMAIN>-wiki` | Auto-derivato per pack. |

## 5. Graph DB (opzionale)

| Variabile | Default | Note |
|-----------|---------|------|
| `GRAPH_DB_ENABLED` | `false` | FalkorDB. |
| `FALKOR_HOST` | `localhost` | — |
| `FALKOR_PORT` | `6379` | — |

## 6. Postgres + Auth

| Variabile | Default | Note |
|-----------|---------|------|
| `POSTGRES_ENABLED` | auto | Vero se `DATABASE_URL` o `POSTGRES_HOST` presenti. |
| `DATABASE_URL` | — | Override completo URI. |
| `POSTGRES_HOST` | `localhost` | — |
| `POSTGRES_PORT` | `5432` (compose: `5433`) | — |
| `POSTGRES_DB` | `llm_wiki` | — |
| `POSTGRES_USER` | `llm_wiki` | App user (non-superuser; RLS-bound). |
| `POSTGRES_PASSWORD` | `llm_wiki_dev` | **Cambiare in prod.** |
| `POSTGRES_POOL_MIN` | `2` | psycopg pool. |
| `POSTGRES_POOL_MAX` | `10` | — |
| `SECRET_KEY` | — | **Obbligatoria se `AUTH_REQUIRED=true`.** Min 32 byte; HS256. |
| `AUTH_REQUIRED` | `false` | Blocca chat/conversazioni/memorie dietro login. |
| `AUTH_PUBLIC_REGISTRATION` | `false` | `true` = self-signup. |
| `AUTH_COOKIE_SECURE` | `true` | `false` solo in dev su `http://`. |
| `AUTH_COOKIE_SAMESITE` | `strict` | `lax` se cross-domain. |
| `AUTH_COOKIE_NAME` | `llm_wiki_refresh` | Refresh cookie. |
| `ACCESS_TOKEN_TTL_MINUTES` | `1440` (24h) | JWT lifetime. |
| `REFRESH_TOKEN_TTL_DAYS` | `30` | Refresh rotation lifetime. |
| `MULTI_TENANT_REQUIRED` | `=AUTH_REQUIRED` | Forza invariante 1:1 user↔tenant. |
| `INVITATION_TTL_HOURS` | `24` | TTL token invito. |

## 7. Bootstrap admin iniziale

| Variabile | Default | Note |
|-----------|---------|------|
| `ADMIN_BOOTSTRAP_AUTOSTART` | `false` | Se `true`, crea admin al primo boot se `users` vuota. |
| `ADMIN_BOOTSTRAP_EMAIL` | `admin@localhost` | — |
| `ADMIN_BOOTSTRAP_PASSWORD` | (generata) | Se omessa, viene generata e stampata su stderr una volta. |

## 8. Rate limiting

| Variabile | Default | Note |
|-----------|---------|------|
| `CACHE_BACKEND` | `memory` | `memory` \| `redis`. Distribuito → `redis`. |
| `CACHE_REDIS_URL` | `redis://localhost:6380/0` | — |
| `RATE_LIMIT_USER_PER_MINUTE` | `120` | Chat, feedback, memorie. |
| `RATE_LIMIT_ADMIN_PER_MINUTE` | `60` | RBAC ops. |
| `RATE_LIMIT_JOB_PER_MINUTE` | `30` | Ingest jobs. |
| `RATE_LIMIT_LOGIN_PER_MIN_IP` | `10` | Login per IP. |
| `RATE_LIMIT_LOGIN_PER_MIN_EMAIL` | `5` | Login per email. |
| `RATE_LIMIT_REGISTER_PER_HOUR_IP` | `5` | — |
| `RATE_LIMIT_REFRESH_PER_MIN_IP` | `30` | — |

## 9. Security headers / hardening

| Variabile | Default | Note |
|-----------|---------|------|
| `SECURITY_HEADERS_ENABLED` | `true` | CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy. |
| `ENABLE_HSTS` | `false` | Solo dietro HTTPS. |
| `CONTENT_SECURITY_POLICY` | (default safe) | Override custom. |
| `CORS_ALLOW_ORIGINS` | `http://localhost:5173,http://localhost:3000` | CSV. |
| `CORS_ALLOW_CREDENTIALS` | `true` | Cookie refresh. |

## 10. Admin API

| Variabile | Default | Note |
|-----------|---------|------|
| `ADMIN_API_ENABLED` | `true` | Mount di `/api/admin/*`. |
| `ADMIN_API_LOOPBACK_ONLY` | `true` | `_AdminLoopbackGuard` rifiuta non-127.0.0.1 prima dell'handler. |
| `AUTO_INGEST_ON_STARTUP` | `true` | Coda auto-ingest dei PDF in `raw/` privi di source page. |

## 11. Feedback

| Variabile | Default | Note |
|-----------|---------|------|
| `FEEDBACK_ENABLED` | `true` | — |
| `FEEDBACK_LOG_PATH` | `<WIKI_ROOT>/.feedback.jsonl` | Append-only mirror. |

## 12. Logging & Observability

| Variabile | Default | Note |
|-----------|---------|------|
| `LOG_LEVEL_CONSOLE` | `INFO` | — |
| `LOG_FORMAT` | `text` | `text` \| `json` (per Promtail/Loki). |
| `LOG_FILE_PATH` | — | Se settato, mirror su file. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | — | Es. `http://localhost:4318` attiva tracing. |
| `OTEL_SERVICE_NAME` | `llm-wiki` | — |
| `OTEL_RESOURCE_ATTRIBUTES` | — | Comma-sep `key=value`. |
| `PROMETHEUS_METRICS_ENABLED` | `true` | Espone `/metrics`. |

## 13. Ingest pipeline (extra)

| Variabile | Default | Note |
|-----------|---------|------|
| `INGEST_EXTRACTOR` | `auto` | `docling` \| `pymupdf` \| `pdfplumber` \| `auto`. |
| `INGEST_DRY_RUN` | `false` | Genera in `.new.md`/`.needs-review.md` ma non sostituisce. |
| `INGEST_LINTER_STRICT` | `true` | Fail-fast se sezioni richieste mancano. |

## Generare un `.env` per produzione

Esempio minimo template:

```ini
APP_DOMAIN=legal
WIKI_ROOT=/srv/llm-wiki/vaults/legal

LLM_VENDOR=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o
INGEST_OPENAI_MODEL=gpt-4o-mini

DATABASE_URL=postgresql://app:***@db.internal:5432/llm_wiki
SECRET_KEY=<48 byte token_urlsafe>
AUTH_REQUIRED=true
AUTH_PUBLIC_REGISTRATION=false
AUTH_COOKIE_SECURE=true
AUTH_COOKIE_SAMESITE=strict

CACHE_BACKEND=redis
CACHE_REDIS_URL=redis://redis.internal:6379/0

ADMIN_API_LOOPBACK_ONLY=true
SECURITY_HEADERS_ENABLED=true
ENABLE_HSTS=true
CORS_ALLOW_ORIGINS=https://wiki.example.com

LOG_FORMAT=json
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
PROMETHEUS_METRICS_ENABLED=true
```

## Validare la configurazione

```bash
python -m llm_wiki doctor --strict
python -m llm_wiki status --json
```

`doctor` controlla pack, vault, Qdrant, LLM, Postgres, conflitti shell↔.env e segnala valori sospetti (es. `SECRET_KEY` < 32 byte, `AUTH_COOKIE_SECURE=false` con `AUTH_REQUIRED=true`).
