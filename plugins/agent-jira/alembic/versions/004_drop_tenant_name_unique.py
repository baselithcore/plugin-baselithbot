"""Drop UNIQUE constraint on tenants.name.

Lo slug è già l'identificatore univoco; due organizzazioni distinte
possono legittimamente avere lo stesso display name.

Revision ID: 004
Revises: 003
Create Date: 2026-04-14
"""

from typing import Sequence, Union

from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE tenants DROP CONSTRAINT IF EXISTS tenants_name_key")


def downgrade() -> None:
    op.execute("ALTER TABLE tenants ADD CONSTRAINT tenants_name_key UNIQUE (name)")
