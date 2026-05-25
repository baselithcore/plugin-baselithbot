# ADR-0006: Postgres Row-Level Security per Multi-Tenant

**Status:** Accepted (gated F5+)
**Date:** 2026-05-03

## Context

Multi-tenant deploy richiede isolamento dati. Filtering applicativo via `WHERE tenant_id = ...` è fragile: bug in una sola query di lettura → cross-tenant leak. Compliance-grade serve enforcement DB-level.

## Decision

Attivare **Row-Level Security** Postgres su tabelle scope-tenant:

- `users`, `documents`, `policies`, `reports`, `audit_log` con colonna `tenant_id` (vedi [migration 0002](../../docheck-engine/alembic/versions/0002_tenant_id_columns.py)).
- Policy `tenant_isolation_<table>` con `USING (tenant_id = current_setting('app.current_tenant'))` + `WITH CHECK` per insert (vedi [migration 0003](../../docheck-engine/alembic/versions/0003_postgres_rls.py)).
- `FORCE ROW LEVEL SECURITY` → applica policy anche a table owner (no bypass).
- Session GUC `app.current_tenant` settata da [`db/rls.py`](../../docheck-engine/src/docheck/db/rls.py) via SQLAlchemy `checkout` event listener: ogni connection riceve tenant corrente da `current_tenant()` ContextVar.

## Consequences

**Positive**
- Cross-tenant leak prevented at DB level — impossibile bypassare via dimenticanza WHERE.
- SQLite no-op → MVP single-tenant non impattato.
- Audit-compliance ready (SOC2 trust criteria CC6).

**Negative**
- Connection pool: ogni checkout richiede SET — overhead trascurabile (~µs).
- Postgres-specific → test multi-tenant richiedono Postgres real (no sqlite mock).
- Migration manuale per cliente esistente con dati legacy (`UPDATE ... SET tenant_id`).

## Mitigazioni

- Test integration F5 con docker-compose Postgres dedicato.
- CI matrix: SQLite + Postgres backend.
- Backfill script per migrazione dati legacy.

## Alternatives Considered

- **Schema-per-tenant**: troppo overhead operativo (DDL per onboard), no scaling oltre ~50 tenant.
- **Database-per-tenant**: maggior isolamento ma costo infra alto, no analytics cross-tenant.
- **Solo filtering applicativo**: rischio leak inaccettabile per certificazione.
