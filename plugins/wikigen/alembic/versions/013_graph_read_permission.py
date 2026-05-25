"""Add ``graph.read`` permission and grant to all system roles.

Gates the ``/api/graph/*`` knowledge-graph endpoints (graphify-style
PR1+PR2+PR3 surface). Pre-013 the router was completely ungated — any
caller able to reach the process could enumerate entities, relations,
communities, centrality, and exfiltrate the full graph snapshot. The
read-only nature of the endpoints does not justify the leak: entity
names often carry sensitive domain content (clinical terms, customer
names, internal product codenames).

Granted to ``superuser``, ``admin``, ``moderator``, ``user`` so any
authenticated end user with at least the base wiki role can browse
the graph (parity with ``obsidian.open`` from mig 012). Anonymous
callers never see ``graph.read`` in their permission set — the router
returns 401/403 when Postgres is ON.

Setup mode (Postgres OFF) is unaffected: the router gate short-circuits
to allow so the wizard / dev environments stay accessible.

Revision ID: 013_graph_read_permission
Revises: 012_obsidian_permission
Create Date: 2026-05-24
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "013_graph_read_permission"
down_revision: str | None = "012_obsidian_permission"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PERMISSION_SLUG = "graph.read"
PERMISSION_DESC = "Lettura grafo conoscenze (entità, relazioni, comunità)"

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
