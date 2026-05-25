# Module: tenant context + middleware

Propaga `tenant_id` async-safe per request via `ContextVar`. MVP single-tenant (`default`).

## Files

| File | Responsabilità |
|------|----------------|
| [core/tenant.py](../../docheck-engine/src/docheck/core/tenant.py) | `current_tenant()`, `set_tenant`, resolution priority |
| [api/middleware.py](../../docheck-engine/src/docheck/api/middleware.py) | `TenantMiddleware`, `RequestIdMiddleware`, `SecurityHeadersMiddleware` |

## Resolution priority

1. JWT claim `tid` (quando OIDC enabled)
2. Header `X-Tenant-Id`
3. `default`

Multi-tenant disattivato → sempre `default`.

## Usage downstream

- [`vectorstores/chroma.py`](../../docheck-engine/src/docheck/services/vectorstores/chroma.py) e [`qdrant.py`](../../docheck-engine/src/docheck/services/vectorstores/qdrant.py) prefissano collection `{tenant}__{name}`.
- Future: row-level security policies Postgres su `tenant_id` colonna.
- Audit log: `tenant_id` aggiunto a payload (TODO F5).

## Security headers (production)

`SecurityHeadersMiddleware` aggiunge:

- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `Referrer-Policy: no-referrer`
- `Permissions-Policy: geolocation=(), camera=(), microphone=()`

## Limiti MVP

- Tenant isolation = collection prefix only (no row-level enforcement).
- No quota / rate limit per tenant.
- Cross-tenant leak prevention dipende solo da `current_tenant()` correttamente settato.
- Test integration F5: tenant A non legge dati tenant B (security gate).
