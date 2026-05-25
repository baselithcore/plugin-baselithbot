"""seed report:export RBAC permission

Endpoints `/reports/{id}/export.md` and `/reports/{id}/export.json` require
`report:export` permission. Without this seed every role hits 403 even when
the role can read the underlying document.

Revision ID: 0009
Revises: 0008
Create Date: 2026-05-03
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Roles that may export a signed report. Mirrors `audit:export` set + reader
# (reader can already read documents/findings, exporting the same report
# in MD/JSON adds no extra disclosure).
SEED: list[tuple[str, str, str]] = [
    ("admin", "report", "export"),
    ("compliance_officer", "report", "export"),
    ("dpo", "report", "export"),
    ("reader", "report", "export"),
]


def upgrade() -> None:
    for role_id, resource, action in SEED:
        op.execute(
            "INSERT OR IGNORE INTO permissions (role_id, resource, action) "
            f"VALUES ('{role_id}', '{resource}', '{action}');"  # nosec B608
        )


def downgrade() -> None:
    for role_id, resource, action in SEED:
        op.execute(
            "DELETE FROM permissions WHERE role_id = "
            f"'{role_id}' AND resource = '{resource}' AND action = '{action}';"  # nosec B608
        )
