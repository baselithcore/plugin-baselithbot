# Security Model

Discussione concettuale del modello di sicurezza doCheck. Per disclosure responsabile e versioni supportate: [SECURITY.md](../../SECURITY.md).

## Principi

1. **Local-first, zero egress**: dati sensibili dei clienti non lasciano mai il perimetro on-prem.
2. **Defense in depth**: nessun singolo controllo è autosufficiente.
3. **Non-ripudio**: ogni operazione critica è loggata in catena hash firmata.
4. **Least privilege**: RBAC granulare `(resource, action)`; ruoli minimi richiesti per ogni operazione.
5. **Audit-grade trasparenza**: ogni verdetto del sistema è glass-box ([glass-box.md](glass-box.md)).

## Threat model sintetico

| Attaccante | Capacità | Mitigazione |
|------------|----------|-------------|
| Insider `reader` | Login valido, ruolo minimo | RBAC enforcement; tentativi cross-resource loggati |
| Insider privilegiato (`compliance_officer`, `dpo`) | Read audit, write policy | Audit chain integrity rilevatore tampering |
| Network attacker on-prem | Sniff traffico LAN | Trasporto Unix socket default; CSP Electron strict |
| Internet attacker | Nessuna connessione attesa | Egress lockdown CI gate; nessuna API esterna |
| Operatore host root | Filesystem access | SQLCipher at-rest + master key in OS keychain (mitigazione parziale) |
| Tenant cross-leak (multi-tenant) | Login tenant A, prova accedere tenant B | tenant_id colonna + Postgres RLS + vector collection prefix |

Threat actor escluso: stato-nazione con accesso fisico al nodo (out-of-scope MVP).

## Strato 1 — Network

### Trasporto

Default: **Unix domain socket** `storage/docheck.sock`. Niente porta TCP esposta. UI Electron parla via IPC fetch wrapper o socket diretto.

Dev opt-in: `DOCHECK_BIND_TCP=127.0.0.1:8765` per sviluppare con browser. **Mai** TCP non-loopback in produzione.

### Egress

- LLM: vLLM o Ollama on-prem. URL config-flag, validato in CI.
- Embedding: BGE-M3 caricato in-process (no API calls).
- OCR: PaddleOCR/Tesseract local binary.
- Vector DB: Chroma (persist disco) o Qdrant (container interno).

**Egress lockdown gate** in CI:

```bash
# Test E2E in container con tcpdump
tcpdump -i eth0 -n 'not (dst net 127.0.0.0/8 or dst net 10.0.0.0/8)' &
pytest tests/ -k e2e
# Fail PR se ≥ 1 pacchetto in uscita verso non-loopback/internal
```

Helm chart: `NetworkPolicy` deny-egress default. Solo `vllm`, `qdrant`, `postgres` interni allow-listed.

## Strato 2 — Autenticazione

### Login

`POST /api/v1/auth/login` → `{email, password}` → verifica argon2id (`passlib`) → emette **JWT EdDSA** (Ed25519, [`core/jwt.py`](../../docheck-engine/src/docheck/core/jwt.py)).

Claims:

- `sub` — user_id
- `email`
- `roles` — frozenset
- `tid` — tenant_id (default `"default"`)
- `iat`, `exp` — issued/expiry standard

### Verifica

Ogni request privata richiede `Authorization: Bearer <jwt>`. Engine:

1. Verifica firma con public key Ed25519.
2. Verifica `exp`.
3. Setta `current_tenant(claims["tid"])`.
4. Ritorna `Principal(user_id, email, roles)`.

Fallback legacy `X-User-Id` header per MVP / smoke test, **da rimuovere pre-GA**.

### OIDC (post-MVP)

Stub pronto. Attivato impostando `DOCHECK_OIDC_ISSUER`. Validazione JWKS via `oidc.py`. Multi-tenant: claim `tid` da Keycloak realm.

## Strato 3 — Autorizzazione (RBAC)

Modello: `(resource, action)` permission. Ruolo = set di permission.

| Ruolo | Permission tipiche |
|-------|--------------------|
| `admin` | tutto |
| `compliance_officer` | `policy:*`, `document:*`, `report:*` |
| `dpo` | `audit:read`, `report:read`, `document:read` |
| `reader` | `document:read`, `report:read` |

Enforcement: dependency `require(resource, action)` ([api/deps.py](../../docheck-engine/src/docheck/api/deps.py)).

```python
@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    principal: Principal = Depends(require("document", "write")),
    ...
): ...
```

Permission matrix completa: [docs/api/endpoints.md](../api/endpoints.md#rbac).

## Strato 4 — Audit log

Append-only, hash-chained, firmato Ed25519. Per-tenant chain.

### Schema record

```
seq | ts | tenant_id | user_id | action | resource | payload_hash | prev_hash | entry_hash | signature
```

### Hash chain

```
entry_hash = SHA256(prev_hash || canonical_json({tenant_id, user_id, action, resource, payload_hash}))
signature  = Ed25519_sign(entry_hash, master_key)
```

Per-tenant: `prev_hash` lookup filtra per `tenant_id`. Tampering record di tenant A non rompe chain di tenant B.

### Immutabilità

- SQLite: trigger `BEFORE UPDATE/DELETE ON audit_log → RAISE FAIL`.
- Postgres: `CREATE RULE` deny + revoke `UPDATE/DELETE` su tabella + RLS policy.

Tentare un `UPDATE` solleva eccezione → operazione respinta a livello DB, non solo applicativo.

### Verifica

`GET /api/v1/audit/verify` ricalcola chain completo, ritorna `{ok: bool, broken_seq: int | null, total_entries: int}`. Job giornaliero schedulato.

Vedi [ADR-0002 — SQLCipher audit hash chain](../adr/0002-sqlcipher-audit-hash-chain.md).

### Master key custody

File: `storage/audit_ed25519.key` mode 0600, generata al primo avvio.

Production target: OS keychain (macOS Keychain / Windows DPAPI / Linux `secret-service` via `keyring`). Procedura migration: [docs/runbooks/rotate-keys.md](../runbooks/rotate-keys.md).

## Strato 5 — Encryption at rest

### SQLCipher (single-tenant)

Attivata via `DOCHECK_DB_ENCRYPTION_ENABLED=true`. Parametri:

- `cipher_page_size=4096`
- `kdf_iter=256000`
- `cipher_hmac_algorithm=HMAC_SHA512`

Master DB key in keyring (`DOCHECK_DB_KEY_KEYRING_SERVICE`, `_USER`).

### Postgres (multi-tenant)

Encryption at-rest via:

- LUKS/dm-crypt sul volume.
- Postgres `pgcrypto` per colonne sensibili specifiche.
- Backup cifrati (pg_basebackup + age/gpg).

Vedi [ADR-0008 — Encryption-at-rest strategy](../adr/0008-encryption-at-rest-strategy.md).

### Documenti sorgente

Su volume cifrato a livello FS (LUKS / FileVault / BitLocker host). Path `storage/docs/<sha256>` riferito da `documents.storage_uri`.

Auto-purge configurabile via `purge_at` colonna (TTL retention, `DOCHECK_RETENTION_DEFAULT_DAYS`).

## Strato 6 — Frontend

### Electron

- `nodeIntegration: false`, `contextIsolation: true`, `sandbox: true`.
- Preload narrow API surface (no `require`, no `process`, no `fs`).
- CSP: `default-src 'self'; connect-src 'self' ws://unix-socket; script-src 'self'`.
- Notarization macOS, code-signing Windows (pre-GA).

### CSRF / origin

Engine CORS allow-list: `app://docheck`, `vscode-webview://*`, `tauri://*`, `file://`, `localhost:3000/3100` (dev). Bearer JWT richiesto su mutating endpoints.

### Headers

`SecurityHeadersMiddleware`:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`
- `Permissions-Policy: geolocation=(), camera=(), microphone=()`

## Strato 7 — Multi-tenant isolation

Vedi [multitenant.md](multitenant.md) per dettagli.

Sintesi:

- `tenant_id` colonna su tutte le tabelle dati (`TenantMixin`).
- ContextVar per propagazione async-safe.
- Postgres RLS policies attive (Alembic 0003).
- Vector collection prefix `{tenant_id}__{name}`.
- Audit chain per-tenant.

Test integration security gate: tenant A non legge dati tenant B.

## Strato 8 — Glass-box come controllo

Vedi [glass-box.md](glass-box.md). Sintesi: ogni finding tracciabile + report firmati Ed25519 = compliance audit-grade. Non è solo UX, è controllo di integrità sull'output del LLM.

## Pen-test

Obbligatorio prima di ogni release GA. Scope minimo:

- Egress lockdown.
- CSP Electron.
- Audit tampering.
- RBAC bypass.
- JWT replay/forge.
- Multi-tenant cross-leak.
- SQLi su query dinamiche (poche, ma controllare RLS bypass).
- Path traversal su upload/download.

## Vedi anche

- [SECURITY.md](../../SECURITY.md) — disclosure policy + threat model esecutivo.
- [glass-box.md](glass-box.md) — pillar trasparenza output.
- [multitenant.md](multitenant.md) — isolation strategy.
- ADR rilevanti: [0002](../adr/0002-sqlcipher-audit-hash-chain.md), [0006](../adr/0006-postgres-rls-multitenant.md), [0008](../adr/0008-encryption-at-rest-strategy.md).
