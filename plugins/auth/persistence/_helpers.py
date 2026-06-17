"""Row mapping and role (de)serialization helpers for auth persistence."""

from datetime import datetime, timezone
from typing import List, Set

from core.auth.types import AuthRole
from core.observability.logging import get_logger
from plugins.auth.models import User

logger = get_logger(__name__)


def parse_roles(roles_list: List[str]) -> Set[AuthRole]:
    """Convert database roles array to AuthRole set."""
    result = set()
    for role_str in roles_list:
        try:
            result.add(AuthRole(role_str))
        except ValueError:
            logger.warning(f"Unknown role in database: {role_str}")
    return result if result else {AuthRole.USER}


def serialize_roles(roles: Set[AuthRole]) -> List[str]:
    """Convert AuthRole set to database array."""
    return [r.value for r in roles]


def row_to_user(row: dict) -> User:
    """Convert database row to User object."""
    return User(
        id=str(row["id"]),
        email=row["email"],
        username=row.get("username"),
        password_hash=row["password_hash"],
        roles=parse_roles(row["roles"]),
        mfa_secret=row.get("mfa_secret"),
        mfa_enabled=row.get("mfa_enabled", False),
        is_active=row.get("is_active", True),
        allowed_tabs=row.get("allowed_tabs"),
        created_at=row.get("created_at", datetime.now(timezone.utc)),
        updated_at=row.get("updated_at", datetime.now(timezone.utc)),
        last_login=row.get("last_login"),
        failed_login_attempts=row.get("failed_login_attempts", 0),
        locked_until=row.get("locked_until"),
        email_verified=row.get("email_verified", False),
        status=row.get("status") or "active",
        full_name=row.get("full_name"),
        password_changed_at=row.get("password_changed_at"),
        last_login_ip=row.get("last_login_ip"),
    )
