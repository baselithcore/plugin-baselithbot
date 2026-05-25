"""Setup invitations + force password change flag.

Aggiunge il flow "invitation token" raccomandato per il bootstrap
maintainer→cliente:

- ``setup_invitations`` — token signed, hash-only in DB, single-use,
  time-bound. Token plain solo nel canale fuori-banda (CLI banner /
  email out-of-app).
- ``users.password_must_change`` — flag baseline: forza il cambio
  password al primo login. Settato dal bootstrap autostart legacy
  (password generata) e da future password-reset flows. Per
  invitation accept resta False (utente sceglie subito la password).

Pattern allineato a NIST SP 800-63B "credential rotation": niente
password fissa, ogni credenziale è scoped + time-limited + revocabile.

Revision ID: 009_invitations_and_password_change
Revises: 008_rbac_hierarchy
Create Date: 2026-05-02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "009_invitations_pwchange"
down_revision: str | None = "008_rbac_hierarchy"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Force password change baseline. Default FALSE — utenti esistenti
    # non vengono forzati al cambio retroattivamente. Settato a TRUE
    # solo da bootstrap autostart e password reset admin-driven.
    op.execute(
        """
        ALTER TABLE users
        ADD COLUMN IF NOT EXISTS password_must_change BOOLEAN NOT NULL DEFAULT FALSE
        """
    )

    # Setup invitations. token_hash è SHA-256 del token plain (mai
    # salvato in chiaro). Single-use: ``used_at`` non NULL ⇒ consumato.
    # ``role_slug`` è opzionale: NULL = ruolo determinato a accept time
    # da contesto (es. "primo invite di sistema" → superuser).
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS setup_invitations (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            token_hash TEXT NOT NULL UNIQUE,
            email CITEXT NOT NULL,
            role_slug TEXT NULL,
            tenant_slug TEXT NULL,
            display_name TEXT NOT NULL DEFAULT '',
            note TEXT NOT NULL DEFAULT '',
            expires_at TIMESTAMPTZ NOT NULL,
            used_at TIMESTAMPTZ NULL,
            created_by UUID NULL REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_setup_invitations_email ON setup_invitations (email)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_setup_invitations_expires "
        "ON setup_invitations (expires_at) "
        "WHERE used_at IS NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_setup_invitations_expires")
    op.execute("DROP INDEX IF EXISTS idx_setup_invitations_email")
    op.execute("DROP TABLE IF EXISTS setup_invitations")
    op.execute("ALTER TABLE users DROP COLUMN IF EXISTS password_must_change")
