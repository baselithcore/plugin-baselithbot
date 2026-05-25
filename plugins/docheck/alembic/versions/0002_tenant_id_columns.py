"""tenant_id columns + index (multi-tenant scaffolding)

Adds nullable `tenant_id` to scoped tables. Default 'default'.
Activated when DOCHECK_MULTITENANT_ENABLED=true; queries must filter by tenant_id.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-03

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TABLES = ["users", "documents", "policies", "reports", "audit_log"]


def upgrade() -> None:
    for tbl in _TABLES:
        op.add_column(
            tbl,
            sa.Column(
                "tenant_id",
                sa.String,
                nullable=False,
                server_default="default",
            ),
        )
        op.create_index(f"idx_{tbl}_tenant", tbl, ["tenant_id"])


def downgrade() -> None:
    for tbl in _TABLES:
        op.drop_index(f"idx_{tbl}_tenant", table_name=tbl)
        op.drop_column(tbl, "tenant_id")
