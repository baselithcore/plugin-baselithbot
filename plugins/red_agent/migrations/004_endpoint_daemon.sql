-- Red Agent endpoint daemon tables.
--
-- Adds the persistence surface for the on-host daemon (`baselith-redagent-daemon`):
--   * agent registry (one row per enrolled host)
--   * cert lifecycle + revocation tracking
--   * single-use enrollment tokens
--   * append-only command audit (idempotency-keyed, replay-safe)
--   * partitioned, monthly-rotated telemetry hot tier
--   * append-only daemon-side audit log (separate from scan audit)
--
-- Multi-tenancy is enforced at the row level. Every daemon-related
-- table carries a `tenant_id TEXT NOT NULL` column matching the
-- convention established in migration 003 (`red_agent_targets`).
-- Row-level security is enabled and policies require the session
-- variable `app.tenant_id` to be set by the FastAPI / gRPC
-- interceptor before any query against these tables.
--
-- See plugins/red_agent/docs/agent_daemon.md for the full design.

-- ---------------------------------------------------------------------------
-- Helper: tenant context accessor.
-- The interceptor sets `app.tenant_id` per session via
-- `SET LOCAL app.tenant_id = '<uuid-or-text>'` inside a transaction.
-- The function returns NULL when unset, which RLS policies treat as
-- "no rows visible" — fail closed.
-- ---------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION red_agent_current_tenant() RETURNS TEXT
LANGUAGE plpgsql STABLE AS $$
BEGIN
    RETURN current_setting('app.tenant_id', true);
END;
$$;

-- ---------------------------------------------------------------------------
-- 1. Agents registry.
-- One row per enrolled daemon. `agent_uuid` is generated on-host and
-- persisted across reboots / cert rotations; it is the durable
-- identity the daemon claims in its SPIFFE URI SAN.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS red_agent_agents (
    agent_uuid          UUID PRIMARY KEY,
    tenant_id           TEXT NOT NULL,

    -- Platform metadata captured at last AgentHello.
    os                  TEXT NOT NULL CHECK (os IN ('linux', 'macos', 'windows')),
    os_version          TEXT,
    kernel_version      TEXT,
    arch                TEXT NOT NULL CHECK (arch IN ('x86_64', 'aarch64')),
    hostname            TEXT,
    boot_id             TEXT,
    cpu_count           INTEGER,
    mem_total_bytes     BIGINT,

    -- Daemon version (semver) at last connect. Used to gate rolling
    -- upgrades and detect lagging agents.
    daemon_version      TEXT,
    protocol_version    INTEGER NOT NULL,

    -- Effective negotiated capability set (subset of declared).
    capabilities        TEXT[] NOT NULL DEFAULT '{}',

    -- Free-form labels for policy targeting (`env=prod`, `region=eu`, ...).
    -- Phase 2 introduces label-based scheduling; the column is here from
    -- day 1 so backfill is cheap.
    labels              JSONB NOT NULL DEFAULT '{}'::jsonb,

    -- Connection state. Updated by the gRPC service.
    status              TEXT NOT NULL DEFAULT 'enrolled'
        CHECK (status IN ('enrolled', 'online', 'offline', 'revoked', 'disabled')),
    last_seen_at        TIMESTAMPTZ,
    last_disconnect_reason TEXT,

    -- Metadata.
    enrolled_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    enrolled_by         TEXT,
    archived_at         TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_agents_tenant ON red_agent_agents (tenant_id);
CREATE INDEX IF NOT EXISTS idx_agents_status ON red_agent_agents (status);
CREATE INDEX IF NOT EXISTS idx_agents_last_seen ON red_agent_agents (last_seen_at DESC);
CREATE INDEX IF NOT EXISTS idx_agents_labels_gin ON red_agent_agents USING GIN (labels);

ALTER TABLE red_agent_agents ENABLE ROW LEVEL SECURITY;

CREATE POLICY agents_tenant_isolation ON red_agent_agents
    USING (tenant_id = red_agent_current_tenant());

-- ---------------------------------------------------------------------------
-- 2. Certificate lifecycle.
-- Tracks every cert issued to an agent. We keep history (not just the
-- active row) so revocation, rotation audits, and forensic queries
-- ("which cert was active at T?") all work.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS red_agent_agent_certs (
    serial              TEXT PRIMARY KEY,                 -- cert serial number
    agent_uuid          UUID NOT NULL REFERENCES red_agent_agents(agent_uuid) ON DELETE CASCADE,
    tenant_id           TEXT NOT NULL,
    fingerprint_sha256  TEXT NOT NULL UNIQUE,             -- SPKI fingerprint hex
    spiffe_uri          TEXT NOT NULL,
    not_before          TIMESTAMPTZ NOT NULL,
    not_after           TIMESTAMPTZ NOT NULL,

    -- Lifecycle state.
    state               TEXT NOT NULL DEFAULT 'active'
        CHECK (state IN ('active', 'rotated', 'expired', 'revoked')),
    issued_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    rotated_at          TIMESTAMPTZ,
    revoked_at          TIMESTAMPTZ,
    revoked_reason      TEXT,
    revoked_by          TEXT
);

CREATE INDEX IF NOT EXISTS idx_certs_agent ON red_agent_agent_certs (agent_uuid);
CREATE INDEX IF NOT EXISTS idx_certs_tenant ON red_agent_agent_certs (tenant_id);
CREATE INDEX IF NOT EXISTS idx_certs_state ON red_agent_agent_certs (state);
CREATE INDEX IF NOT EXISTS idx_certs_not_after ON red_agent_agent_certs (not_after);

-- Only one active cert per agent at any time. Enforced via partial
-- unique index rather than a CHECK constraint so we can have many
-- rotated/revoked rows in history.
CREATE UNIQUE INDEX IF NOT EXISTS uq_certs_active_per_agent
    ON red_agent_agent_certs (agent_uuid)
    WHERE state = 'active';

ALTER TABLE red_agent_agent_certs ENABLE ROW LEVEL SECURITY;

CREATE POLICY certs_tenant_isolation ON red_agent_agent_certs
    USING (tenant_id = red_agent_current_tenant());

-- ---------------------------------------------------------------------------
-- 3. Enrollment tokens.
-- Single-use, time-bound bearer tokens that authorize a fresh host to
-- request a tenant-scoped cert. Stored hashed (never plaintext) so a
-- DB read does not leak active enrollment material.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS red_agent_enrollment_tokens (
    id                  UUID PRIMARY KEY,
    tenant_id           TEXT NOT NULL,

    -- SHA-256 of the bearer token. The plaintext token is shown to
    -- the operator exactly once at creation and never persisted.
    token_sha256        TEXT NOT NULL UNIQUE,

    -- Optional pre-binding to a specific agent_uuid. When NULL the
    -- token is freely-redeemable; when set it can only enroll that
    -- specific UUID (used by MDM-driven provisioning).
    bind_agent_uuid     UUID,

    -- Optional initial labels applied to the resulting agent row.
    labels              JSONB NOT NULL DEFAULT '{}'::jsonb,

    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by          TEXT NOT NULL,
    expires_at          TIMESTAMPTZ NOT NULL,

    -- Lifecycle: 'unused' | 'redeemed' | 'expired' | 'revoked'.
    state               TEXT NOT NULL DEFAULT 'unused'
        CHECK (state IN ('unused', 'redeemed', 'expired', 'revoked')),
    redeemed_at         TIMESTAMPTZ,
    -- ``redeemed_agent_uuid`` is intentionally NOT a foreign key:
    -- the redeem path validates the token before the agent row is
    -- created. The value is informational audit trace.
    redeemed_agent_uuid UUID,
    revoked_at          TIMESTAMPTZ,
    revoked_by          TEXT
);

CREATE INDEX IF NOT EXISTS idx_enroll_tokens_tenant ON red_agent_enrollment_tokens (tenant_id);
CREATE INDEX IF NOT EXISTS idx_enroll_tokens_state ON red_agent_enrollment_tokens (state);
CREATE INDEX IF NOT EXISTS idx_enroll_tokens_expires ON red_agent_enrollment_tokens (expires_at);

ALTER TABLE red_agent_enrollment_tokens ENABLE ROW LEVEL SECURITY;

CREATE POLICY enroll_tokens_tenant_isolation ON red_agent_enrollment_tokens
    USING (tenant_id = red_agent_current_tenant());

-- ---------------------------------------------------------------------------
-- 4. Command audit.
-- Every Command sent to an agent and every CommandResult returned is
-- recorded here, idempotency-keyed. The dedup index on
-- (agent_uuid, idempotency_key) lets the gRPC handler re-deliver
-- safely after a network blip.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS red_agent_agent_commands (
    id                  UUID PRIMARY KEY,
    tenant_id           TEXT NOT NULL,
    agent_uuid          UUID NOT NULL REFERENCES red_agent_agents(agent_uuid) ON DELETE CASCADE,

    idempotency_key     TEXT NOT NULL,
    correlation_id      TEXT,

    -- Command kind: 'inventory' | 'local_scan' | 'hash_files' |
    -- 'collect_artifact' | 'apply_config' | 'self_update'.
    kind                TEXT NOT NULL,

    -- Command payload (the proto Command sub-message, JSON-encoded).
    payload             JSONB NOT NULL,

    -- Lifecycle.
    state               TEXT NOT NULL DEFAULT 'queued'
        CHECK (state IN ('queued', 'sent', 'acked', 'completed', 'failed', 'timeout', 'rejected')),

    -- Audit fields.
    requested_by        TEXT NOT NULL,
    requested_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    sent_at             TIMESTAMPTZ,
    completed_at        TIMESTAMPTZ,
    deadline            TIMESTAMPTZ,

    -- Result fields. CommandResult.payload lands in `result_payload`,
    -- error fields in their own columns for cheap querying.
    result_status       TEXT,
    result_payload      JSONB,
    error_code          TEXT,
    error_message       TEXT,
    elapsed_ms          BIGINT
);

-- Idempotency: same agent + same key returns the existing row.
CREATE UNIQUE INDEX IF NOT EXISTS uq_commands_idempotency
    ON red_agent_agent_commands (agent_uuid, idempotency_key);

CREATE INDEX IF NOT EXISTS idx_commands_tenant ON red_agent_agent_commands (tenant_id);
CREATE INDEX IF NOT EXISTS idx_commands_agent ON red_agent_agent_commands (agent_uuid);
CREATE INDEX IF NOT EXISTS idx_commands_state ON red_agent_agent_commands (state);
CREATE INDEX IF NOT EXISTS idx_commands_requested_at ON red_agent_agent_commands (requested_at DESC);
CREATE INDEX IF NOT EXISTS idx_commands_correlation ON red_agent_agent_commands (correlation_id)
    WHERE correlation_id IS NOT NULL;

ALTER TABLE red_agent_agent_commands ENABLE ROW LEVEL SECURITY;

CREATE POLICY commands_tenant_isolation ON red_agent_agent_commands
    USING (tenant_id = red_agent_current_tenant());

-- ---------------------------------------------------------------------------
-- 5. Telemetry (partitioned hot tier).
-- Append-only event stream from agents. Partitioned by RANGE on
-- `observed_at` with one partition per calendar month. Phase 2 adds a
-- maintenance job that creates next-month partitions in advance and
-- detaches partitions older than the retention window for archival
-- to the warm tier (ClickHouse / S3 / Loki).
--
-- Partitioning at this layer keeps point queries fast (the planner
-- prunes to a single partition) and makes retention sweeps cheap
-- (DROP partition vs DELETE). It also bounds the cost of an RLS
-- recheck.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS red_agent_agent_telemetry (
    id              UUID NOT NULL,
    tenant_id       TEXT NOT NULL,
    agent_uuid      UUID NOT NULL,

    observed_at     TIMESTAMPTZ NOT NULL,
    received_at     TIMESTAMPTZ NOT NULL DEFAULT now(),

    kind            TEXT NOT NULL,
    severity        TEXT NOT NULL DEFAULT 'info'
        CHECK (severity IN ('info', 'low', 'medium', 'high', 'critical')),

    -- Event payload schema is per-`kind`, documented in the daemon
    -- repo. We do not enforce a structure at the DB layer.
    attributes      JSONB NOT NULL DEFAULT '{}'::jsonb,
    correlation_id  TEXT,

    -- Stream sequencing for replay / dedup.
    batch_id        UUID NOT NULL,
    batch_seq       INTEGER NOT NULL,

    PRIMARY KEY (id, observed_at)
) PARTITION BY RANGE (observed_at);

CREATE INDEX IF NOT EXISTS idx_telemetry_tenant ON red_agent_agent_telemetry (tenant_id);
CREATE INDEX IF NOT EXISTS idx_telemetry_agent ON red_agent_agent_telemetry (agent_uuid, observed_at DESC);
CREATE INDEX IF NOT EXISTS idx_telemetry_kind ON red_agent_agent_telemetry (kind);
CREATE INDEX IF NOT EXISTS idx_telemetry_correlation ON red_agent_agent_telemetry (correlation_id)
    WHERE correlation_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_telemetry_attributes_gin
    ON red_agent_agent_telemetry USING GIN (attributes);

ALTER TABLE red_agent_agent_telemetry ENABLE ROW LEVEL SECURITY;

CREATE POLICY telemetry_tenant_isolation ON red_agent_agent_telemetry
    USING (tenant_id = red_agent_current_tenant());

-- Bootstrap partitions: current month and next month. The Phase 1
-- maintenance task adds further partitions monthly via cron.
DO $$
DECLARE
    cur_month_start DATE := date_trunc('month', now())::DATE;
    next_month_start DATE := (date_trunc('month', now()) + INTERVAL '1 month')::DATE;
    after_next_month DATE := (date_trunc('month', now()) + INTERVAL '2 months')::DATE;
    partname TEXT;
BEGIN
    partname := format('red_agent_agent_telemetry_%s', to_char(cur_month_start, 'YYYY_MM'));
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF red_agent_agent_telemetry
            FOR VALUES FROM (%L) TO (%L)',
        partname, cur_month_start, next_month_start
    );

    partname := format('red_agent_agent_telemetry_%s', to_char(next_month_start, 'YYYY_MM'));
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF red_agent_agent_telemetry
            FOR VALUES FROM (%L) TO (%L)',
        partname, next_month_start, after_next_month
    );
END $$;

-- ---------------------------------------------------------------------------
-- 6. Daemon audit log.
-- Distinct from `red_agent_audit` (scan-focused). Captures
-- enrollment, cert rotation, revocation, command authorization, and
-- policy distribution events. Append-only; no UPDATE / DELETE.
-- Hash-chained per tenant so a tampered row breaks downstream
-- verification.
-- ---------------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS red_agent_agent_audit_log (
    id              BIGSERIAL PRIMARY KEY,
    tenant_id       TEXT NOT NULL,
    agent_uuid      UUID,            -- NULL for tenant-wide events
    actor           TEXT NOT NULL,
    event           TEXT NOT NULL,
    payload         JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at     TIMESTAMPTZ NOT NULL DEFAULT now(),

    -- SHA-256 hash of (prev_hash || canonical(payload)). Set by the
    -- application layer at insert time. Verified by audit export job.
    prev_hash       BYTEA,
    row_hash        BYTEA NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_agent_audit_tenant ON red_agent_agent_audit_log (tenant_id);
CREATE INDEX IF NOT EXISTS idx_agent_audit_agent ON red_agent_agent_audit_log (agent_uuid);
CREATE INDEX IF NOT EXISTS idx_agent_audit_event ON red_agent_agent_audit_log (event);
CREATE INDEX IF NOT EXISTS idx_agent_audit_occurred ON red_agent_agent_audit_log (occurred_at DESC);

ALTER TABLE red_agent_agent_audit_log ENABLE ROW LEVEL SECURITY;

CREATE POLICY agent_audit_tenant_isolation ON red_agent_agent_audit_log
    USING (tenant_id = red_agent_current_tenant());

-- Append-only: deny UPDATE and DELETE at the policy layer.
CREATE POLICY agent_audit_no_update ON red_agent_agent_audit_log
    FOR UPDATE USING (false);

CREATE POLICY agent_audit_no_delete ON red_agent_agent_audit_log
    FOR DELETE USING (false);

-- ---------------------------------------------------------------------------
-- 7. Findings origin discriminator.
-- Existing `red_agent_findings` table gains a `source` column so we
-- can distinguish scans produced server-side (from sandboxed Docker
-- scanners) from findings produced on-host by the daemon's local
-- executor. Backfill existing rows to 'sandbox'.
-- ---------------------------------------------------------------------------

ALTER TABLE red_agent_findings
    ADD COLUMN IF NOT EXISTS source       TEXT NOT NULL DEFAULT 'sandbox'
        CHECK (source IN ('sandbox', 'endpoint')),
    ADD COLUMN IF NOT EXISTS agent_uuid   UUID REFERENCES red_agent_agents(agent_uuid) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS idx_findings_source ON red_agent_findings (source);
CREATE INDEX IF NOT EXISTS idx_findings_agent ON red_agent_findings (agent_uuid)
    WHERE agent_uuid IS NOT NULL;
