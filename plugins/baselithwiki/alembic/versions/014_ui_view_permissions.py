"""Add ``view.*`` permissions for home UI surface gating.

Closes the audit gap "ogni pulsante home deve essere assegnabile per
ruolo". Pre-014 several header / drawer surfaces (Settings modal, Help
shortcuts, Command palette, Sources drawer, StatusPill, Edition
selector) were always visible to any authenticated user — admin had no
way to compose a stripped-down profile (es. "kiosk" user with chat
only).

Pattern Notion / Linear / GitHub: every UI surface that does NOT have
a natural CRUD permission gets a ``view.<surface>`` perm. Surfaces
that already map to CRUD perms reuse them:

- Memories drawer → ``memory.read``
- Graph tab → ``graph.read``
- Upload → ``ingest.run``
- Wizard → ``admin.scaffold``
- Admin users → ``admin.user.manage``
- Obsidian button → ``obsidian.open``

Granted by default to every system role (``superuser/admin/moderator/user``)
so existing deploys see no behavior change — operators must explicitly
revoke a ``view.*`` perm from a role to hide the surface.

Revision ID: 014_ui_view_permissions
Revises: 013_graph_read_permission
Create Date: 2026-05-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "014_ui_view_permissions"
down_revision: str | None = "013_graph_read_permission"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PERMISSIONS: tuple[tuple[str, str], ...] = (
    ("view.settings", "Aprire il pannello Impostazioni"),
    ("view.help", "Aprire il pannello Scorciatoie / Help"),
    ("view.command_palette", "Aprire la tavolozza comandi (⌘/)"),
    ("view.sources", "Aprire il pannello Fonti / citazioni"),
    ("view.status", "Vedere l'indicatore di stato del deploy"),
    ("view.editions", "Vedere il selettore di edizione / dominio"),
)

GRANT_TO_SLUGS = ("superuser", "admin", "moderator", "user")


def upgrade() -> None:
    bind = op.get_bind()
    perm_stmt = sa.text(
        "INSERT INTO permissions (slug, description) VALUES (:slug, :desc) "
        "ON CONFLICT (slug) DO UPDATE SET description = EXCLUDED.description"
    )
    grant_stmt = sa.text(
        """
        INSERT INTO role_permissions (role_id, permission_slug)
        SELECT id, :perm FROM roles
        WHERE slug = :slug AND tenant_id IS NULL AND is_system = TRUE
        ON CONFLICT DO NOTHING
        """
    )
    for slug, desc in PERMISSIONS:
        bind.execute(perm_stmt, {"slug": slug, "desc": desc})
        for role in GRANT_TO_SLUGS:
            bind.execute(grant_stmt, {"perm": slug, "slug": role})


def downgrade() -> None:
    bind = op.get_bind()
    for slug, _ in PERMISSIONS:
        bind.execute(
            sa.text("DELETE FROM role_permissions WHERE permission_slug = :slug"),
            {"slug": slug},
        )
        bind.execute(
            sa.text("DELETE FROM permissions WHERE slug = :slug"),
            {"slug": slug},
        )
