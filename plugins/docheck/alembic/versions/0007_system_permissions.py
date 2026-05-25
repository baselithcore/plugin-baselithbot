"""seed system:read / system:admin RBAC permissions

Revision ID: 0007
Revises: 0006
Create Date: 2026-05-03
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


SEED: list[tuple[str, str, str]] = [
    ("admin", "system", "read"),
    ("admin", "system", "admin"),
    ("compliance_officer", "system", "read"),
    ("dpo", "system", "read"),
    ("reader", "system", "read"),
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
