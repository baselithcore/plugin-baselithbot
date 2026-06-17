"""DDL for the Postgres-backed :class:`ProcessStore`.

Each entity is stored as a JSONB ``data`` blob (lossless round-trip of the
Pydantic model, resilient to additive model evolution) plus the few scalar
columns needed for keying, filtering, and insertion-order reads. No foreign keys
are declared on purpose: :meth:`PostgresProcessStore.delete_process` performs the
cascade explicitly inside one transaction, mirroring the in-memory semantics
exactly (orphan rows are possible by the same rules as the in-memory backend).

All statements are idempotent (``IF NOT EXISTS``) so :meth:`initialize` can run
on every boot without an external migration step — matching the self-initializing
pattern used by :class:`core.storage.postgres.PostgresStorage`.
"""

from __future__ import annotations

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS bop_processes (
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    id          TEXT NOT NULL,
    data        JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, id)
);

CREATE TABLE IF NOT EXISTS bop_resources (
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    id          TEXT NOT NULL,
    data        JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, id)
);

CREATE TABLE IF NOT EXISTS bop_samples (
    seq         BIGSERIAL PRIMARY KEY,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    process_id  TEXT NOT NULL,
    kpi_id      TEXT NOT NULL,
    data        JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS bop_samples_series_idx
    ON bop_samples (tenant_id, process_id, kpi_id, seq DESC);

CREATE TABLE IF NOT EXISTS bop_proposals (
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    id          TEXT NOT NULL,
    process_id  TEXT NOT NULL,
    data        JSONB NOT NULL,
    PRIMARY KEY (tenant_id, id)
);
CREATE INDEX IF NOT EXISTS bop_proposals_process_idx
    ON bop_proposals (tenant_id, process_id);

CREATE TABLE IF NOT EXISTS bop_bottlenecks (
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    process_id  TEXT NOT NULL,
    data        JSONB NOT NULL,
    PRIMARY KEY (tenant_id, process_id)
);

CREATE TABLE IF NOT EXISTS bop_rules (
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    id          TEXT NOT NULL,
    process_id  TEXT NOT NULL,
    data        JSONB NOT NULL,
    PRIMARY KEY (tenant_id, id)
);
CREATE INDEX IF NOT EXISTS bop_rules_process_idx
    ON bop_rules (tenant_id, process_id);

CREATE TABLE IF NOT EXISTS bop_firings (
    seq         BIGSERIAL PRIMARY KEY,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    process_id  TEXT NOT NULL,
    data        JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS bop_firings_process_idx
    ON bop_firings (tenant_id, process_id, seq DESC);

CREATE TABLE IF NOT EXISTS bop_mining (
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    process_id  TEXT NOT NULL,
    data        JSONB NOT NULL,
    PRIMARY KEY (tenant_id, process_id)
);

CREATE TABLE IF NOT EXISTS bop_events (
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    process_id  TEXT NOT NULL,
    data        JSONB NOT NULL,
    PRIMARY KEY (tenant_id, process_id)
);

CREATE TABLE IF NOT EXISTS bop_slas (
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    id          TEXT NOT NULL,
    process_id  TEXT NOT NULL,
    data        JSONB NOT NULL,
    PRIMARY KEY (tenant_id, id)
);
CREATE INDEX IF NOT EXISTS bop_slas_process_idx
    ON bop_slas (tenant_id, process_id);

CREATE TABLE IF NOT EXISTS bop_versions (
    tenant_id     TEXT NOT NULL DEFAULT 'default',
    process_id    TEXT NOT NULL,
    version       INTEGER NOT NULL,
    content_hash  TEXT NOT NULL,
    data          JSONB NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, process_id, version)
);
CREATE INDEX IF NOT EXISTS bop_versions_proc_idx
    ON bop_versions (tenant_id, process_id, version DESC);

CREATE TABLE IF NOT EXISTS bop_audit (
    seq         BIGSERIAL PRIMARY KEY,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    process_id  TEXT NOT NULL DEFAULT '',
    data        JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS bop_audit_tenant_idx
    ON bop_audit (tenant_id, seq DESC);
CREATE INDEX IF NOT EXISTS bop_audit_proc_idx
    ON bop_audit (tenant_id, process_id, seq DESC);

CREATE TABLE IF NOT EXISTS bop_changes (
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    id          TEXT NOT NULL,
    process_id  TEXT NOT NULL,
    status      TEXT NOT NULL,
    applied_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    data        JSONB NOT NULL,
    PRIMARY KEY (tenant_id, id)
);
CREATE INDEX IF NOT EXISTS bop_changes_proc_idx
    ON bop_changes (tenant_id, process_id, applied_at DESC);
"""

# Child tables wiped (by tenant_id + process_id) when a process is deleted.
# bop_audit is deliberately excluded: the audit ledger is append-only and must
# survive process deletion (the deletion itself is recorded as an audit event).
_CHILD_TABLES = (
    "bop_samples",
    "bop_proposals",
    "bop_bottlenecks",
    "bop_rules",
    "bop_firings",
    "bop_mining",
    "bop_events",
    "bop_slas",
    "bop_versions",
    "bop_changes",
)

__all__ = ["SCHEMA_DDL", "_CHILD_TABLES"]
