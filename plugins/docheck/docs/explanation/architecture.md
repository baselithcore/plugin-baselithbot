# Architecture

doCheck è un sistema layered, modulare, deployabile come monorepo con due artefatti principali: `docheck-engine` (FastAPI Python) e `docheck-ui` (Next.js + Electron).

Questo documento è la spiegazione concettuale dell'architettura. Per spec storica completa: [blueprint/01_core_architecture.md](../../blueprint/01_core_architecture.md).

## Vista layered

```
┌─────────────────────────────────────────────────────────────┐
│  PRESENTATION (Electron + Next.js + shadcn/ui)              │
│  Document Viewer · Findings Panel · Policy Manager · Audit  │
└──────────────────────────┬──────────────────────────────────┘
                           │ HTTP/WS via Unix socket
┌──────────────────────────▼──────────────────────────────────┐
│  API GATEWAY (FastAPI)                                      │
│  AuthN JWT EdDSA · RBAC dependency · Tenant middleware      │
│  Pydantic validation · Audit emitter · CORS allow-list      │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  ORCHESTRATION (LangGraph StateMachine)                     │
│  Classifier → Structurer → [Legal | Tech | PII] → Synth     │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────┬───────────────┼─────────────────┬────────────────┐
│ INGEST   │ INDEX         │ INFERENCE       │ PERSISTENCE    │
│ pdfplumb │ ChromaDB      │ vLLM (DGX)      │ SQLCipher      │
│ PaddleOCR│ Qdrant (multi)│ Ollama (dev)    │ Postgres+RLS   │
│ docx/xlsx│ BGE-M3 embed  │ Mock (test)     │ Audit log      │
└──────────┴───────────────┴─────────────────┴────────────────┘
```

## Perché layered

Decisioni motivate:

1. **Gateway separato dall'orchestrazione** → API stabile mentre la pipeline agentica evolve (nuovi agenti, nuove topology) senza breaking change client.
2. **LangGraph fra API e LLM** → state machine versionabile, parallel fan-out, retry/repair locali al nodo. Vedi [agentic-flow.md](agentic-flow.md).
3. **Vector store dietro abstraction** → swap Chroma↔Qdrant senza touching agents ([ADR-0005](../adr/0005-vector-store-abstraction.md)).
4. **DB backend dietro abstraction** → SQLCipher single-tenant ↔ Postgres+RLS multi-tenant ([ADR-0006](../adr/0006-postgres-rls-multitenant.md), [ADR-0008](../adr/0008-encryption-at-rest-strategy.md)).

## Componenti chiave

### API Gateway ([docheck-engine/src/docheck/api/](../../docheck-engine/src/docheck/api/))

- FastAPI app con lifespan: setup logging → mkdir storage → setup tracing → migrate DB → install RLS hook → reindex policy.
- Middleware (ordine inserimento, esecuzione inversa): `RequestId` → `Tenant` → `SecurityHeaders` → CORS.
- Router `/api/v1` aggrega submodule: `auth`, `routes` (documents/health), `policies`, `audit`, `metrics`, `system`, `findings`, `summary`, `export`, `workspace`.
- Dependency `current_principal()` accetta Bearer JWT (priority) o `X-User-Id` (legacy MVP). `require(resource, action)` fa enforcement RBAC.
- Trasporto: Unix socket (`storage/docheck.sock`) di default. TCP loopback opt-in via `DOCHECK_BIND_TCP`.

### Orchestration ([agents/graph.py](../../docheck-engine/src/docheck/agents/graph.py))

LangGraph compilato con `StateGraph[ParallelState]`. Topology:

```
classifier → structurer ─┬─> legal      ─┐
                         ├─> technical  ─┼─> synthesizer → END
                         └─> pii        ─┘
```

- `Annotated[list[Finding], add]` reducer permette merge concorrente sicuro.
- `ClassifierAgent` ([ADR-0011](../adr/0011-document-type-taxonomy.md)) determina `doc_type` → applicability filter per agente.
- Repair retry su validation Pydantic fail (max 1) → failover deterministico (skip + push errore in `state.errors`).

Dettagli: [agentic-flow.md](agentic-flow.md).

### Persistence ([db/](../../docheck-engine/src/docheck/db/))

- SQLAlchemy 2.0 async + `AsyncSession`.
- Tabelle principali: `users`, `roles`, `user_roles`, `permissions`, `documents`, `document_chunks`, `policies`, `rules`, `reports`, `audit_log`, `decisions`.
- `TenantMixin` aggiunge colonna `tenant_id` con default `current_tenant()`.
- Backend swap `sqlite|postgres` via `DOCHECK_DB_BACKEND`. SQLCipher attivato via `DOCHECK_DB_ENCRYPTION_ENABLED`.
- Postgres RLS: `install_rls_hook()` setta GUC `app.tenant_id` per session. Policy applicata via Alembic 0003.

### Inference ([services/llm.py](../../docheck-engine/src/docheck/services/llm.py))

Client OpenAI-compatible. Provider swap via `DOCHECK_LLM_PROVIDER`:

- `vllm` — produzione su DGX Spark, `Llama-3.3-70B-Instruct Q4_K_M`.
- `ollama` — dev locale, `llama3.1:8b` o `qwen2.5:3b`.
- `openai-compatible` — qualsiasi server compatibile (mock LLM in test).

Retry interno + timeout configurabile (`DOCHECK_LLM_REQUEST_TIMEOUT_S`). JSON-mode per output strutturato. Temperature `0.1`, top_p `0.9` (determinismo).

### Indexing ([services/embedding.py](../../docheck-engine/src/docheck/services/embedding.py) + [vectorstores/](../../docheck-engine/src/docheck/services/vectorstores/))

- Embedding: BGE-M3 multilingue (IT+EN nativi, ~570M params). Caricato in-process.
- Vector store: ChromaDB (default, persist su disco) o Qdrant (multi-tenant). Collection prefix `{tenant_id}__{name}`.
- Policy index: rebuild on startup (`policy_index.reindex_all()`). Invalidato su `policy.version` bump.

### Caching ([services/cache.py](../../docheck-engine/src/docheck/services/cache.py))

3 livelli:

1. **embedding_cache** — `sha256(text) + model_id` → vector ref.
2. **policy_index_cache** — Chroma persistente, invalidato su bump version.
3. **verdict_cache** — `sha256(chunk_hash || rule_id || rule_version || model_id)` → Finding JSON. Cross-document.

Hit ratio target ≥ 60% post-warmup. Endpoint `GET /api/v1/system/cache` espone metriche.

### Frontend ([docheck-ui/](../../docheck-ui/))

- Next.js 15 App Router. Server component default; `'use client'` solo dove serve.
- Layout 60/40 split-pane: viewer (PDF/text) + findings panel virtualizzato.
- Stato globale: Zustand (UI state) + TanStack Query (server state, dedup, cache).
- Streaming pipeline: hook `useAnalysisStream` consuma WebSocket `/ws/analysis/{doc_id}` → aggiorna `PhaseIndicator` + popola findings live.
- Electron shell: `nodeIntegration: false`, `contextIsolation: true`, `sandbox: true`. Preload espone API narrow.

## Deploy targets

| Target | Stack | DB | Vector | LLM |
|--------|-------|-----|--------|-----|
| Workstation MVP | Electron + engine | SQLCipher | Chroma | vLLM remoto / Ollama locale |
| Server DGX single-tenant | Docker Compose | SQLCipher | Chroma | vLLM container |
| Multi-tenant on-prem | K8s + Helm | Postgres+RLS | Qdrant | vLLM service |
| Air-gapped | Docker offline | SQLCipher / Postgres | Chroma / Qdrant | vLLM con mirror pesi |

## Vincoli architettura

- File source ≤ 500 LOC ([CLAUDE.md §1.1](../../CLAUDE.md)).
- Cambio stack → ADR obbligatorio.
- Zero egress durante analisi (gate CI tcpdump).
- Glass-box mandatory: ogni finding tracciabile a evidence + policy excerpt verbatim.

## Vedi anche

- [agentic-flow.md](agentic-flow.md) — pipeline LangGraph.
- [glass-box.md](glass-box.md) — pillar di prodotto.
- [security-model.md](security-model.md) — threat model + controlli.
- [multitenant.md](multitenant.md) — isolation strategy.
- [blueprint/](../../blueprint/) — design intent originale.
