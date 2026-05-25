# API Reference (v1)

HTTP/WS API completa engine. Base path: `/api/v1`. Trasporto: Unix socket (default) o TCP loopback (`DOCHECK_BIND_TCP`).

Schemi entità: [reference/schemas.md](../reference/schemas.md). Auth + RBAC: [explanation/security-model.md](../explanation/security-model.md).

## Auth

### `POST /auth/login`

Login con credenziali locali. Public (no auth required).

**Request**

```json
{ "email": "admin@local", "password": "<plaintext>" }
```

**Response 200**

```json
{
  "user_id": "u-abc",
  "email": "admin@local",
  "roles": ["admin"],
  "token": "<jwt-eddsa>"
}
```

**Errors**: `401` credenziali invalide, `403` utente disabled.

### `GET /auth/me`

Restituisce principal corrente. Auth: Bearer JWT.

### `POST /auth/change-password`

Cambia password utente corrente.

**Request**: `{ "old_password": "...", "new_password": "..." }`. **Response 204**.

## Health & info

### `GET /health` (public)

```json
{
  "status": "ok",
  "version": "0.1.0",
  "llm_provider": "vllm",
  "llm_model": "llama-3.3-70b-instruct-q4_k_m",
  "llm_base_url": "http://vllm:8000/v1"
}
```

### `GET /info/pubkey` (public)

Public verifying key Ed25519 per validare report e audit chain.

```json
{ "algorithm": "ed25519", "public_key": "<hex>" }
```

## Documents

| Endpoint | Permission | Note |
|----------|-----------|------|
| `GET /documents` | `document:read` | Lista paginata. Query `limit`, `offset`, `q`, `status`. Header `X-Total-Count`. |
| `GET /documents/{id}` | `document:read` | Dettaglio + latest report. |
| `GET /documents/{id}/download` | `document:read` | File originale. |
| `GET /documents/{id}/reports` | `document:read` | Tutti i report dell'doc. |
| `GET /documents/{id}/chunks` | `document:read` | Chunks parsed (testo + bbox). |
| `POST /documents` | `document:write` | Upload `multipart/form-data` field `file`. Max 50MB. |
| `POST /documents/{id}/analyze` | `document:read` | Lancia analisi. Body opzionale `{"policies": [...], "lang": "it"}`. |
| `DELETE /documents/{id}` | `document:write` | Elimina doc + report. Audit `delete`. |

### Upload errors

- `413` file > 50MB.
- `415` mime non supportato. Body: `{"code": "unsupported_mime", "mime_type": "..."}`.

### Analyze errors

- `404` document not found.
- `415` `unsupported_mime`.
- `422` `parsing_failed` (parser exception) o `empty_document` (0 chunks).
- `422` `no_active_policies` (nessuna policy attiva nel tenant).
- `500` `graph_failed` (pipeline LangGraph errore non recuperato).

### Analyze response

Vedi [reference/schemas.md#report](../reference/schemas.md#report) per schema completo.

## WebSocket pipeline

### `WS /ws/analysis/{doc_id}`

Streaming eventi pipeline. Auth: TODO MVP (nessun enforce per ora).

**Eventi**

```ts
type WSEvent =
  | { type: "phase",    phase: "subscribed" | "started" | "classifier" | "structurer" | "legal" | "technical" | "pii" | "synthesizer" | "done" | "error", error?: string }
  | { type: "progress", current: number, total: number, label?: string }
  | { type: "finding",  finding: Finding }
  | { type: "trace",    step: ReasoningStep }
  | { type: "report",   report_id: string }
```

Il client deve chiudere WS quando riceve `phase: "done"`.

## Reports

| Endpoint | Permission | Note |
|----------|-----------|------|
| `GET /reports/{report_id}` | `report:read` | Report firmato + findings completi. |
| `GET /reports/{report_id}/findings/{finding_id}/decision` | `report:read` | Lettura decision corrente. |
| `POST /reports/{report_id}/findings/{finding_id}/decision` | `report:write` | Override umano. Body: `{"decision": "accept"|"reject"|"defer", "rationale": "..."}`. |
| `GET /reports/{report_id}/decisions` | `report:read` | Tutte le decisions del report. |
| `POST /reports/{report_id}/findings/{finding_id}/ask` | `report:read` | Q&A in linguaggio naturale su un finding (RAG). |
| `POST /reports/{report_id}/findings/{finding_id}/ask/stream` | `report:read` | Streaming SSE per Q&A. |
| `POST /reports/{report_id}/summary` | `report:read` | Genera summary IT/EN del report. Body: `{"locale": "it"}`. |
| `GET /reports/{doc_id}/export.md` | `report:read` | Export Markdown. |
| `GET /reports/{doc_id}/export.json` | `report:read` | Export JSON firmato. |

## Policies

| Endpoint | Permission | Note |
|----------|-----------|------|
| `GET /policies` | `policy:read` | Lista. Built-in `DocCheck_Builtin` sempre presente. |
| `GET /policies/{id}/rules?version=...` | `policy:read` | Regole di una specifica versione. |
| `GET /policies/{id}/{version}/export.yaml` | `policy:read` | Export YAML portable. |
| `POST /policies` | `policy:write` | Crea policy. Body schema: vedi [tutorial 02](../tutorials/02-author-policy.md). |
| `PATCH /policies/{id}/{version}` | `policy:write` | Update metadata. Built-in: `403`. |
| `POST /policies/{id}/{version}/active` | `policy:write` | Toggle active. |
| `POST /policies/{id}/{version}/clone` | `policy:write` | Clone in nuova version. |
| `DELETE /policies/{id}/{version}` | `policy:write` | Soft delete. Built-in: `403`. |
| `POST /policies/{id}/{version}/rules` | `policy:write` | Aggiungi rule. |
| `PATCH /policies/{id}/{version}/rules/{rule_id}` | `policy:write` | Update rule. |
| `DELETE /policies/{id}/{version}/rules/{rule_id}` | `policy:write` | Delete rule. |
| `POST /policies/import` | `policy:write` | Import YAML (multipart `file`). |
| `POST /policies/ingest/url` | `policy:write` | Ingest da URL (LLM-assisted rule extraction). |
| `POST /policies/ingest/document` | `policy:write` | Ingest da documento già caricato. |

## Audit

| Endpoint | Permission | Note |
|----------|-----------|------|
| `GET /audit/log?limit=&offset=&action=&user_id=` | `audit:read` | Lista paginata + filter. |
| `GET /audit/{seq}` | `audit:read` | Dettaglio entry singolo + payload. |
| `GET /audit/actions` | `audit:read` | Lista azioni distinte (per filter UI). |
| `GET /audit/users` | `audit:read` | Lista user_id distinti. |
| `GET /audit/verify` | `audit:read` | Ricalcola integrity chain del tenant. Response: `{ok, broken_seq, total_entries}`. |
| `GET /audit/export.csv` | `audit:read` | Export CSV. |
| `GET /audit/export.json` | `audit:read` | Export JSON. |

## System

| Endpoint | Permission | Note |
|----------|-----------|------|
| `GET /system/runtime` | `admin:read` | Versione, model_id, embedding model, tenant. |
| `GET /system/storage` | `admin:read` | Spazio disco docs/, chroma/, db. |
| `POST /system/llm/probe` | `admin:read` | Ping LLM endpoint, ritorna latency + model loaded. |
| `GET /system/cache` | `admin:read` | Hit-ratio embedding/policy/verdict cache. |
| `POST /system/cache/reset` | `admin:write` | Invalida cache. |
| `GET /system/retention` | `admin:read` | Settings TTL. |
| `PUT /system/retention` | `admin:write` | Update TTL. |

## Workspace

| Endpoint | Permission | Note |
|----------|-----------|------|
| `GET /workspace/queue` | `document:read` | Doc in stato `uploaded`/`parsed` ready per analisi. |
| `GET /workspace/active-policies` | `policy:read` | Policy attive del tenant + count rules. |
| `GET /workspace/recent-activity` | `document:read` | Mix audit + report recenti per home dashboard. |

## Metrics

| Endpoint | Permission | Note |
|----------|-----------|------|
| `GET /metrics/cache` | `admin:read` | Equivalente a `/system/cache`. Backwards-compat. |

## RBAC summary

Tutti gli endpoint (eccetto `/auth/login`, `/health`, `/info/pubkey`) richiedono:

- **Bearer JWT** in `Authorization: Bearer <token>` (priority), o
- **`X-User-Id`** header (legacy MVP fallback, da rimuovere pre-GA).

Permission matrix:

| Resource | Actions | Ruoli con accesso |
|----------|---------|-------------------|
| `document` | `read`, `write` | `admin`, `compliance_officer` (write); `+reader` (read) |
| `policy` | `read`, `write` | `admin`, `compliance_officer` (write); `+all` (read) |
| `report` | `read`, `write` | `admin`, `compliance_officer` (write); `+dpo`, `+reader` (read) |
| `audit` | `read` | `admin`, `dpo` |
| `admin` | `read`, `write` | `admin` |

Mismatch → `403 Forbidden`.

## Headers

### Request

- `Authorization: Bearer <jwt>` — auth.
- `X-Tenant-Id: <tenant>` — override tenant (multi-tenant; JWT `tid` claim ha priorità).
- `X-Request-Id: <uuid>` — correlation; engine genera se assente.

### Response

- `X-Request-Id` — echo per correlation.
- `X-Tenant-Id` — tenant del response (debug).
- `X-Total-Count` — su lista paginate.
- `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Permissions-Policy: ...` (security middleware).

## Error envelope

Errori applicativi usano envelope uniforme:

```json
{
  "code": "unsupported_mime",
  "message": "Mime type 'application/foo' not supported",
  "mime_type": "application/foo"
}
```

`code` machine-readable; `message` human-readable. Campi extra context-specific.

## OpenAPI

FastAPI espone schema auto-generato:

- `GET /api/v1/openapi.json`
- `GET /api/v1/docs` (Swagger UI, dev only se `DOCHECK_DEBUG=true`)

## Vedi anche

- [reference/schemas.md](../reference/schemas.md) — JSON contract.
- [reference/config.md](../reference/config.md) — env vars.
- [explanation/security-model.md](../explanation/security-model.md) — RBAC, audit, JWT.
- [tutorials/01-first-analysis.md](../tutorials/01-first-analysis.md) — esempio uso.
