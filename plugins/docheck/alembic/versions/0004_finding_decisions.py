"""finding_decisions table (Workspace finding triage).

Persists per-finding user decisions (accept/reject/mute) tied to a signed report.

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-03

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "finding_decisions",
        sa.Column(
            "report_id",
            sa.String,
            sa.ForeignKey("reports.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("finding_id", sa.String, primary_key=True),
        sa.Column("decision", sa.String, nullable=False),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column("user_id", sa.String, sa.ForeignKey("users.id"), nullable=False),
        sa.Column("decided_at", sa.DateTime, nullable=False),
        sa.Column("tenant_id", sa.String, nullable=False, server_default="default"),
        sa.CheckConstraint(
            "decision IN ('accepted','rejected','muted')", name="ck_decision_kind"
        ),
    )
    op.create_index("idx_decision_report", "finding_decisions", ["report_id"])


def downgrade() -> None:
    op.drop_index("idx_decision_report", table_name="finding_decisions")
    op.drop_table("finding_decisions")
