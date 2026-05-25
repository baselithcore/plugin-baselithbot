-- Migration: Add username field to auth_users table
-- Date: 2026-01-11
-- Description: Adds optional username field for login with username OR email

-- Add username column (nullable for backward compatibility)
ALTER TABLE auth_users
ADD COLUMN IF NOT EXISTS username VARCHAR(50) UNIQUE;

-- Create index for username lookups (partial index, only for non-null values)
CREATE INDEX IF NOT EXISTS idx_auth_users_username
ON auth_users(username)
WHERE username IS NOT NULL;

-- Add constraint to ensure username format if provided
-- Username rules: 3-50 chars, alphanumeric + underscore/dash/dot, must start with letter/number
-- Add constraint to ensure username format if provided
-- Username rules: 3-50 chars, alphanumeric + underscore/dash/dot, must start with letter/number
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'chk_username_format') THEN
        ALTER TABLE auth_users
        ADD CONSTRAINT chk_username_format
        CHECK (
            username IS NULL OR (
                username ~ '^[a-zA-Z0-9][a-zA-Z0-9._-]{2,49}$'
                AND username !~ '[._-]{2,}'  -- No consecutive special chars
                AND username !~ '^[._-]'     -- No leading special chars
                AND username !~ '[._-]$'     -- No trailing special chars
            )
        );
    END IF;
END $$;

-- Add comment
COMMENT ON COLUMN auth_users.username IS 'Optional username for login. If null, user can only login with email.';

-- Update trigger is already in place (update_auth_users_updated_at)
-- No additional triggers needed
