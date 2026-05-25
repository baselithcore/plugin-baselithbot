"""DDL bootstrap for the red_agent Postgres schema.

Schema bootstrap is a single transaction. Statement order matters because
``CREATE TABLE IF NOT EXISTS`` is a no-op on existing tables — so any new
columns must be added by ``ALTER TABLE`` BEFORE any index that references
them is created. The current order is: (1) base ``CREATE TABLE`` statements
with original columns only, (2) idempotent ``ALTER TABLE`` additions for new
columns, (3) all indexes — so both fresh and upgraded deployments converge
on the same final schema in one transaction.
"""

from __future__ import annotations

from typing import Any, cast

import psycopg

from core.observability.logging import get_logger

from ._schema_daemon import ensure_daemon_schema

logger = get_logger(__name__)


SCHEMA_DDL = """
-- (1) base tables -----------------------------------------------------

CREATE TABLE IF NOT EXISTS red_agent_targets (
    id              uuid PRIMARY KEY,
    kind            text NOT NULL,
    name            text NOT NULL,
    value           text NOT NULL,
    environment     text,
    owner           text,
    tags            text[] NOT NULL DEFAULT '{}',
    profile         jsonb NOT NULL DEFAULT '{}'::jsonb,
    schedule_cron   text,
    scope_overrides jsonb NOT NULL DEFAULT '{}'::jsonb,
    description     text,
    tenant_id       text,
    created_by      text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    last_scan_at    timestamptz,
    archived_at     timestamptz,
    UNIQUE (tenant_id, kind, value)
);

CREATE TABLE IF NOT EXISTS red_agent_engagements (
    id              uuid PRIMARY KEY,
    name            text NOT NULL,
    objective       text NOT NULL,
    status          text NOT NULL DEFAULT 'draft',
    rules           jsonb NOT NULL DEFAULT '{}'::jsonb,
    tags            text[] NOT NULL DEFAULT '{}',
    tenant_id       text,
    created_by      text,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now(),
    starts_at       timestamptz,
    ends_at         timestamptz,
    archived_at     timestamptz
);

CREATE TABLE IF NOT EXISTS red_agent_scans (
    id              uuid PRIMARY KEY,
    status          text NOT NULL,
    target_type     text NOT NULL,
    target_value    text NOT NULL,
    intensity       text NOT NULL,
    scanners        text[] NOT NULL DEFAULT '{}',
    tenant_id       text,
    requested_by    text,
    bug_bounty_program text,
    notes           text,
    error           text,
    started_at      timestamptz NOT NULL DEFAULT now(),
    finished_at     timestamptz
);

CREATE TABLE IF NOT EXISTS red_agent_findings (
    id              uuid PRIMARY KEY,
    scan_id         uuid NOT NULL REFERENCES red_agent_scans(id) ON DELETE CASCADE,
    scanner         text NOT NULL,
    title           text NOT NULL,
    description     text NOT NULL DEFAULT '',
    severity        text NOT NULL,
    cvss_score      numeric,
    cwe             text,
    cve             text,
    target          text NOT NULL,
    endpoint        text,
    port            integer,
    service         text,
    evidence        jsonb NOT NULL DEFAULT '{}'::jsonb,
    raw             jsonb NOT NULL DEFAULT '{}'::jsonb,
    remediation     text,
    discovered_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS red_agent_audit (
    id              bigserial PRIMARY KEY,
    scan_id         uuid,
    actor           text,
    event           text NOT NULL,
    payload         jsonb NOT NULL DEFAULT '{}'::jsonb,
    created_at      timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS red_agent_approvals (
    scan_id         uuid PRIMARY KEY,
    state           text NOT NULL,
    reason          text,
    requested_by    text,
    resolved_by     text,
    opened_at       timestamptz NOT NULL DEFAULT now(),
    resolved_at     timestamptz
);

CREATE TABLE IF NOT EXISTS red_agent_policy (
    id              smallint PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    overrides       jsonb NOT NULL DEFAULT '{}'::jsonb,
    updated_by      text,
    updated_at      timestamptz NOT NULL DEFAULT now()
);

-- (2) idempotent column adds (target-as-project + finding lifecycle) --

ALTER TABLE red_agent_scans
    ADD COLUMN IF NOT EXISTS target_id uuid REFERENCES red_agent_targets(id) ON DELETE SET NULL;
ALTER TABLE red_agent_scans
    ADD COLUMN IF NOT EXISTS engagement_id uuid REFERENCES red_agent_engagements(id) ON DELETE SET NULL;

ALTER TABLE red_agent_findings
    ADD COLUMN IF NOT EXISTS state text NOT NULL DEFAULT 'open';
ALTER TABLE red_agent_findings
    ADD COLUMN IF NOT EXISTS assignee text;
ALTER TABLE red_agent_findings
    ADD COLUMN IF NOT EXISTS triaged_at timestamptz;
ALTER TABLE red_agent_findings
    ADD COLUMN IF NOT EXISTS resolved_at timestamptz;
ALTER TABLE red_agent_findings
    ADD COLUMN IF NOT EXISTS due_at timestamptz;
ALTER TABLE red_agent_findings
    ADD COLUMN IF NOT EXISTS notes text;
ALTER TABLE red_agent_findings
    ADD COLUMN IF NOT EXISTS risk_score numeric;
ALTER TABLE red_agent_findings
    ADD COLUMN IF NOT EXISTS controls text[] NOT NULL DEFAULT ARRAY[]::text[];
ALTER TABLE red_agent_findings
    ADD COLUMN IF NOT EXISTS external_ref text;
CREATE INDEX IF NOT EXISTS red_agent_findings_external_ref_idx
    ON red_agent_findings(external_ref);

ALTER TABLE red_agent_findings
    ADD COLUMN IF NOT EXISTS validation_status text NOT NULL DEFAULT 'unvalidated';
ALTER TABLE red_agent_findings
    ADD COLUMN IF NOT EXISTS validation_method text;
ALTER TABLE red_agent_findings
    ADD COLUMN IF NOT EXISTS validation_evidence jsonb NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE red_agent_findings
    ADD COLUMN IF NOT EXISTS validated_at timestamptz;
CREATE INDEX IF NOT EXISTS red_agent_findings_validation_status_idx
    ON red_agent_findings(validation_status);

-- Differential-scan cache: input fingerprint → last successful scan.
CREATE TABLE IF NOT EXISTS red_agent_scan_fingerprints (
    fingerprint     text NOT NULL,
    scanner         text NOT NULL,
    scan_id         uuid NOT NULL REFERENCES red_agent_scans(id) ON DELETE CASCADE,
    tenant_id       text,
    completed_at    timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (fingerprint, scanner)
);
CREATE INDEX IF NOT EXISTS red_agent_scan_fingerprints_scanner_idx
    ON red_agent_scan_fingerprints(scanner);
CREATE INDEX IF NOT EXISTS red_agent_scan_fingerprints_tenant_idx
    ON red_agent_scan_fingerprints(tenant_id);
CREATE INDEX IF NOT EXISTS red_agent_scan_fingerprints_completed_idx
    ON red_agent_scan_fingerprints(completed_at);

-- (3) indexes (must run AFTER ALTER TABLE so referenced columns exist) --

CREATE INDEX IF NOT EXISTS red_agent_targets_tenant_idx
    ON red_agent_targets(tenant_id);
CREATE INDEX IF NOT EXISTS red_agent_targets_kind_idx
    ON red_agent_targets(kind);
CREATE INDEX IF NOT EXISTS red_agent_targets_archived_idx
    ON red_agent_targets(archived_at);

CREATE INDEX IF NOT EXISTS red_agent_engagements_tenant_idx
    ON red_agent_engagements(tenant_id);
CREATE INDEX IF NOT EXISTS red_agent_engagements_status_idx
    ON red_agent_engagements(status);
CREATE INDEX IF NOT EXISTS red_agent_engagements_archived_idx
    ON red_agent_engagements(archived_at);

CREATE INDEX IF NOT EXISTS red_agent_scans_target_id_idx
    ON red_agent_scans(target_id);
CREATE INDEX IF NOT EXISTS red_agent_scans_engagement_id_idx
    ON red_agent_scans(engagement_id);

CREATE INDEX IF NOT EXISTS red_agent_findings_severity_idx
    ON red_agent_findings(severity);
CREATE INDEX IF NOT EXISTS red_agent_findings_scan_id_idx
    ON red_agent_findings(scan_id);
CREATE INDEX IF NOT EXISTS red_agent_findings_target_idx
    ON red_agent_findings(target);
CREATE INDEX IF NOT EXISTS red_agent_findings_state_idx
    ON red_agent_findings(state);
CREATE INDEX IF NOT EXISTS red_agent_findings_due_idx
    ON red_agent_findings(due_at);
"""


async def ensure_schema(dsn: str) -> bool:
    """Idempotent schema bootstrap. Returns True on success.

    Runs the original scan/finding DDL first, then chains into
    :func:`ensure_daemon_schema` so the endpoint-daemon tables are
    created in the same bootstrap pass. The two phases run in separate
    transactions on purpose: a failure in the daemon DDL must not roll
    back the core scan schema, which is required for the rest of the
    plugin to function.
    """
    if not dsn:
        return False
    try:
        connect = cast(Any, psycopg.AsyncConnection.connect)
        async with await connect(dsn) as conn:
            await conn.execute(SCHEMA_DDL)
            await conn.commit()
    except Exception as e:  # noqa: BLE001
        logger.warning(
            "red_agent.schema.bootstrap_failed",
            extra={"error": str(e)},
        )
        return False

    daemon_ok = await ensure_daemon_schema(dsn)
    if not daemon_ok:
        logger.warning("red_agent.daemon_schema.skipped")
    return True
