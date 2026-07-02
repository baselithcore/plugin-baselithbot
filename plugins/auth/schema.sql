-- Auth Plugin Database Schema
-- PostgreSQL tables for authentication

-- Users table
CREATE TABLE IF NOT EXISTS auth_users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE,  -- Optional username for login
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    roles TEXT[] NOT NULL DEFAULT ARRAY['user'],
    mfa_secret VARCHAR(255),
    mfa_enabled BOOLEAN DEFAULT FALSE,
    is_active BOOLEAN DEFAULT TRUE,
    allowed_tabs TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    last_login TIMESTAMPTZ,
    failed_login_attempts INTEGER DEFAULT 0,
    locked_until TIMESTAMPTZ
);

-- Indexes for users
CREATE INDEX IF NOT EXISTS idx_auth_users_username ON auth_users(username) WHERE username IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_auth_users_email ON auth_users(email);
CREATE INDEX IF NOT EXISTS idx_auth_users_active ON auth_users(is_active) WHERE is_active = TRUE;

-- MFA Backup codes
CREATE TABLE IF NOT EXISTS auth_mfa_backup_codes (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth_users(id) ON DELETE CASCADE,
    code_hash VARCHAR(64) NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_backup_codes_user ON auth_mfa_backup_codes(user_id);

-- Short-lived MFA challenge tokens (login temp tokens + forced-enrollment tokens).
-- Shared across uvicorn workers so a challenge minted on one worker can be
-- verified on another (multi-worker / WEB_CONCURRENCY>1 deployments). Rows are
-- short-lived and reaped by expiry; an in-memory tier still fronts this table.
CREATE TABLE IF NOT EXISTS auth_mfa_challenges (
    token_hash VARCHAR(64) PRIMARY KEY,
    user_id UUID REFERENCES auth_users(id) ON DELETE CASCADE,
    purpose VARCHAR(32) NOT NULL,
    data JSONB NOT NULL DEFAULT '{}'::jsonb,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_auth_mfa_challenges_expires ON auth_mfa_challenges(expires_at);

-- Refresh tokens for session management
CREATE TABLE IF NOT EXISTS auth_refresh_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth_users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON auth_refresh_tokens(user_id);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash ON auth_refresh_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_refresh_tokens_expires ON auth_refresh_tokens(expires_at) 
    WHERE revoked_at IS NULL;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_auth_users_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for updated_at
DROP TRIGGER IF EXISTS trigger_auth_users_updated_at ON auth_users;
CREATE TRIGGER trigger_auth_users_updated_at
    BEFORE UPDATE ON auth_users
    FOR EACH ROW
    EXECUTE FUNCTION update_auth_users_updated_at();

-- Audit log for admin actions
CREATE TABLE IF NOT EXISTS auth_audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action VARCHAR(50) NOT NULL,
    actor_id UUID NOT NULL,
    target_id UUID,
    details JSONB,
    ip_address VARCHAR(45),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_action ON auth_audit_log(action);
CREATE INDEX IF NOT EXISTS idx_audit_log_actor ON auth_audit_log(actor_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_target ON auth_audit_log(target_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_created ON auth_audit_log(created_at DESC);

-- WebAuthn credentials for passwordless authentication
CREATE TABLE IF NOT EXISTS auth_webauthn_credentials (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth_users(id) ON DELETE CASCADE,
    credential_id BYTEA NOT NULL UNIQUE,
    public_key BYTEA NOT NULL,
    sign_count INTEGER DEFAULT 0,
    transports TEXT[],
    aaguid BYTEA,
    name VARCHAR(100),  -- User-friendly name (e.g., "iPhone 15 Pro")
    created_at TIMESTAMPTZ DEFAULT NOW(),
    last_used TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_webauthn_credentials_user ON auth_webauthn_credentials(user_id);
CREATE INDEX IF NOT EXISTS idx_webauthn_credentials_credential_id ON auth_webauthn_credentials(credential_id);
CREATE INDEX IF NOT EXISTS idx_webauthn_credentials_last_used ON auth_webauthn_credentials(last_used DESC);

-- Cross-worker WebAuthn challenge store (registration + authentication). The
-- previous in-process dict broke passkeys under WEB_CONCURRENCY>1 and never
-- expired abandoned challenges; this shared tier is single-use (popped on
-- verify) with a server-side TTL.
CREATE TABLE IF NOT EXISTS auth_webauthn_challenges (
    challenge_key TEXT PRIMARY KEY,
    challenge BYTEA NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_auth_webauthn_challenges_expires ON auth_webauthn_challenges(expires_at);

-- =============================================================================
-- RBAC: granular permissions, custom roles, role/user assignments, tab policy.
-- Additive layer on top of the legacy auth_users.roles[] column (compat shim):
-- system roles are mirrored here so require_roles() keeps working unchanged.
-- =============================================================================

-- Permission catalog. Slug is "resource.action" or the dynamic tab form
-- "tab:<plugin>:<tab_id>". The wildcard slug '*' grants everything.
CREATE TABLE IF NOT EXISTS auth_permissions (
    slug VARCHAR(180) PRIMARY KEY,
    description TEXT DEFAULT '',
    category VARCHAR(80) DEFAULT 'general',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Roles. System roles (is_system) mirror AuthRole enum values by slug;
-- custom roles are admin-defined.
CREATE TABLE IF NOT EXISTS auth_roles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(80) UNIQUE NOT NULL,
    name VARCHAR(120) NOT NULL,
    description TEXT DEFAULT '',
    is_system BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Role -> permission (M:N).
CREATE TABLE IF NOT EXISTS auth_role_permissions (
    role_id UUID REFERENCES auth_roles(id) ON DELETE CASCADE,
    permission_slug VARCHAR(180) REFERENCES auth_permissions(slug) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_slug)
);

CREATE INDEX IF NOT EXISTS idx_auth_role_perms_role ON auth_role_permissions(role_id);

-- User -> custom role (M:N). System roles stay in auth_users.roles[] for compat.
CREATE TABLE IF NOT EXISTS auth_user_roles (
    user_id UUID REFERENCES auth_users(id) ON DELETE CASCADE,
    role_id UUID REFERENCES auth_roles(id) ON DELETE CASCADE,
    granted_at TIMESTAMPTZ DEFAULT NOW(),
    granted_by UUID,
    PRIMARY KEY (user_id, role_id)
);

CREATE INDEX IF NOT EXISTS idx_auth_user_roles_user ON auth_user_roles(user_id);

-- Per-plugin-tab access policy. Default-allow: a tab with no row (or
-- restricted=FALSE) is visible to every authenticated user (backward
-- compatible). When restricted=TRUE, access requires the tab:<plugin>:<id>
-- permission (admin / wildcard always allowed).
CREATE TABLE IF NOT EXISTS auth_tab_policy (
    plugin VARCHAR(120) NOT NULL,
    tab_id VARCHAR(160) NOT NULL,
    label VARCHAR(200) DEFAULT '',
    restricted BOOLEAN DEFAULT FALSE,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (plugin, tab_id)
);

-- Groups: bundle users and assign roles in bulk (wikigen-style). A user's
-- effective permissions are the union of their direct roles and the roles of
-- every group they belong to.
CREATE TABLE IF NOT EXISTS auth_groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(80) UNIQUE NOT NULL,
    name VARCHAR(120) NOT NULL,
    description TEXT DEFAULT '',
    is_system BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS auth_group_members (
    group_id UUID REFERENCES auth_groups(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth_users(id) ON DELETE CASCADE,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    added_by UUID,
    PRIMARY KEY (group_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_auth_group_members_user ON auth_group_members(user_id);

CREATE TABLE IF NOT EXISTS auth_group_roles (
    group_id UUID REFERENCES auth_groups(id) ON DELETE CASCADE,
    role_id UUID REFERENCES auth_roles(id) ON DELETE CASCADE,
    PRIMARY KEY (group_id, role_id)
);

CREATE INDEX IF NOT EXISTS idx_auth_group_roles_group ON auth_group_roles(group_id);

-- =============================================================================
-- ENTERPRISE EXTENSIONS (additive; safe to run repeatedly)
-- Account lifecycle, self-service recovery, login/security history, API keys,
-- invitations, and SSO (OIDC/SAML) federation.
-- =============================================================================

-- Account lifecycle + security metadata on the user record.
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN DEFAULT FALSE;
-- Last accepted TOTP time-step, for single-use / replay rejection (NIST 800-63B).
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS mfa_last_totp_step BIGINT;
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS status VARCHAR(20) DEFAULT 'active';
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMPTZ;
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS last_login_ip VARCHAR(45);
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS full_name VARCHAR(160);

-- Single-use, time-limited tokens for password reset, email verification, and
-- invitation acceptance. `purpose` discriminates the flow.
CREATE TABLE IF NOT EXISTS auth_recovery_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth_users(id) ON DELETE CASCADE,
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    purpose VARCHAR(30) NOT NULL,  -- password_reset | email_verify | invite
    expires_at TIMESTAMPTZ NOT NULL,
    used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_recovery_tokens_hash ON auth_recovery_tokens(token_hash);
CREATE INDEX IF NOT EXISTS idx_recovery_tokens_user ON auth_recovery_tokens(user_id);

-- Per-attempt login & security activity history (success and failure), used for
-- the self-service "security activity" view and risk/anomaly assessment.
CREATE TABLE IF NOT EXISTS auth_login_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth_users(id) ON DELETE CASCADE,
    event VARCHAR(40) NOT NULL,  -- login_success | login_failure | mfa_challenge | passkey | sso | password_reset
    ip_address VARCHAR(45),
    user_agent TEXT,
    location VARCHAR(120),
    risk_score INTEGER DEFAULT 0,
    method VARCHAR(30) DEFAULT 'password',  -- password | mfa | passkey | sso | api_key
    success BOOLEAN DEFAULT TRUE,
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_login_history_user ON auth_login_history(user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_login_history_created ON auth_login_history(created_at DESC);

-- Personal Access Tokens / service API keys. Only the SHA-256 hash is stored;
-- `prefix` is a short non-secret lookup/display fragment.
CREATE TABLE IF NOT EXISTS auth_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES auth_users(id) ON DELETE CASCADE,
    name VARCHAR(120) NOT NULL,
    prefix VARCHAR(16) NOT NULL,
    key_hash VARCHAR(64) NOT NULL UNIQUE,
    scopes TEXT[] DEFAULT ARRAY[]::TEXT[],
    expires_at TIMESTAMPTZ,
    last_used_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    created_by UUID
);

CREATE INDEX IF NOT EXISTS idx_api_keys_user ON auth_api_keys(user_id);
CREATE INDEX IF NOT EXISTS idx_api_keys_hash ON auth_api_keys(key_hash) WHERE revoked_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_api_keys_prefix ON auth_api_keys(prefix);

-- Admin-issued invitations (email-based onboarding instead of admin-set passwords).
CREATE TABLE IF NOT EXISTS auth_invitations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL,
    roles TEXT[] NOT NULL DEFAULT ARRAY['user'],
    token_hash VARCHAR(64) NOT NULL UNIQUE,
    invited_by UUID,
    expires_at TIMESTAMPTZ NOT NULL,
    accepted_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_invitations_email ON auth_invitations(email);
CREATE INDEX IF NOT EXISTS idx_invitations_hash ON auth_invitations(token_hash);

-- SSO identity providers (OIDC / SAML 2.0), admin-configured at runtime.
-- Secrets (client_secret, SAML SP private key) are stored encrypted-at-rest.
CREATE TABLE IF NOT EXISTS auth_sso_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(60) UNIQUE NOT NULL,
    name VARCHAR(120) NOT NULL,
    protocol VARCHAR(10) NOT NULL,  -- oidc | saml
    enabled BOOLEAN DEFAULT TRUE,
    config JSONB NOT NULL DEFAULT '{}'::jsonb,  -- non-secret settings
    secret_enc TEXT,  -- encrypted client_secret / SP key
    default_roles TEXT[] DEFAULT ARRAY['user'],
    auto_provision BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Links a federated identity (provider + subject) to a local user account.
CREATE TABLE IF NOT EXISTS auth_sso_identities (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    provider_id UUID REFERENCES auth_sso_providers(id) ON DELETE CASCADE,
    user_id UUID REFERENCES auth_users(id) ON DELETE CASCADE,
    subject VARCHAR(255) NOT NULL,  -- IdP "sub" / NameID
    email VARCHAR(255),
    last_login TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE (provider_id, subject)
);

CREATE INDEX IF NOT EXISTS idx_sso_identities_user ON auth_sso_identities(user_id);

-- =============================================================================
-- MFA ENFORCEMENT POLICY (additive; safe to run repeatedly)
-- Mandatory two-factor can be required globally, per group, or per user. The
-- effective requirement for a user is the OR of all three. Enforced at login:
-- a required-but-unenrolled user is forced through enrollment before a session
-- is issued.
-- =============================================================================
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS mfa_required BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE auth_groups ADD COLUMN IF NOT EXISTS mfa_required BOOLEAN NOT NULL DEFAULT FALSE;

-- Singleton row holding org-wide security toggles (id is pinned to 1).
CREATE TABLE IF NOT EXISTS auth_security_policy (
    id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    mfa_required_all BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
INSERT INTO auth_security_policy (id, mfa_required_all)
VALUES (1, FALSE) ON CONFLICT (id) DO NOTHING;

-- =============================================================================
-- MULTI-TENANCY: tenants + user→tenant membership (additive; safe to re-run)
-- Identity-derived tenancy: a user's access-token `tenant_id` claim is resolved
-- from their membership (see plugins/auth/tenancy.py). With NO membership a user
-- falls back to a personal tenant (tenant_id == user_id) — so existing installs
-- are unchanged until an admin provisions tenants and assigns members.
-- =============================================================================
CREATE TABLE IF NOT EXISTS auth_tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    slug VARCHAR(80) UNIQUE NOT NULL,
    name VARCHAR(160) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'active',  -- active | suspended
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Membership: which users belong to which tenants, with a per-tenant role and a
-- single default tenant per user (the one their token lands on at login).
CREATE TABLE IF NOT EXISTS auth_user_tenants (
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    tenant_id UUID NOT NULL REFERENCES auth_tenants(id) ON DELETE CASCADE,
    role VARCHAR(40) NOT NULL DEFAULT 'member',  -- member | admin (tenant-scoped)
    is_default BOOLEAN NOT NULL DEFAULT FALSE,
    added_at TIMESTAMPTZ DEFAULT NOW(),
    added_by UUID,
    PRIMARY KEY (user_id, tenant_id)
);

CREATE INDEX IF NOT EXISTS idx_auth_user_tenants_user ON auth_user_tenants(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_user_tenants_tenant ON auth_user_tenants(tenant_id);
-- At most one default tenant per user.
CREATE UNIQUE INDEX IF NOT EXISTS uq_auth_user_tenants_default
    ON auth_user_tenants(user_id) WHERE is_default;

-- =============================================================================
-- LLM COST GOVERNANCE (additive; safe to run repeatedly)
-- A monthly per-user spend cap, resolvable globally, per group, or per user.
-- The effective cap is the MOST SPECIFIC that is set: user > group > global
-- (NULL inherits the level below). Spend is metered per user per calendar month.
-- All money is stored as integer MICRO-USD (1 USD = 1_000_000) for exact maths.
-- =============================================================================
ALTER TABLE auth_users ADD COLUMN IF NOT EXISTS monthly_cap_micros BIGINT;
ALTER TABLE auth_groups ADD COLUMN IF NOT EXISTS monthly_cap_micros BIGINT;

-- Singleton row: global default cap + the warn threshold + enforcement toggle.
CREATE TABLE IF NOT EXISTS auth_cost_policy (
    id SMALLINT PRIMARY KEY DEFAULT 1 CHECK (id = 1),
    monthly_cap_micros BIGINT,                 -- NULL = unlimited by default
    warn_threshold_pct SMALLINT NOT NULL DEFAULT 80
        CHECK (warn_threshold_pct BETWEEN 1 AND 100),
    enforce BOOLEAN NOT NULL DEFAULT TRUE,     -- hard-block at 100% when true
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
INSERT INTO auth_cost_policy (id) VALUES (1) ON CONFLICT (id) DO NOTHING;

-- Per-user, per-month usage aggregate. `period` is the first day of the month.
CREATE TABLE IF NOT EXISTS auth_llm_usage (
    user_id UUID NOT NULL REFERENCES auth_users(id) ON DELETE CASCADE,
    period DATE NOT NULL,                       -- e.g. 2026-06-01
    spend_micros BIGINT NOT NULL DEFAULT 0,
    prompt_tokens BIGINT NOT NULL DEFAULT 0,
    completion_tokens BIGINT NOT NULL DEFAULT 0,
    request_count INTEGER NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (user_id, period)
);
CREATE INDEX IF NOT EXISTS idx_auth_llm_usage_period ON auth_llm_usage(period);

-- =============================================================================
-- PER-PLUGIN TENANCY OVERRIDE (additive; safe to run repeatedly)
-- An operator may override a plugin's manifest-declared `tenancy` at runtime
-- (`shared` = 1 tenant/N users, deployment-derived; `personal` = 1 user/1
-- tenant). A present row overrides the manifest; absent = inherit the manifest.
-- `updated_by` is stored as free text (not an FK) so a non-UUID actor — an API
-- key, an impersonation token — never fails the write or breaks on user delete.
-- =============================================================================
CREATE TABLE IF NOT EXISTS auth_plugin_tenancy_override (
    plugin_name TEXT PRIMARY KEY,
    mode TEXT NOT NULL CHECK (mode IN ('shared', 'personal')),
    updated_by TEXT,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
