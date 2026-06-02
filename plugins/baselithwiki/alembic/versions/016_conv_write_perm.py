"""Add ``conversation.write`` permission for create/rename operations.

Closes audit gap: pre-016 ``POST /api/conversations`` (create),
``PATCH /api/conversations/{id}`` (rename / pin / metadata) and
``POST /api/conversations/{id}/messages`` (append turn) erano gated
solo da ``require_user`` senza un permesso granulare. La perm
``conversation.delete`` esisteva già per la rimozione — write è ora
il simmetrico richiesto per coerenza RBAC + per consentire profili
"read-only" che possono leggere le proprie chat passate ma non
crearne di nuove.

Granted by default a tutti e 4 i ruoli system (``superuser/admin/
moderator/user``) per non rompere deploy esistenti — operatori che
vogliono profili strict (es. "audit-viewer") possono revocarla
esplicitamente.

Revision ID: 016_conv_write_perm
Revises: 015_groups
Create Date: 2026-05-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "016_conv_write_perm"
down_revision: str | None = "015_groups"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PERMISSION_SLUG = "conversation.write"
PERMISSION_DESC = "Creazione e modifica delle proprie conversazioni"
GRANT_TO_SLUGS = ("superuser", "admin", "moderator", "user")


def upgrade() -> None:
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
