"""Feedback triage workflow — status / tags / resolution + ``feedback.triage`` perm.

Aggiunge a ``feedback`` (mig 005) le colonne necessarie al workflow
moderazione moderno (pattern Helicone / LangSmith / PostHog / Linear):

- ``status`` enum ``open|triaged|resolved|dismissed`` — stato triage.
  ``open`` (default) per backward-compat dei record pre-018.
- ``tags TEXT[]`` — vocabolario libero ma con tag-suggeriti FE-side:
  ``hallucination`` / ``missing_citation`` / ``stale_doc`` /
  ``out_of_scope`` / ``wrong_source`` / ``incomplete``. GIN index per
  filtri ``tags @> ARRAY['hallucination']`` efficiente.
- ``resolution_note`` — testo libero del moderatore (es. "Aggiornato
  doc X, ri-ingestato").
- ``resolved_by_user_id`` (FK users SET NULL) + ``resolved_at`` —
  audit del chi/quando ha chiuso il record.

Aggiunge anche il permesso ``feedback.triage`` (separato da
``feedback.delete``): triage è workflow non distruttivo, va a
moderator+admin senza dover toccare delete. Seedato a:

- ``moderator``  → cura quotidiana del feedback
- ``admin``      → tutte le operazioni moderazione
- ``superuser``  → privilegio omnicomprensivo

Niente RLS aggiuntiva — la tabella eredita le policy di mig 006
(``tenant_id`` already filtered).

Revision ID: 018_feedback_triage
Revises: 017_embeds
Create Date: 2026-05-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "018_feedback_triage"
down_revision: str | None = "017_embeds"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PERMISSION_SLUG = "feedback.triage"
PERMISSION_DESC = "Triage feedback (status, tag, note risoluzione)"
GRANT_TO_SLUGS = ("superuser", "admin", "moderator")


def upgrade() -> None:
    # status: enum-via-CHECK invece di ENUM type — più facile da
    # estendere (basta cambiare la CHECK), zero ALTER TYPE pesante.
    op.execute(
        """
        ALTER TABLE feedback
            ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'open'
                CHECK (status IN ('open', 'triaged', 'resolved', 'dismissed')),
            ADD COLUMN IF NOT EXISTS tags TEXT[] NOT NULL DEFAULT ARRAY[]::TEXT[],
            ADD COLUMN IF NOT EXISTS resolution_note TEXT,
            ADD COLUMN IF NOT EXISTS resolved_by_user_id UUID
                REFERENCES users(id) ON DELETE SET NULL,
            ADD COLUMN IF NOT EXISTS resolved_at TIMESTAMPTZ
        """
    )
    # Index parziale su status: ``open`` è lo stato più filtrato (le
    # dashboard di triage mostrano "cosa devo guardare ora"), niente
    # senso indicizzare i resolved che crescono linearmente.
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_feedback_status_open "
        "ON feedback (tenant_id, created_at DESC) WHERE status = 'open'"
    )
    # GIN per filtri "tags contiene X".
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_feedback_tags "
        "ON feedback USING GIN (tags)"
    )

    bind = op.get_bind()
    bind.execute(
        sa.text(
            "INSERT INTO permissions (slug, description) VALUES (:slug, :desc) "
            "ON CONFLICT (slug) DO UPDATE SET description = EXCLUDED.description"
        ),
        {"slug": PERMISSION_SLUG, "desc": PERMISSION_DESC},
    )
    grant_stmt = sa.text(
        """
        INSERT INTO role_permissions (role_id, permission_slug)
        SELECT id, :perm FROM roles
        WHERE slug = :slug AND tenant_id IS NULL AND is_system = TRUE
        ON CONFLICT DO NOTHING
        """
    )
    for role_slug in GRANT_TO_SLUGS:
        bind.execute(grant_stmt, {"perm": PERMISSION_SLUG, "slug": role_slug})


def downgrade() -> None:
    bind = op.get_bind()
    bind.execute(
        sa.text("DELETE FROM role_permissions WHERE permission_slug = :slug"),
        {"slug": PERMISSION_SLUG},
    )
    bind.execute(
        sa.text("DELETE FROM permissions WHERE slug = :slug"),
        {"slug": PERMISSION_SLUG},
    )
    op.execute("DROP INDEX IF EXISTS idx_feedback_tags")
    op.execute("DROP INDEX IF EXISTS idx_feedback_status_open")
    op.execute(
        """
        ALTER TABLE feedback
            DROP COLUMN IF EXISTS resolved_at,
            DROP COLUMN IF EXISTS resolved_by_user_id,
            DROP COLUMN IF EXISTS resolution_note,
            DROP COLUMN IF EXISTS tags,
            DROP COLUMN IF EXISTS status
        """
    )
