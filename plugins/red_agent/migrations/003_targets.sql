-- Red Agent target-as-project model + finding lifecycle.
-- Promotes targets to first-class persistent entities. Scans become "runs"
-- against a target. Findings gain a triage lifecycle (open → triaged →
-- fixed/wontfix/accepted) with optional assignee and SLA due date.

CREATE TABLE IF NOT EXISTS red_agent_targets (
    id              UUID PRIMARY KEY,
    kind            TEXT NOT NULL CHECK (kind IN ('web','host','cloud','network')),
    name            TEXT NOT NULL,
    value           TEXT NOT NULL,
    environment     TEXT,
    owner           TEXT,
    tags            TEXT[] NOT NULL DEFAULT '{}',
    profile         JSONB NOT NULL DEFAULT '{}'::jsonb,
    schedule_cron   TEXT,
    scope_overrides JSONB NOT NULL DEFAULT '{}'::jsonb,
    description     TEXT,
    tenant_id       TEXT,
    created_by      TEXT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_scan_at    TIMESTAMPTZ,
    archived_at     TIMESTAMPTZ,
    UNIQUE (tenant_id, kind, value)
);

CREATE INDEX IF NOT EXISTS idx_targets_tenant ON red_agent_targets (tenant_id);
CREATE INDEX IF NOT EXISTS idx_targets_kind ON red_agent_targets (kind);
CREATE INDEX IF NOT EXISTS idx_targets_environment ON red_agent_targets (environment);
CREATE INDEX IF NOT EXISTS idx_targets_archived ON red_agent_targets (archived_at);

ALTER TABLE red_agent_scans
    ADD COLUMN IF NOT EXISTS target_id UUID REFERENCES red_agent_targets(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS idx_scans_target_id ON red_agent_scans (target_id);

-- Finding triage lifecycle. Backfill existing rows to 'open' so the UI sees a
-- consistent state. SLA due date is computed by the application layer (per
-- severity) and persisted here for query/sort convenience.
ALTER TABLE red_agent_findings
    ADD COLUMN IF NOT EXISTS state       TEXT NOT NULL DEFAULT 'open'
        CHECK (state IN ('open','triaged','fixed','wontfix','accepted')),
    ADD COLUMN IF NOT EXISTS assignee    TEXT,
    ADD COLUMN IF NOT EXISTS triaged_at  TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS due_at      TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS notes       TEXT;

CREATE INDEX IF NOT EXISTS idx_findings_state ON red_agent_findings (state);
CREATE INDEX IF NOT EXISTS idx_findings_due ON red_agent_findings (due_at);
