-- Red Agent runtime policy overrides.
-- Singleton row (id=1) holds operator-edited overlays on top of env defaults.
-- Loaded on plugin init and re-applied on every PUT /settings/scope.

CREATE TABLE IF NOT EXISTS red_agent_policy (
    id              SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    overrides       JSONB NOT NULL DEFAULT '{}'::jsonb,
    updated_by      TEXT,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
