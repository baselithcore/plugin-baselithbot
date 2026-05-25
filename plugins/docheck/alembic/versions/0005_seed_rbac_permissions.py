"""seed RBAC permissions for shipped roles

Idempotent: uses INSERT OR IGNORE so re-runs / pre-populated rows do not break.

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-03
"""

from collections.abc import Sequence

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# (role_id, resource, action)
SEED: list[tuple[str, str, str]] = [
    # admin: full access
    ("admin", "document", "read"),
    ("admin", "document", "write"),
    ("admin", "policy", "read"),
    ("admin", "policy", "write"),
    ("admin", "policy", "admin"),
    ("admin", "audit", "read"),
    ("admin", "audit", "export"),
    ("admin", "finding", "read"),
    ("admin", "finding", "write"),
    # compliance officer: author policies, run analyses
    ("compliance_officer", "document", "read"),
    ("compliance_officer", "document", "write"),
    ("compliance_officer", "policy", "read"),
    ("compliance_officer", "policy", "write"),
    ("compliance_officer", "audit", "read"),
    ("compliance_officer", "audit", "export"),
    ("compliance_officer", "finding", "read"),
    ("compliance_officer", "finding", "write"),
    # dpo: oversight + audit
    ("dpo", "document", "read"),
    ("dpo", "policy", "read"),
    ("dpo", "audit", "read"),
    ("dpo", "audit", "export"),
    ("dpo", "finding", "read"),
    # reader: read-only
    ("reader", "document", "read"),
    ("reader", "policy", "read"),
    ("reader", "finding", "read"),
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
