# API HTTP Reference

Server FastAPI esposto da `main.py`. Default bind: `127.0.0.1:8000`. CORS aperto su `localhost:5173`/`127.0.0.1:5173` (frontend Vite dev).

## 1. White-label endpoints (NUOVI)

### `GET /api/branding`

Restituisce le label del Domain Pack attivo. Consumato da `DomainContext` del frontend.

**Risposta** `200 OK`:

```json
{
  "domain": "insurance",
  "label": "Wiki Polizze Assicurative",
  "description": "Knowledge base contrattuale: Set Informativi, NTA, DIP, regolamenti IVASS, sentenze.",
  "language": "it",
  "ui": {
    "app_name": "Wiki Polizze",
    "short_name": "Polizze",
    "vault_label": "Vault contrattuale",
    "tagline": "Cerca clausole, garanzie ed esclusioni nelle Condizioni di Assicurazione.",
    "empty_state": "Carica un Set Informativo o le NTA per iniziare.",
    "page_type_labels": {
      "source": "Fonti",
      "concept": "Concetti / Garanzie",
      "entity": "Entità",
      "topic": "Temi"
    },
    "extra": {
      "badges": {
        "stato": ["vigente", "superata", "abrogata"],
        "rango": ["regolamento-ue", "cc-inderogabile", "..."]
      }
    }
  },
  "page_types": [
    {"id": "source", "label": "Fonte", "plural": "fonti", "folder": "sources"},
    {"id": "concept", "label": "Concetto / Garanzia", "plural": "concetti", "folder": "concepts"},
    {"id": "entity", "label": "Entità", "plural": "entità", "folder": "entities"},
    {"id": "topic", "label": "Tema", "plural": "temi", "folder": "topics"}
  ],
  "subtypes": {
    "source": ["polizza-set-informativo", "norme-assuntive", "..."],
    "concept": ["garanzia-assicurativa", "pack-opzionale", "..."],
    "entity": ["compagnia", "regolatore", "gestore"]
  },
  "groups": [
    {
      "key": "editions",
      "label": "Edizioni Prodotto",
      "page_type": "source",
      "group_by": ["codice-prodotto", "edizione-iso"],
      "extra_fields": ["modello", "stato", "edizione"]
    }
  ]
}
```

### `GET /api/groups`

Lista delle regole di grouping dichiarate dal pack. Sostituisce la logica `/api/editions` di rag-wiki.

**Risposta** `200 OK`:

```json
{
  "rules": [
    {
      "key": "editions",
      "label": "Edizioni Prodotto",
      "page_type": "source",
      "group_by": ["codice-prodotto", "edizione-iso"],
      "extra_fields": ["modello", "stato", "edizione"]
    }
  ]
}
```

### `GET /api/groups/{rule_key}`

Materializza una regola di grouping scansionando il vault.

**Esempio**: `GET /api/groups/editions`

**Risposta** `200 OK`:

```json
{
  "rule": { /* come sopra */ },
  "count": 3,
  "groups": [
    {
      "id": "casa-servizi-2024-06",
      "key": {"codice-prodotto": "casa-servizi", "edizione-iso": "2024-06-01"},
      "label": "Unipol Casa & Servizi — Ed. 06/2024",
      "members": [
        {
          "document_id": "sources/set-informativo-casa-servizi-062024",
          "title": "Set Informativo Unipol Casa & Servizi — Ed. 06/2024",
          "subtype": "polizza-set-informativo",
          "page_type": "source"
        },
        { /* NTA, DIP, … */ }
      ],
      "extras": {
        "modello": "PRD/12345/00/01",
        "stato": "vigente",
        "edizione": "01/06/2024"
      }
    }
  ]
}
```

**Errori**:

- `404 unknown grouping rule: <key>` se la regola non esiste nel pack

## 2. Status

### `GET /api/status`

Diagnostica completa: dominio + provider LLM + embedder + Qdrant + vault.

**Risposta** `200 OK`:

```json
{
  "domain": {
    "name": "insurance",
    "label": "Wiki Polizze Assicurative",
    "language": "it",
    "page_types": ["source", "concept", "entity", "topic"]
  },
  "provider": {
    "vendor": "ollama",
    "model": "llama3.1:8b",
    "endpoint": "http://localhost:11434"
  },
  "embedder": {
    "name": "BAAI/bge-m3",
    "dim": 1024,
    "hybrid": true
  },
  "reranker": {
    "enabled": true,
    "model": "BAAI/bge-reranker-v2-m3",
    "available": true,
    "input_mult": 5
  },
  "contextual": {"enabled": false, "model": "qwen2.5:7b-instruct", "available": false},
  "qdrant": {
    "mode": "server",
    "target": "http://localhost:6333",
    "available": true,
    "collection": "insurance-wiki",
    "vectors_count": 1234,
    "points_count": 1234
  },
  "graph": {"enabled": false},
  "vault": {"root": "/abs/path/vaults/insurance", "pages": 87},
  "features": {"feedback_enabled": true}
}
```

## 3. Chat (RAG)

### `POST /api/chat`

One-shot RAG sincrono.

**Body**:

```json
{
  "message": "Cosa copre la garanzia furto?",
  "history": [],
  "limit": 8,
  "graph": false
}
```

**Risposta** `200 OK`:

```json
{
  "answer": "In due righe: la garanzia Furto e Rapina copre [...].\n\nDettaglio: ...\n\nFonti:\n- [[concepts/garanzia-furto-e-rapina]] (art. 4.2 CdA)",
  "sources": [
    {
      "document_id": "concepts/garanzia-furto-e-rapina",
      "title": "Garanzia Furto e Rapina — Sezione 4",
      "score": 0.873,
      "relative_path": "wiki/concepts/garanzia-furto-e-rapina.md",
      "page_type": "concept",
      "subtype": "garanzia-assicurativa",
      "via_rinvio": false,
      "article_ref": null,
      "extra": { /* tutti gli altri campi frontmatter */ }
    }
  ],
  "hits": 8
}
```

### `POST /api/chat/stream`

Versione streaming. Body identico. Risposta `application/x-ndjson`:

```text
{"type":"agent","content":"Retriever"}
{"type":"step","content":"Hybrid retrieval (dense + sparse + ColBERT)…"}
{"type":"step","content":"Trovati 8 chunk rilevanti"}
{"type":"hits","count":8}
{"type":"agent","content":"RAG"}
{"type":"step","content":"Generazione risposta in corso…"}
{"type":"token","content":"In "}
{"type":"token","content":"due "}
{"type":"token","content":"righe"}
...
{"type":"sources","items":[{...}]}
{"type":"done"}
```

## 4. Wiki

### `GET /api/wiki/pages`

Indice completo per sidebar/autocomplete.

```json
{
  "count": 87,
  "pages": [
    {
      "document_id": "concepts/garanzia-furto",
      "title": "Garanzia Furto",
      "type": "concept",
      "category": "concepts",
      "tags": ["furto", "rapina"],
      "wikilinks_count": 5
    }
  ]
}
```

### `GET /api/wiki/page/{doc_id:path}`

Contenuto di una pagina specifica per preview citazioni.

**Esempio**: `GET /api/wiki/page/concepts/garanzia-furto`

```json
{
  "document_id": "concepts/garanzia-furto",
  "title": "Garanzia Furto",
  "type": "concept",
  "category": "concepts",
  "tags": ["furto"],
  "aliases": [],
  "wikilinks_out": ["sources/set-informativo-casa", "concepts/franchigie-e-scoperti"],
  "body": "## In due righe\n...\n## Cosa copre\n...",
  "relative_path": "wiki/concepts/garanzia-furto.md"
}
```

## 5. Ingest

### `POST /api/ingest/raw` (multipart)

Carica un PDF e lancia il job di ingest in background.

**Form fields**:

- `file` — file PDF (max 50 MB)
- `overwrite` (bool, default `false`) — sovrascrive pagine wiki esistenti
- `reindex` (bool, default `true`) — re-indicizza Qdrant dopo write
- `dry_run` (bool, default `false`) — non scrive su disco
- `only_source_page` (bool, default `false`) — genera solo `wiki/sources/*.md`
- `replace_existing` (bool, default `false`) — sovrascrive il PDF in `raw/` se esistente

**Risposta** `200 OK`:

```json
{
  "job_id": "abc123",
  "filename": "polizza-vita-2024.pdf",
  "size": 1234567,
  "status": "queued",
  "options": {"overwrite": false, "reindex": true, "dry_run": false, "only_source_page": false}
}
```

**Errori**:

- `400` filename non valido / estensione non ammessa
- `409` PDF già presente in `raw/` e `replace_existing=false`
- `413` file > 50 MB

### `GET /api/ingest/raw/jobs`

Lista job recenti (in-memory + persisted fallback).

```json
{
  "count": 2,
  "jobs": [
    {"id": "abc123", "filename": "polizza-vita-2024.pdf", "status": "running", "progress": 0.4, "events": [...]},
    {"id": "def456", "filename": "nta-casa-2023.pdf", "status": "completed", "progress": 1.0, "events": [...]}
  ]
}
```

### `GET /api/ingest/raw/jobs/{job_id}`

Snapshot di un singolo job.

### `GET /api/ingest/raw/jobs/{job_id}/stream`

NDJSON streaming degli eventi del job (replay history + live).

```text
{"type":"step","content":"Estrazione PDF (docling)…"}
{"type":"step","content":"Classificazione documento"}
{"type":"step","content":"Pianificazione: 1 source + 8 concept + 2 entity"}
{"type":"page","target":"wiki/sources/...","status":"written"}
{"type":"page","target":"wiki/concepts/...","status":"written"}
...
{"type":"done","summary":"source=polizza-vita-2024.pdf written=11 needs-review=0 errors=0"}
{"type":"final","status":"completed",...}
```

### `POST /api/ingest/file`

Re-indicizza un singolo `.md` esistente in Qdrant (no LLM):

```json
{"path": "wiki/concepts/franchigie-e-scoperti.md"}
```

### `POST /api/ingest`

Re-index completo di tutto il vault (blocking).

**Query**: `?concurrency=4`

### `GET /api/raw/files`

Lista PDF presenti in `raw/` (utile per UI dedupe pre-upload).

```json
{
  "count": 3,
  "files": [
    {"name": "set-informativo-casa.pdf", "size": 1234567, "modified": 1714560000.0}
  ]
}
```

## 6. Feedback

### `POST /api/feedback`

Append-only JSONL di voti utente (gating: `FEEDBACK_ENABLED=true`).

```json
{
  "message_id": "msg-uuid-123",
  "rating": "up",
  "reason": "Citazioni accurate",
  "question": "...",
  "answer": "...",
  "sources": [...],
  "edition": "casa-servizi-2024-06"
}
```

Risposta: `{"status": "ok"}` o `404 feedback disabled`.

## 7. Compatibilità con rag-wiki

| rag-wiki | wiki-white-label | Cambio |
 | --- | --- | --- |
| `GET /api/editions` | `GET /api/groups/editions` | Stesso payload, path diverso. Frontend insurance: aggiornare fetch |
| Tutto il resto | Identico | Drop-in replacement |

Per frontend custom in produzione che dipendono da `/api/editions`, esporre uno shim:

```python
# main.py — opzionale
@app.get("/api/editions")
def legacy_editions() -> dict[str, Any]:
    """Shim retrocompatibile per il frontend pre-white-label."""
    return get_groups("editions")
```

---

## 8. Auth & RBAC endpoints

Per il modello concettuale (JWT, refresh, RBAC, RLS) → [`auth-rbac.md`](auth-rbac.md).

### Convenzioni auth

- **Access token**: header `Authorization: Bearer <jwt>`. JWT HS256, payload include `user_id`, `tenant_id`, `perms[]`.
- **Refresh token**: cookie `llm_wiki_refresh` (`httpOnly`, `Secure`, `SameSite=Strict`). Inviato solo su `/auth/refresh`.
- **Errori**: 401 (non autenticato), 403 (autenticato ma permesso mancante), 429 (rate-limit).

### `POST /auth/bootstrap`

Crea il primo utente admin. **Loopback-only** (`ADMIN_API_LOOPBACK_ONLY=true`). Rate-limit `1/h`.

Funziona solo finché `users` è vuota.

```json
{ "email": "admin@example.com", "password": "..." }
```

→ `201` `{ access_token, user, expires_in }` + `Set-Cookie: llm_wiki_refresh`

### `GET /auth/bootstrap/status`

Pubblico. `200` `{ "needs_bootstrap": true|false }`.

### `GET /auth/invite/{token}`

Peek non distruttivo del token di invito. `200` `{ email, role_slug, expires_at, used: false }` o `404`.

### `POST /auth/invite/accept`

```json
{ "token": "...", "password": "...", "display_name": "Mario" }
```

Consuma invito + crea user/tenant + emette token. `201` come `/bootstrap`. Reuse → `404`.

### `POST /auth/register`

Solo se `AUTH_PUBLIC_REGISTRATION=true`. Rate-limit `5/h` per IP.

```json
{ "email": "...", "password": "...", "display_name": "Mario" }
```

→ `201` `{ access_token, user }` + cookie refresh.

### `POST /auth/login`

Rate-limit: `10/min` per IP, `5/min` per email.

```json
{ "email": "...", "password": "..." }
```

→ `200` `{ access_token, user, expires_in }` + cookie refresh.
→ `401` `{ "detail": "invalid credentials" }`
→ `429` con headers `X-RateLimit-*`

### `POST /auth/refresh`

Cookie obbligatorio. Body vuoto. Rate-limit `30/min` per IP.

→ `200` `{ access_token, expires_in }` + nuovo cookie refresh (rotation).
→ `401` se token scaduto / revocato / replay detected (revoca famiglia).

### `POST /auth/logout`

Header `Authorization` + cookie. Revoca **solo** il refresh corrente.

→ `204` + cookie cleared.

### `POST /auth/logout-all`

Revoca tutti i refresh dell'utente (forza re-login su ogni device).

### `GET /auth/me`

→ `200` `{ id, email, display_name, tenant_id, roles: [...], perms: [...], is_active, password_must_change }`.

### `POST /auth/password`

```json
{ "old_password": "...", "new_password": "..." }
```

→ `204`. Effetto: revoca tutti i refresh **eccetto il corrente** e rimuove flag `password_must_change`.

---

## 9. Conversations

Tutti richiedono auth + permesso `conversation.read`. RLS isolata per `user_id`.

### `GET /api/conversations?limit=20&offset=0`

→ `200` `{ items: [{ id, title, created_at, updated_at, message_count }], total }`

### `POST /api/conversations`

```json
{ "title": "Domande su decreto X" }
```

→ `201` `{ id, title, created_at }`

### `GET /api/conversations/{id}` / `PATCH` (title) / `DELETE` (cascade messages)

### `GET /api/conversations/{id}/messages?limit=100`

→ `200` `{ items: [{ id, role: "user|assistant|system", content, created_at }] }`

### `POST /api/conversations/{id}/messages`

Solo admin (manuale). Body `{ role, content }`.

### `DELETE /api/conversations/{id}/messages/{message_id}`

---

## 10. Memories (pgvector)

Auth + `memory.*`. RLS isolata per utente.

### `GET /api/memories?limit=50`

→ `200` `{ items: [{ id, content, created_at }], total }`

### `POST /api/memories`

```json
{ "content": "Lavoro nel reparto compliance, focus 2024." }
```

Embedding calcolato in background (BGE-M3, 1024 dim). → `201` `{ id, content, created_at }`.

### `GET /api/memories/{id}` / `DELETE /api/memories/{id}`

### `POST /api/memories/search`

```json
{ "query": "preferenze utente", "limit": 5, "min_similarity": 0.6 }
```

→ `200` `{ items: [{ id, content, similarity }] }`. Cosine sim, RLS-bound.

---

## 11. Ingest (PDF pipeline)

Auth + `ingest.run` (eccetto endpoint pubblici di sola lettura). Rate-limit `30/min`.

### `POST /api/ingest/file`

`multipart/form-data` con field `file`.

→ `202` `{ job_id, file_path, status: "pending" }`

### `GET /api/raw/files`

Lista file in `<vault>/raw/`. → `[{ name, size, modified_at, has_source_page }]`

### `POST /api/ingest/raw`

Upload PDF in `raw/` senza schedulare ingest. → `201` `{ path }`.

### `GET /api/ingest/raw/pending`

PDF in `raw/` senza pagina source corrispondente. → `[{ name, path }]`.

### `POST /api/ingest/raw/from-disk`

```json
{ "path": "<vault>/raw/file.pdf" }
```

Schedula ingest senza upload. → `202` `{ job_id }`.

### `GET /api/ingest/raw/jobs?status=running|done|failed`

→ `[{ job_id, file, status, stage, progress, started_at, ended_at, error? }]`

### `GET /api/ingest/raw/jobs/{job_id}`

Snapshot dettagliato.

### `GET /api/ingest/raw/jobs/{job_id}/stream` (SSE)

Eventi:

```text
event: stage
data: {"stage":"classify","progress":0.3}

event: log
data: {"level":"info","message":"page_type=concept"}

event: done
data: {"output":"wiki/concepts/garanzia-foo.md"}
```

---

## 12. Feedback

### `POST /api/feedback`

```json
{ "message_id": "...", "conversation_id": "...", "direction": "+", "note": "..." }
```

`direction ∈ ['+','-']`. → `201`.

### `GET /api/feedback?from=...&to=...`

Auth + `feedback.read`. → aggregato `{ total, positive, negative, by_message: [...] }`.

---

## 13. RBAC admin

Tutti richiedono `admin.user.manage` o ruolo `superuser`/`admin`. Audit log obbligatorio.

### `GET /api/admin/rbac/permissions`

→ `[{ slug, description }]` (catalog completo).

### `GET /api/admin/rbac/roles` / `GET /api/admin/rbac/roles/{id}`

→ ruoli globali + tenant-scoped, con permessi inclusi.

### `GET /api/admin/rbac/users`

→ `[{ id, email, display_name, roles: [...], domains: [...] }]`.

### `POST /api/admin/rbac/users/{user_id}/roles`

```json
{ "role_id": "..." }
```

Hierarchy-aware: rifiuta promozione self e laterale. → `204`. Audit `rbac.role.assign`.

### `DELETE /api/admin/rbac/users/{user_id}/roles/{role_id}`

→ `204`. Audit `rbac.role.revoke`.

### `POST /api/admin/rbac/users/{user_id}/domains` / `DELETE .../domains/{slug}`

Multi-wiki grant (mig 008). Body `{ domain_slug, role_id }`.

---

## 14. System / Health / Metrics

### `GET /api/status`

Pubblico. Pack, provider, qdrant, embedder, setup_mode, telemetry counters. Admin vede campi extra (paths, urls).

### `GET /health`

Liveness — sempre `200` se processo vivo.

### `GET /healthz`

Readiness Kubernetes-style: 200 solo se pack + DB + Qdrant ok. Altrimenti `503` con dettaglio.

### `GET /readiness`

Verboso JSON per dipendenza:

```json
{
  "status": "ready",
  "checks": {
    "database": {"ok": true, "latency_ms": 4},
    "qdrant": {"ok": true, "collections": 1},
    "llm": {"ok": true, "vendor": "ollama"},
    "pack": {"ok": true, "name": "legal"}
  }
}
```

### `GET /metrics`

Solo se `PROMETHEUS_METRICS_ENABLED=true`. Formato Prometheus text. Catalogo metriche → [`observability.md`](observability.md).

---

## 15. Admin (scaffold + runtime)

Loopback-only se `ADMIN_API_LOOPBACK_ONLY=true`. RBAC: `admin.scaffold` o `admin.runtime`.

### `GET /api/admin/scaffold/defaults`

Defaults per il wizard (page_type templates, vault root suggerito).

### `GET /api/admin/tenants` / `GET /api/admin/tenants/{name}`

Lista pack installati / dettaglio.

### `POST /api/admin/tenants/{name}/activate`

Scrive `APP_DOMAIN=<name>` + `WIKI_ROOT_<NAME>=...` in `.env`. Richiede restart per essere effettivo (single-tenant per processo).

### `POST /api/admin/scaffold/preview`

```json
{
  "name": "legal",
  "label": "Wiki Legale",
  "language": "it",
  "vault_root": "/srv/llm-wiki/vaults/legal",
  "provider": {"vendor": "ollama", "model": "llama3.1:8b"},
  "synthesize_prompts": true
}
```

→ `200` dry-run plan: file da creare, diff `.env`, validation result.

### `POST /api/admin/scaffold/apply`

Stesso body, esegue. → `200` `{ pack_name, vault_root, env_diff, synthesis: {...}, ingest_queued: [...] }`.

### `POST /api/admin/uploads/logo`

`multipart/form-data` field `file`. Salva in `domains/<pack>/logo.png`.

### `POST /api/admin/runtime/restart`

Auth + `admin.runtime`. SIGHUP graceful ai worker uvicorn.

---

## 16. Errori standard

| Status | Body | Quando |
| ------ | ---- | ------ |
| 400 | `{detail: "validation error", errors: [...]}` | Pydantic validation |
| 401 | `{detail: "not authenticated"}` | Token mancante/scaduto |
| 403 | `{detail: "missing permission: <slug>"}` | RBAC fail |
| 404 | `{detail: "not found"}` | Risorsa inesistente / RLS-isolated |
| 409 | `{detail: "conflict"}` | Es. email duplicata |
| 422 | `{detail: [{loc, msg, type}]}` | Pydantic structural |
| 429 | `{detail: "rate limit exceeded"}` + `X-RateLimit-*` | Rate-limit |
| 500 | `{detail: "internal error", request_id}` | Bug app |
| 503 | `{detail: "service unavailable"}` | Healthz fail (DB/Qdrant down) |

Tutti gli errori includono header `X-Request-ID` per correlazione log/trace.
