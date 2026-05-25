# ADR-0005: Vector Store Abstraction Layer

**Status:** Accepted
**Date:** 2026-05-03

## Context

MVP usa ChromaDB locale (single-process). Multi-tenant post-MVP richiede Qdrant cluster con namespace isolation. Cambiare backend deve essere config flip, non rewrite agenti/services.

## Decision

Introdotto `services/vectorstores/` package:

- [`base.py`](../../docheck-engine/src/docheck/services/vectorstores/base.py) — `VectorStore` Protocol con `upsert`, `query`, `delete_collection`.
- [`chroma.py`](../../docheck-engine/src/docheck/services/vectorstores/chroma.py) — implementazione ChromaDB (default).
- [`qdrant.py`](../../docheck-engine/src/docheck/services/vectorstores/qdrant.py) — implementazione Qdrant (multi-tenant).
- Factory `get_store()` ritorna istanza per `settings.vector_backend`.

**Tenant isolation:** collection name prefisso `{tenant_id}__{collection}` via `current_tenant()` ContextVar (vedi [`core/tenant.py`](../../docheck-engine/src/docheck/core/tenant.py)).

**Compatibility:** `services/embedding.py` mantiene shim `_ChromaCollectionShim` con API ChromaDB-style (ids/distances/documents/metadatas keyed dict) per non rompere agent code esistente.

## Consequences

**Positive**

- Switch backend = `DOCHECK_VECTOR_BACKEND=qdrant` + `DOCHECK_QDRANT_URL=...`.
- Tenant scoping centralizzato (un solo punto da auditare).
- Test possibile mockare `VectorStore` Protocol senza dipendenze Chroma/Qdrant.

**Negative**

- API surface comune limita a feature subset (Chroma `where_document` text search non esposto).
- Qdrant `id` deve essere int o UUID — wrapping `str(hit.id)` per uniformità API.

## Alternatives Considered

- **LangChain VectorStore base class**: troppi adapter già esistenti ma over-engineered, dependency drift.
- **LlamaIndex VectorStoreIndex**: stesso issue + opinionated retrieval pipeline.
- **Direct backend selection at agent level**: ogni agente deve sapere backend → cattiva separazione.
