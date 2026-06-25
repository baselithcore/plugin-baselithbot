# Tenant isolation: application filtering + optional Postgres RLS

BaselithCore enforces multi-tenancy in **two layers**. Layer 1 is always on;
Layer 2 is opt-in defense-in-depth.

## Layer 1 — application-level tenant filtering (always on)

Tenancy is **identity-derived**: the access token carries a `tenant_id` claim
(`plugins/auth/tenancy.py:resolve_user_tenant`) bound to a context var
(`core.context.get_current_tenant_id`). Stores scope every read/write to it,
e.g. `core/storage/postgres.py` (`interactions`, `feedback`),
`plugins/baselithoptimizeprocess`, `plugins/baselith_pitwall`. A user with no
tenant membership falls back to a personal tenant (`tenant_id == user_id`), so
existing single-tenant installs are unchanged.

This layer works regardless of the database role.

### Per-plugin tenancy mode (`shared` vs `personal`)

A session resolves to **one** `tenant_id` (pinned `AUTH_TENANT_ID` → org
membership → personal). That single value is what every plugin sees by default.
A plugin can, however, choose its **tenancy model** independently of how the
deployment resolves tenancy, declared once in its manifest:

```yaml
# plugins/<name>/manifest.yaml
tenancy: personal   # default: "shared"
```

- **`shared`** (default) — scope data by the deployment-derived tenant
  (`core.context.get_current_tenant_id()`): pinned, org-shared, or personal,
  whatever the deploy resolves. Use for org/collaborative data.
- **`personal`** — force **1 user = 1 tenant** *regardless* of the deployment
  tenant, so a per-user surface (notes, chat history, personal vault) stays
  isolated even on a shared/org deployment. Use for private per-user data.

The plugin's store resolves its scope key with `self.tenant_key()`
(= `core.context.resolve_plugin_tenant(self.metadata.tenancy)`) **instead of**
calling `get_current_tenant_id()` directly. This stays *identity-derived*: the
per-user key comes from the user context var (`core.context.get_current_user_id`),
bound at the same chokepoints as the tenant — the security & tenant middleware,
the auth `_bind_tenant` guard, the task-queue worker, and the event bus — never
from a client header. It degrades safely to the session/default tenant when no
user is bound (background tasks, scripts).

`PluginMetadata.tenancy` is surfaced **read-only** in the BaselithControl plugin
inventory (a "Shared"/"Personal" badge), so an operator can see each plugin's
isolation model at a glance.

> **It is a manifest-declared, not an admin-toggled, setting.** Unlike the
> central per-tab access policy (pure visibility, freely reversible), the tenancy
> mode is the *storage scope key*. Flipping `shared`↔`personal` after a plugin
> has written data changes which `tenant_id` rows are read/written, **orphaning**
> the existing rows (they are hidden, not deleted). Treat a mode change as a data
> migration: backfill the new key, or only set it before the plugin stores data.

## Layer 2 — Postgres Row-Level Security (opt-in, defense-in-depth)

RLS makes the **database** reject cross-tenant rows even if an application
`WHERE tenant_id = …` is ever forgotten. It is **off by default** and requires
three things together; enabling fewer than all three is either a no-op or an
outage:

1. **`DB_RLS_ENABLED=true`** — the connection pool then sets the
   `app.tenant_id` GUC to the request's tenant on every checkout
   (`core/db/connection.py:_sync_apply_tenant` / `_async_apply_tenant`). Outside
   a request it degrades to `"default"`, so background tasks never break.
2. **A non-superuser application role.** Postgres **bypasses RLS for
   superusers and the table owner** (unless `FORCE ROW LEVEL SECURITY`). The
   default `baselithcore` role is a superuser, so RLS has *no effect* until the
   app connects as a least-privilege, non-superuser role.
3. **Per-table policies** keyed on the GUC (below).

### Policy recipe (run once, as the table owner)

```sql
-- Least-privilege app role the backend connects as (DB_USER/DB_PASSWORD).
CREATE ROLE app_runtime LOGIN PASSWORD '…' NOSUPERUSER NOBYPASSRLS;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_runtime;
GRANT USAGE ON ALL SEQUENCES IN SCHEMA public TO app_runtime;

-- One policy per tenant-scoped DATA table. Do NOT apply to admin/membership
-- tables (auth_tenants, auth_user_tenants): those are managed across tenants by
-- platform/tenant admins and must not be filtered by the requester's tenant.
ALTER TABLE interactions ENABLE ROW LEVEL SECURITY;
CREATE POLICY interactions_tenant ON interactions
  USING       (tenant_id = current_setting('app.tenant_id', true))
  WITH CHECK  (tenant_id = current_setting('app.tenant_id', true));

ALTER TABLE feedback ENABLE ROW LEVEL SECURITY;
CREATE POLICY feedback_tenant ON feedback
  USING       (tenant_id = current_setting('app.tenant_id', true))
  WITH CHECK  (tenant_id = current_setting('app.tenant_id', true));
```

`plugins/red_agent` already ships this pattern in its migrations
(`red_agent_current_tenant()` + per-table policies) and is the reference.

### Verified behaviour

With a non-superuser role and the GUC set, isolation holds: tenant A sees only
A's rows, B only B's, and an unset GUC matches **no** rows (fail-closed). The
GUC is set per request by the pool hook, validated against a live database.

### Caveat

A non-superuser role + RLS-enabled tables + `DB_RLS_ENABLED=false` (GUC never
set) makes every policy match nothing → effective outage. Always flip
`DB_RLS_ENABLED` and the role together.
