-- Red Agent initial schema
-- Tables intentionally append-only for findings; updates only via status transitions on scans.

CREATE TABLE IF NOT EXISTS red_agent_scans (
    id              UUID PRIMARY KEY,
    status          TEXT NOT NULL,
    target_type     TEXT NOT NULL,
    target_value    TEXT NOT NULL,
    intensity       TEXT NOT NULL,
    scanners        TEXT[] NOT NULL,
    tenant_id       TEXT,
    requested_by    TEXT NOT NULL,
    bug_bounty_program TEXT,
    notes           TEXT,
    error           TEXT,
    started_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at     TIMESTAMPTZ,
    duration_seconds DOUBLE PRECISION
);

CREATE INDEX IF NOT EXISTS idx_scans_tenant ON red_agent_scans (tenant_id);
CREATE INDEX IF NOT EXISTS idx_scans_status ON red_agent_scans (status);
CREATE INDEX IF NOT EXISTS idx_scans_started_at ON red_agent_scans (started_at DESC);

CREATE TABLE IF NOT EXISTS red_agent_findings (
    id            UUID PRIMARY KEY,
    scan_id       UUID NOT NULL REFERENCES red_agent_scans(id) ON DELETE CASCADE,
    scanner       TEXT NOT NULL,
    title         TEXT NOT NULL,
    description   TEXT NOT NULL,
    severity      TEXT NOT NULL,
    cvss_score    DOUBLE PRECISION,
    cwe           TEXT,
    cve           TEXT,
    target        TEXT NOT NULL,
    endpoint      TEXT,
    port          INTEGER,
    service       TEXT,
    evidence      JSONB NOT NULL DEFAULT '{}'::jsonb,
    raw           JSONB NOT NULL DEFAULT '{}'::jsonb,
    remediation   TEXT,
    discovered_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_findings_scan ON red_agent_findings (scan_id);
CREATE INDEX IF NOT EXISTS idx_findings_severity ON red_agent_findings (severity);
CREATE INDEX IF NOT EXISTS idx_findings_target ON red_agent_findings (target);

CREATE TABLE IF NOT EXISTS red_agent_audit (
    id            BIGSERIAL PRIMARY KEY,
    scan_id       UUID,
    actor         TEXT NOT NULL,
    event         TEXT NOT NULL,
    payload       JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_audit_scan ON red_agent_audit (scan_id);
CREATE INDEX IF NOT EXISTS idx_audit_event ON red_agent_audit (event);

-- HITL approval requests. A row is created when an active/intrusive scan
-- enters AWAITING_APPROVAL and updated to APPROVED / REJECTED / TIMEOUT
-- when the operator (or watchdog) resolves it. Survives process restart;
-- on boot the registry rehydrates open rows so the orchestrator can
-- resume waiting.
CREATE TABLE IF NOT EXISTS red_agent_approvals (
    scan_id       UUID PRIMARY KEY REFERENCES red_agent_scans(id) ON DELETE CASCADE,
    state         TEXT NOT NULL CHECK (state IN ('open', 'approved', 'rejected', 'timeout')),
    reason        TEXT NOT NULL,
    requested_by  TEXT NOT NULL,
    resolved_by   TEXT,
    opened_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at   TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_approvals_state ON red_agent_approvals (state);
