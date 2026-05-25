"""postgres row-level security policies (multi-tenant gate)

Activated only on Postgres backend. SQLite skips silently.
Each scoped table gets RLS enabled + USING/WITH CHECK policy on tenant_id matching
session GUC `app.current_tenant`.

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-03

"""

from collections.abc import Sequence

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TABLES = ["users", "documents", "policies", "reports", "audit_log"]


def _is_postgres() -> bool:
    bind = op.get_bind()
    return bind.dialect.name == "postgresql"


def upgrade() -> None:
    if not _is_postgres():
        return

    for tbl in _TABLES:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY;")
        op.execute(f"""
            CREATE POLICY tenant_isolation_{tbl} ON {tbl}
            USING (tenant_id = current_setting('app.current_tenant', true))
            WITH CHECK (tenant_id = current_setting('app.current_tenant', true));
        """)


def downgrade() -> None:
    if not _is_postgres():
        return
    for tbl in _TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_{tbl} ON {tbl};")
        op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY;")
