"""DDL for the Postgres-backed :class:`PitwallStore`.

Each entity is a JSONB ``data`` blob (lossless round-trip of the Pydantic model,
resilient to additive evolution) plus the scalar columns needed for keying,
filtering, and insertion-order reads. All statements are idempotent
(``IF NOT EXISTS``) so :meth:`initialize` runs on every boot without an external
migration step, mirroring :class:`core.storage.postgres.PostgresStorage`.

The audit ledger (``pitwall_audit``) is deliberately excluded from the
delete-session cascade: it is append-only and must survive session deletion (the
deletion itself is recorded there).
"""

from __future__ import annotations

SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS pitwall_sessions (
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    id          TEXT NOT NULL,
    data        JSONB NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (tenant_id, id)
);
CREATE INDEX IF NOT EXISTS pitwall_sessions_tenant_idx
    ON pitwall_sessions (tenant_id, created_at DESC);

CREATE TABLE IF NOT EXISTS pitwall_recommendations (
    seq         BIGSERIAL PRIMARY KEY,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    session_id  TEXT NOT NULL,
    id          TEXT NOT NULL,
    car_id      TEXT NOT NULL DEFAULT '',
    data        JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS pitwall_recs_session_idx
    ON pitwall_recommendations (tenant_id, session_id, seq DESC);
CREATE INDEX IF NOT EXISTS pitwall_recs_car_idx
    ON pitwall_recommendations (tenant_id, session_id, car_id, seq DESC);

CREATE TABLE IF NOT EXISTS pitwall_audit (
    seq         BIGSERIAL PRIMARY KEY,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    session_id  TEXT NOT NULL DEFAULT '',
    data        JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS pitwall_audit_tenant_idx
    ON pitwall_audit (tenant_id, seq DESC);
CREATE INDEX IF NOT EXISTS pitwall_audit_session_idx
    ON pitwall_audit (tenant_id, session_id, seq DESC);

CREATE TABLE IF NOT EXISTS pitwall_acks (
    seq             BIGSERIAL PRIMARY KEY,
    tenant_id       TEXT NOT NULL DEFAULT 'default',
    session_id      TEXT NOT NULL,
    recommendation_id TEXT NOT NULL,
    data            JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS pitwall_acks_session_idx
    ON pitwall_acks (tenant_id, session_id, seq DESC);

CREATE TABLE IF NOT EXISTS pitwall_snapshots (
    seq         BIGSERIAL PRIMARY KEY,
    tenant_id   TEXT NOT NULL DEFAULT 'default',
    session_id  TEXT NOT NULL,
    car_id      TEXT NOT NULL,
    data        JSONB NOT NULL
);
CREATE INDEX IF NOT EXISTS pitwall_snapshots_car_idx
    ON pitwall_snapshots (tenant_id, session_id, car_id, seq);
"""

# Child tables wiped (by tenant_id + session_id) when a session is deleted.
# pitwall_audit is excluded on purpose — it is an append-only ledger.
_CHILD_TABLES = (
    "pitwall_recommendations",
    "pitwall_acks",
    "pitwall_snapshots",
)

__all__ = ["SCHEMA_DDL", "_CHILD_TABLES"]
