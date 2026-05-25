"""DDL bootstrap for the endpoint-daemon-related Red Agent tables.

Kept in a separate module from ``_schema.py`` so each file stays under
the 500-LOC cap and the daemon-specific schema can evolve without
churning the original scan/finding bootstrap.

Tables managed here:

* ``red_agent_agents`` — registry of enrolled hosts.
* ``red_agent_agent_certs`` — cert lifecycle (issue / rotate / revoke).
* ``red_agent_enrollment_tokens`` — single-use bearer tokens.
* ``red_agent_agent_commands`` — command audit (idempotency-keyed).
* ``red_agent_agent_telemetry`` — partitioned hot tier.
* ``red_agent_agent_audit_log`` — append-only daemon audit (hash-chained).

Every table carries a ``tenant_id TEXT NOT NULL`` column and has Row
Level Security enabled with a policy that resolves ``app.tenant_id``
from the session via :func:`red_agent_current_tenant`. The FastAPI /
gRPC interceptor is responsible for setting that variable inside a
transaction before any query against these tables. The mirror
``migrations/004_endpoint_daemon.sql`` file is the canonical reference
and the target of any future external migration tooling.
"""

from __future__ import annotations

from typing import Any, cast

import psycopg

from core.observability.logging import get_logger

logger = get_logger(__name__)


DAEMON_SCHEMA_DDL = r"""
-- Helper: tenant context accessor used by every RLS policy below.
CREATE OR REPLACE FUNCTION red_agent_current_tenant() RETURNS TEXT
LANGUAGE plpgsql STABLE AS $$
BEGIN
    RETURN current_setting('app.tenant_id', true);
END;
$$;

-- 1. Agents registry. -------------------------------------------------------

CREATE TABLE IF NOT EXISTS red_agent_agents (
    agent_uuid          uuid PRIMARY KEY,
    tenant_id           text NOT NULL,
    os                  text NOT NULL CHECK (os IN ('linux', 'macos', 'windows')),
    os_version          text,
    kernel_version      text,
    arch                text NOT NULL CHECK (arch IN ('x86_64', 'aarch64')),
    hostname            text,
    boot_id             text,
    cpu_count           integer,
    mem_total_bytes     bigint,
    daemon_version      text,
    protocol_version    integer NOT NULL,
    capabilities        text[] NOT NULL DEFAULT '{}',
    labels              jsonb NOT NULL DEFAULT '{}'::jsonb,
    status              text NOT NULL DEFAULT 'enrolled'
        CHECK (status IN ('enrolled', 'online', 'offline', 'revoked', 'disabled')),
    last_seen_at        timestamptz,
    last_disconnect_reason text,
    enrolled_at         timestamptz NOT NULL DEFAULT now(),
    enrolled_by         text,
    archived_at         timestamptz
);

CREATE INDEX IF NOT EXISTS red_agent_agents_tenant_idx
    ON red_agent_agents (tenant_id);
CREATE INDEX IF NOT EXISTS red_agent_agents_status_idx
    ON red_agent_agents (status);
CREATE INDEX IF NOT EXISTS red_agent_agents_last_seen_idx
    ON red_agent_agents (last_seen_at DESC);
CREATE INDEX IF NOT EXISTS red_agent_agents_labels_gin
    ON red_agent_agents USING GIN (labels);

ALTER TABLE red_agent_agents ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS agents_tenant_isolation ON red_agent_agents;
CREATE POLICY agents_tenant_isolation ON red_agent_agents
    USING (tenant_id = red_agent_current_tenant());

-- 2. Cert lifecycle. --------------------------------------------------------

CREATE TABLE IF NOT EXISTS red_agent_agent_certs (
    serial              text PRIMARY KEY,
    agent_uuid          uuid NOT NULL REFERENCES red_agent_agents(agent_uuid) ON DELETE CASCADE,
    tenant_id           text NOT NULL,
    fingerprint_sha256  text NOT NULL UNIQUE,
    spiffe_uri          text NOT NULL,
    not_before          timestamptz NOT NULL,
    not_after           timestamptz NOT NULL,
    state               text NOT NULL DEFAULT 'active'
        CHECK (state IN ('active', 'rotated', 'expired', 'revoked')),
    issued_at           timestamptz NOT NULL DEFAULT now(),
    rotated_at          timestamptz,
    revoked_at          timestamptz,
    revoked_reason      text,
    revoked_by          text
);

CREATE INDEX IF NOT EXISTS red_agent_certs_agent_idx
    ON red_agent_agent_certs (agent_uuid);
CREATE INDEX IF NOT EXISTS red_agent_certs_tenant_idx
    ON red_agent_agent_certs (tenant_id);
CREATE INDEX IF NOT EXISTS red_agent_certs_state_idx
    ON red_agent_agent_certs (state);
CREATE INDEX IF NOT EXISTS red_agent_certs_not_after_idx
    ON red_agent_agent_certs (not_after);
CREATE UNIQUE INDEX IF NOT EXISTS red_agent_certs_active_per_agent_uq
    ON red_agent_agent_certs (agent_uuid)
    WHERE state = 'active';

ALTER TABLE red_agent_agent_certs ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS certs_tenant_isolation ON red_agent_agent_certs;
CREATE POLICY certs_tenant_isolation ON red_agent_agent_certs
    USING (tenant_id = red_agent_current_tenant());

-- 3. Enrollment tokens. -----------------------------------------------------

CREATE TABLE IF NOT EXISTS red_agent_enrollment_tokens (
    id                  uuid PRIMARY KEY,
    tenant_id           text NOT NULL,
    token_sha256        text NOT NULL UNIQUE,
    bind_agent_uuid     uuid,
    labels              jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at          timestamptz NOT NULL DEFAULT now(),
    created_by          text NOT NULL,
    expires_at          timestamptz NOT NULL,
    state               text NOT NULL DEFAULT 'unused'
        CHECK (state IN ('unused', 'redeemed', 'expired', 'revoked')),
    redeemed_at         timestamptz,
    -- ``redeemed_agent_uuid`` is an audit trace field. We deliberately
    -- avoid a foreign-key constraint here: the redeem path validates
    -- the token *before* the agent row exists (chicken-egg), and the
    -- value is informational once the agent is enrolled.
    redeemed_agent_uuid uuid,
    revoked_at          timestamptz,
    revoked_by          text
);

-- Drop legacy FK constraint if a previous bootstrap created it. Safe
-- on fresh installs (no-op when the constraint never existed).
ALTER TABLE red_agent_enrollment_tokens
    DROP CONSTRAINT IF EXISTS red_agent_enrollment_tokens_redeemed_agent_uuid_fkey;

CREATE INDEX IF NOT EXISTS red_agent_enroll_tokens_tenant_idx
    ON red_agent_enrollment_tokens (tenant_id);
CREATE INDEX IF NOT EXISTS red_agent_enroll_tokens_state_idx
    ON red_agent_enrollment_tokens (state);
CREATE INDEX IF NOT EXISTS red_agent_enroll_tokens_expires_idx
    ON red_agent_enrollment_tokens (expires_at);

ALTER TABLE red_agent_enrollment_tokens ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS enroll_tokens_tenant_isolation ON red_agent_enrollment_tokens;
CREATE POLICY enroll_tokens_tenant_isolation ON red_agent_enrollment_tokens
    USING (tenant_id = red_agent_current_tenant());

-- 4. Command audit. ---------------------------------------------------------

CREATE TABLE IF NOT EXISTS red_agent_agent_commands (
    id                  uuid PRIMARY KEY,
    tenant_id           text NOT NULL,
    agent_uuid          uuid NOT NULL REFERENCES red_agent_agents(agent_uuid) ON DELETE CASCADE,
    idempotency_key     text NOT NULL,
    correlation_id      text,
    kind                text NOT NULL,
    payload             jsonb NOT NULL,
    state               text NOT NULL DEFAULT 'queued'
        CHECK (state IN ('queued', 'sent', 'acked', 'completed', 'failed', 'timeout', 'rejected')),
    requested_by        text NOT NULL,
    requested_at        timestamptz NOT NULL DEFAULT now(),
    sent_at             timestamptz,
    completed_at        timestamptz,
    deadline            timestamptz,
    result_status       text,
    result_payload      jsonb,
    error_code          text,
    error_message       text,
    elapsed_ms          bigint
);

CREATE UNIQUE INDEX IF NOT EXISTS red_agent_commands_idempotency_uq
    ON red_agent_agent_commands (agent_uuid, idempotency_key);
CREATE INDEX IF NOT EXISTS red_agent_commands_tenant_idx
    ON red_agent_agent_commands (tenant_id);
CREATE INDEX IF NOT EXISTS red_agent_commands_agent_idx
    ON red_agent_agent_commands (agent_uuid);
CREATE INDEX IF NOT EXISTS red_agent_commands_state_idx
    ON red_agent_agent_commands (state);
CREATE INDEX IF NOT EXISTS red_agent_commands_requested_idx
    ON red_agent_agent_commands (requested_at DESC);
CREATE INDEX IF NOT EXISTS red_agent_commands_correlation_idx
    ON red_agent_agent_commands (correlation_id)
    WHERE correlation_id IS NOT NULL;

ALTER TABLE red_agent_agent_commands ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS commands_tenant_isolation ON red_agent_agent_commands;
CREATE POLICY commands_tenant_isolation ON red_agent_agent_commands
    USING (tenant_id = red_agent_current_tenant());

-- 5. Telemetry (RANGE-partitioned by observed_at). --------------------------

CREATE TABLE IF NOT EXISTS red_agent_agent_telemetry (
    id              uuid NOT NULL,
    tenant_id       text NOT NULL,
    agent_uuid      uuid NOT NULL,
    observed_at     timestamptz NOT NULL,
    received_at     timestamptz NOT NULL DEFAULT now(),
    kind            text NOT NULL,
    severity        text NOT NULL DEFAULT 'info'
        CHECK (severity IN ('info', 'low', 'medium', 'high', 'critical')),
    attributes      jsonb NOT NULL DEFAULT '{}'::jsonb,
    correlation_id  text,
    batch_id        uuid NOT NULL,
    batch_seq       integer NOT NULL,
    PRIMARY KEY (id, observed_at)
) PARTITION BY RANGE (observed_at);

CREATE INDEX IF NOT EXISTS red_agent_telemetry_tenant_idx
    ON red_agent_agent_telemetry (tenant_id);
CREATE INDEX IF NOT EXISTS red_agent_telemetry_agent_idx
    ON red_agent_agent_telemetry (agent_uuid, observed_at DESC);
CREATE INDEX IF NOT EXISTS red_agent_telemetry_kind_idx
    ON red_agent_agent_telemetry (kind);
CREATE INDEX IF NOT EXISTS red_agent_telemetry_correlation_idx
    ON red_agent_agent_telemetry (correlation_id)
    WHERE correlation_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS red_agent_telemetry_attributes_gin
    ON red_agent_agent_telemetry USING GIN (attributes);

ALTER TABLE red_agent_agent_telemetry ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS telemetry_tenant_isolation ON red_agent_agent_telemetry;
CREATE POLICY telemetry_tenant_isolation ON red_agent_agent_telemetry
    USING (tenant_id = red_agent_current_tenant());

-- Bootstrap current + next month partitions. The Phase-1 maintenance
-- task adds further partitions monthly via cron.
DO $part$
DECLARE
    cur_month_start  date := date_trunc('month', now())::date;
    next_month_start date := (date_trunc('month', now()) + interval '1 month')::date;
    after_next       date := (date_trunc('month', now()) + interval '2 months')::date;
    partname         text;
BEGIN
    partname := format('red_agent_agent_telemetry_%s',
                       to_char(cur_month_start, 'YYYY_MM'));
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF red_agent_agent_telemetry
            FOR VALUES FROM (%L) TO (%L)',
        partname, cur_month_start, next_month_start
    );

    partname := format('red_agent_agent_telemetry_%s',
                       to_char(next_month_start, 'YYYY_MM'));
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF red_agent_agent_telemetry
            FOR VALUES FROM (%L) TO (%L)',
        partname, next_month_start, after_next
    );
END
$part$;

-- 6. Daemon-side audit log (separate from scan-focused red_agent_audit). ----

CREATE TABLE IF NOT EXISTS red_agent_agent_audit_log (
    id              bigserial PRIMARY KEY,
    tenant_id       text NOT NULL,
    agent_uuid      uuid,
    actor           text NOT NULL,
    event           text NOT NULL,
    payload         jsonb NOT NULL DEFAULT '{}'::jsonb,
    occurred_at     timestamptz NOT NULL DEFAULT now(),
    prev_hash       bytea,
    row_hash        bytea NOT NULL
);

CREATE INDEX IF NOT EXISTS red_agent_agent_audit_tenant_idx
    ON red_agent_agent_audit_log (tenant_id);
CREATE INDEX IF NOT EXISTS red_agent_agent_audit_agent_idx
    ON red_agent_agent_audit_log (agent_uuid);
CREATE INDEX IF NOT EXISTS red_agent_agent_audit_event_idx
    ON red_agent_agent_audit_log (event);
CREATE INDEX IF NOT EXISTS red_agent_agent_audit_occurred_idx
    ON red_agent_agent_audit_log (occurred_at DESC);

ALTER TABLE red_agent_agent_audit_log ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS agent_audit_tenant_isolation ON red_agent_agent_audit_log;
CREATE POLICY agent_audit_tenant_isolation ON red_agent_agent_audit_log
    USING (tenant_id = red_agent_current_tenant());
DROP POLICY IF EXISTS agent_audit_no_update ON red_agent_agent_audit_log;
CREATE POLICY agent_audit_no_update ON red_agent_agent_audit_log
    FOR UPDATE USING (false);
DROP POLICY IF EXISTS agent_audit_no_delete ON red_agent_agent_audit_log;
CREATE POLICY agent_audit_no_delete ON red_agent_agent_audit_log
    FOR DELETE USING (false);

-- 7. Findings origin discriminator. -----------------------------------------

ALTER TABLE red_agent_findings
    ADD COLUMN IF NOT EXISTS source text NOT NULL DEFAULT 'sandbox'
        CHECK (source IN ('sandbox', 'endpoint'));
ALTER TABLE red_agent_findings
    ADD COLUMN IF NOT EXISTS agent_uuid uuid REFERENCES red_agent_agents(agent_uuid) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS red_agent_findings_source_idx
    ON red_agent_findings (source);
CREATE INDEX IF NOT EXISTS red_agent_findings_agent_idx
    ON red_agent_findings (agent_uuid)
    WHERE agent_uuid IS NOT NULL;
"""


async def ensure_daemon_schema(dsn: str) -> bool:
    """Apply the daemon-related DDL idempotently.

    Returns True on success. Failures are logged at WARNING and surface
    as False so the caller (``ensure_schema``) can decide whether to
    abort plugin bootstrap or continue with a degraded surface.
    """
    if not dsn:
        return False
    try:
        connect = cast(Any, psycopg.AsyncConnection.connect)
        async with await connect(dsn) as conn:
            await conn.execute(DAEMON_SCHEMA_DDL)
            await conn.commit()
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "red_agent.daemon_schema.bootstrap_failed",
            extra={"error": str(e)},
        )
        return False
