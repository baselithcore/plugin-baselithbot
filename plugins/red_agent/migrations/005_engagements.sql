-- Red Agent engagements / campaigns.

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

ALTER TABLE red_agent_scans
    ADD COLUMN IF NOT EXISTS engagement_id uuid
    REFERENCES red_agent_engagements(id) ON DELETE SET NULL;

CREATE INDEX IF NOT EXISTS red_agent_engagements_tenant_idx
    ON red_agent_engagements(tenant_id);
CREATE INDEX IF NOT EXISTS red_agent_engagements_status_idx
    ON red_agent_engagements(status);
CREATE INDEX IF NOT EXISTS red_agent_engagements_archived_idx
    ON red_agent_engagements(archived_at);
CREATE INDEX IF NOT EXISTS red_agent_scans_engagement_id_idx
    ON red_agent_scans(engagement_id);
