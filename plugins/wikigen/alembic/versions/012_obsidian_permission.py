"""Add `obsidian.open` permission and grant to all system roles.

Lets end users follow ``obsidian://...`` links emitted by the wiki page
viewer. The URI is also gated server-side by the per-tenant
``.obsidian-init.json`` flag set by ``POST /api/admin/tenants/{name}/obsidian/init``;
this permission is the user-side half of that two-key gate.

Granted to ``superuser``, ``admin``, ``moderator``, ``user`` so any
authenticated end user with at least the base wiki role can open the
desktop client. Anonymous callers (auth disabled / not logged in) never
see ``obsidian.open`` in their permission set, so the URI stays hidden.

Revision ID: 012_obsidian_permission
Revises: 011_audit_role_hardening
Create Date: 2026-05-02
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "012_obsidian_permission"
down_revision: str | None = "011_audit_role_hardening"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PERMISSION_SLUG = "obsidian.open"
PERMISSION_DESC = "Aprire pagine wiki nel client Obsidian (URI obsidian://)"

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
    grant = sa.text(
        """
        INSERT INTO role_permissions (role_id, permission_slug)
        SELECT id, :perm FROM roles
        WHERE slug = :slug AND tenant_id IS NULL AND is_system = TRUE
        ON CONFLICT DO NOTHING
        """
    )
    for slug in GRANT_TO_SLUGS:
        bind.execute(grant, {"perm": PERMISSION_SLUG, "slug": slug})


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
