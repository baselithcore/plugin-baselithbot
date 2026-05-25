# 1. Architettura Core

Sistema layered, modulare, deployabile come monorepo con due artefatti principali: `docheck-engine` (FastAPI Python) + `docheck-ui` (Electron + Next.js statico).

## 1.1 Diagramma Layered

```
┌─────────────────────────────────────────────────────────────┐
│  PRESENTATION LAYER (Electron + Next.js + shadcn/ui)        │
│  - Document Viewer · Findings Panel · Policy Manager        │
└──────────────────────────┬──────────────────────────────────┘
                           │ gRPC/WS local socket
┌──────────────────────────▼──────────────────────────────────┐
│  API GATEWAY (FastAPI)                                      │
│  - AuthN OIDC-ready · RBAC middleware · Rate limit          │
│  - Request validation (Pydantic) · Audit emitter            │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│  ORCHESTRATION LAYER (LangGraph StateMachine)               │
│  Parser → Structurer → [Legal | Tech | PII] → Synthesizer   │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────┬───────────────┼─────────────────┬────────────────┐
│ INGEST   │ INDEX         │ INFERENCE       │ PERSISTENCE    │
│ PaddleOCR│ ChromaDB      │ vLLM (DGX)      │ SQLite cifrato │
│ pdfplumb │ BGE-M3 multi  │ Llama-3.3-70B   │ (SQLCipher)    │
│ docx/xlsx│ embed (IT/EN) │ Q4_K_M          │ Audit Log      │
└──────────┴───────────────┴─────────────────┴────────────────┘
```

## 1.2 Componenti Produzione

### Identity & RBAC

- Ruoli: `admin`, `compliance_officer`, `dpo`, `reader`.
- Tabelle `users`, `roles`, `user_roles`, `permissions` (vedi `06_db_schema.sql`).
- Enforcement via decoratore Python `@require_role` su endpoint FastAPI.
- OIDC stub pronto per Keycloak (multi-tenant ready).
- Local auth MVP: argon2id password hash.

### Audit Trail (hash-chained, append-only)

- Tutti eventi rilevanti loggati: `login`, `upload`, `analyze`, `policy_create`, `policy_activate`, `view_finding`, `report_export`.
- Schema record: `seq, ts, user_id, action, resource, payload_hash, prev_hash, entry_hash, signature(Ed25519)`.
- Hash chain stile Merkle per non-ripudio.
- Trigger SQLite `BEFORE UPDATE/DELETE` → `RAISE FAIL` per immutabilità.
- Job giornaliero `verify_audit_chain()` ricalcola integrità end-to-end.
- Export report firmati Ed25519 (chiave privata in OS keychain).

### Caching (3 livelli)

1. **embedding_cache** — key `sha256(text) + model_id` → vector ref Chroma. LRU su disco.
2. **policy_index_cache** — Chroma persistente per policy indicizzate, invalidato su `policy.version` bump.
3. **verdict_cache** — key `sha256(chunk_hash || rule_id || rule_version || model_id)` → Finding JSON. Riutilizzabile fra documenti simili.

### Document Storage

- Volume cifrato a livello FS (LUKS / FileVault / BitLocker).
- File originali in `storage/docs/<sha256>` riferiti da `documents.storage_uri`.
- Metadati + offset mapping in SQLite.
- Auto-purge configurabile via `purge_at` (TTL retention).

### Observability

- OpenTelemetry locale, trace export su file (no exporter cloud).
- Dashboard Grafana opzionale via Docker compose (profilo `--profile observability`).
- Prometheus metrics endpoint solo su Unix socket.

### Packaging

- **Workstation MVP:** Electron installer firmato (notarized macOS, signed Windows). LLM scaricabile post-install via wizard.
- **Server DGX:** Docker Compose multi-container (`engine`, `vllm`, `chroma`, `ui-static`, `audit-db`). Helm chart pianificato per multi-tenant.
- **Air-gapped install:** mirror locale di pesi modelli e dipendenze Python (wheel cache).

## 1.3 Sicurezza & Network

- **Egress lockdown:** binding gRPC/WS solo su Unix socket, no TCP esposto. Validazione CI con `tcpdump` durante test E2E.
- **SQLCipher:** `cipher_page_size=4096`, `kdf_iter=256000`, `cipher_hmac_algorithm=HMAC_SHA512`.
- **Master key custody:** macOS Keychain / Windows DPAPI / Linux secret-service (`keyring` lib).
- **CSP Electron:** `default-src 'self'; connect-src 'self' ws://unix-socket; script-src 'self'`. Disabled `nodeIntegration` in renderer.
- **Pen-test interno** prima di GA (fase F4).
