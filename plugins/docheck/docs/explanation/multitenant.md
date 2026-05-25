# Multi-tenant Isolation

doCheck è single-tenant per default (workstation MVP) e abilita multi-tenant on-prem via flag (`DOCHECK_MULTITENANT_ENABLED=true` + Postgres + Qdrant). Questo documento spiega la strategia di isolation.

## Decisioni architetturali

- [ADR-0004 — Helm multitenant path](../adr/0004-helm-multitenant-path.md)
- [ADR-0005 — Vector store abstraction](../adr/0005-vector-store-abstraction.md)
- [ADR-0006 — Postgres RLS multitenant](../adr/0006-postgres-rls-multitenant.md)
- [ADR-0008 — Encryption at-rest strategy](../adr/0008-encryption-at-rest-strategy.md)

## Modello

Tenant = unità di isolation. Tipicamente: un cliente / una BU / un namespace logico.

Ogni risorsa dati ha colonna `tenant_id`. Il sistema **non** offre cross-tenant view (no super-admin che legge tutto in produzione; gestione amministrativa solo via accesso DB diretto o tooling dedicato fuori-banda).

## Resolution priority

`current_tenant()` ([core/tenant.py](../../docheck-engine/src/docheck/core/tenant.py)) async-safe via `ContextVar`. Resolution order in `TenantMiddleware` ([api/middleware.py](../../docheck-engine/src/docheck/api/middleware.py)):

1. JWT claim `tid` (production con OIDC abilitato).
2. Header `X-Tenant-Id` (legacy / dev).
3. Default: `"default"`.

Multi-tenant disattivato → sempre `"default"`.

## Layer 1 — DB

### TenantMixin

```python
class TenantMixin:
    tenant_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=lambda: current_tenant(),
        index=True,
    )
```

Applicato a tutti i modelli dati (`Document`, `DocumentChunk`, `Policy`, `Rule`, `Report`, `AuditLog`, `Decision`, ecc.).

### Postgres RLS

Migration Alembic 0003 abilita Row-Level Security:

```sql
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
CREATE POLICY tenant_isolation ON documents
  USING (tenant_id = current_setting('app.tenant_id'));
```

`install_rls_hook()` in [db/rls.py](../../docheck-engine/src/docheck/db/rls.py) setta GUC `app.tenant_id` per ogni session via `SET LOCAL app.tenant_id = '...'`.

Conseguenza: anche un `SELECT * FROM documents` senza `WHERE tenant_id = ...` ritorna solo righe del tenant corrente. Sicurezza by default.

### SQLite (single-tenant)

RLS non disponibile. Enforcement applicativo solo (filtro esplicito su `current_tenant()`). Per single-tenant MVP non è un problema (sempre `"default"`).

## Layer 2 — Vector store

Collection naming: `{tenant_id}__{name}`. Esempio:

- `default__policies` (single-tenant)
- `acme__policies`, `acme__verdict_cache` (tenant `acme`)

Implementato in [vectorstores/chroma.py](../../docheck-engine/src/docheck/services/vectorstores/chroma.py) e [vectorstores/qdrant.py](../../docheck-engine/src/docheck/services/vectorstores/qdrant.py).

Test [tests/test_vectorstore_isolation.py](../../docheck-engine/tests/test_vectorstore_isolation.py) verifica che query lato tenant A non veda chunks tenant B.

## Layer 3 — Audit chain

Chain hash include `tenant_id` in canonical JSON. `prev_hash` lookup filtra per `tenant_id == current_tenant()`.

Conseguenze:

- Chain di tenant A indipendente da chain di tenant B.
- Tampering record di un tenant non rompe integrity di altri tenant.
- `verify_chain()` opera per-tenant.

Test: [tests/test_audit_tenant_isolation.py](../../docheck-engine/tests/test_audit_tenant_isolation.py).

## Layer 4 — Cache

Verdict cache key include `tenant_id`:

```
cache_key = sha256(tenant_id || chunk_hash || rule_id || rule_version || model_id)
```

Embedding cache è cross-tenant safe (key = solo `sha256(text) + model_id`, contenuto è vector di testo, non sensibile lato compliance).

Policy index Chroma rispetta collection prefix.

## Layer 5 — Filesystem

Documenti sorgente in `storage/docs/<sha256>`. Single-tenant: shared. Multi-tenant: subdir per tenant `storage/docs/<tenant_id>/<sha256>` (TODO pre-GA F5).

## Limiti correnti

| Limite | Impatto | Risoluzione pianificata |
|--------|---------|------------------------|
| FS docs non per-tenant | Hash collision improbabile ma teorica condivisione | F5: subdir per tenant |
| No quota per tenant | Tenant pesante può saturare risorse | F5: rate limiting + quota colonne |
| No tenant onboarding flow UI | Onboarding via script CLI | F5: setup wizard admin |
| Backfill tenant_id storico | Non applicabile (multi-tenant è greenfield) | n/a |

## Test gate sicurezza

Pre-GA, test di integration obbligatori:

1. Tenant A login → upload doc → analyze.
2. Tenant B login → API query documents → 0 risultati.
3. Tenant B login → tentativo `GET /api/v1/documents/{a_doc_id}` → 404.
4. Tenant B login → vector retrieval → 0 chunk del tenant A.
5. Audit verify per tenant A: ok. Tampering tenant A → tenant B verify ancora ok.
6. JWT con `tid=A` → tentativo header override `X-Tenant-Id: B` → JWT prevale (tenant resolution priority).

## Tooling cross-tenant amministrativo

Per backup, migration, support:

- Accesso DB diretto con utente postgres `app_admin` che bypassa RLS (`BYPASSRLS`). Solo da bastion + audit OS.
- Mai esporre via API cross-tenant view.
- Audit log specifico per accesso admin.

## Vedi anche

- [security-model.md](security-model.md) — controlli sicurezza globali.
- [architecture.md](architecture.md) — vista layered con persistence target.
- [modules/tenant.md](../modules/tenant.md) — reference rapida modulo.
