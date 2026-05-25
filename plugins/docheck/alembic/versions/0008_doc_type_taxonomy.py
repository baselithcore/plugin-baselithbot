"""ADR-0011: doc_type on documents + applicable_doc_types/frameworks on policies

Revision ID: 0008
Revises: 0007
Create Date: 2026-05-03
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("documents") as batch:
        batch.add_column(sa.Column("doc_type", sa.String, nullable=True))
        batch.add_column(sa.Column("doc_type_confidence", sa.Float, nullable=True))

    with op.batch_alter_table("policies") as batch:
        batch.add_column(sa.Column("applicable_doc_types", sa.Text, nullable=True))
        batch.add_column(sa.Column("frameworks", sa.Text, nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("policies") as batch:
        batch.drop_column("frameworks")
        batch.drop_column("applicable_doc_types")

    with op.batch_alter_table("documents") as batch:
        batch.drop_column("doc_type_confidence")
        batch.drop_column("doc_type")
