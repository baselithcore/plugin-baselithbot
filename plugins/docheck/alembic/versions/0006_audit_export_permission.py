"""seed audit:export RBAC permission for admin/dpo

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-03
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0006"
down_revision: str | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SEED: list[tuple[str, str, str]] = [
    ("admin", "audit", "export"),
    ("dpo", "audit", "export"),
    ("compliance_officer", "audit", "export"),
]


def upgrade() -> None:
    for role_id, resource, action in SEED:
        op.execute(
            "INSERT OR IGNORE INTO permissions (role_id, resource, action) "
            f"VALUES ('{role_id}', '{resource}', '{action}');"
        )


def downgrade() -> None:
    for role_id, resource, action in SEED:
        op.execute(  # nosec B608 — static SEED values, safe from injection
            "DELETE FROM permissions WHERE role_id = "
            f"'{role_id}' AND resource = '{resource}' AND action = '{action}';"
        )
