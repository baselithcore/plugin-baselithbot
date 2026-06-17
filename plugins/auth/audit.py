"""
Auth Plugin Audit Logging.

Provides audit logging for admin actions.
"""

from core.observability.logging import get_logger
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from psycopg.rows import dict_row
from psycopg.types.json import Json

from core.db.connection import get_connection, get_cursor

logger = get_logger(__name__)


# Audit action types
class AuditAction:
    """Audit action type constants."""

    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    USER_PASSWORD_RESET = "user.password_reset"
    USER_UNLOCKED = "user.unlocked"
    USER_SESSIONS_REVOKED = "user.sessions_revoked"
    USER_MFA_DISABLED = "user.mfa_disabled"
    USER_INVITED = "user.invited"
    INVITATION_REVOKED = "user.invitation_revoked"
    USER_STATUS_CHANGED = "user.status_changed"
    # RBAC administration
    ROLE_CREATED = "rbac.role_created"
    ROLE_DELETED = "rbac.role_deleted"
    ROLE_PERMISSIONS_CHANGED = "rbac.role_permissions_changed"
    USER_ROLE_ASSIGNED = "rbac.user_role_assigned"
    USER_ROLE_REVOKED = "rbac.user_role_revoked"
    TAB_POLICY_CHANGED = "rbac.tab_policy_changed"
    GROUP_CREATED = "rbac.group_created"
    GROUP_DELETED = "rbac.group_deleted"
    GROUP_MEMBER_ADDED = "rbac.group_member_added"
    GROUP_MEMBER_REMOVED = "rbac.group_member_removed"
    GROUP_ROLE_CHANGED = "rbac.group_role_changed"


@dataclass
class AuditEntry:
    """Audit log entry."""

    id: str
    action: str
    actor_id: str
    target_id: Optional[str]
    details: Dict[str, Any]
    ip_address: Optional[str]
    created_at: datetime

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "id": self.id,
            "action": self.action,
            "actor_id": self.actor_id,
            "target_id": self.target_id,
            "details": self.details,
            "ip_address": self.ip_address,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


def _row_to_audit_entry(row: dict) -> AuditEntry:
    """Convert database row to AuditEntry object."""
    return AuditEntry(
        id=str(row["id"]),
        action=row["action"],
        actor_id=str(row["actor_id"]),
        target_id=str(row["target_id"]) if row.get("target_id") else None,
        details=row.get("details") or {},
        ip_address=row.get("ip_address"),
        created_at=row.get("created_at", datetime.now(timezone.utc)),
    )


class AuditLogger:
    """Audit logger for admin actions."""

    def log(
        self,
        action: str,
        actor_id: str,
        target_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
    ) -> str:
        """
        Log an audit event.

        Args:
            action: Action type (e.g., "user.created")
            actor_id: ID of the user performing the action
            target_id: ID of the affected user (if applicable)
            details: Additional context about the action
            ip_address: Client IP address

        Returns:
            ID of the created audit entry
        """
        entry_id = str(uuid.uuid4())

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO auth_audit_log
                        (id, action, actor_id, target_id, details, ip_address)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    """,
                    (
                        entry_id,
                        action,
                        actor_id,
                        target_id,
                        Json(details) if details is not None else None,
                        ip_address,
                    ),
                )
            conn.commit()

        logger.info(
            f"Audit: {action} by {actor_id}" + (f" on {target_id}" if target_id else "")
        )
        return entry_id

    def get_entries(
        self,
        action: Optional[str] = None,
        actor_id: Optional[str] = None,
        target_id: Optional[str] = None,
        page: int = 1,
        limit: int = 50,
    ) -> tuple[List[AuditEntry], int]:
        """
        Get audit log entries with optional filters.

        Args:
            action: Filter by action type
            actor_id: Filter by actor
            target_id: Filter by target
            page: Page number (1-indexed)
            limit: Entries per page

        Returns:
            Tuple of (entries, total_count)
        """
        conditions = []
        params: List[Any] = []

        if action:
            conditions.append("action = %s")
            params.append(action)

        if actor_id:
            conditions.append("actor_id = %s")
            params.append(actor_id)

        if target_id:
            conditions.append("target_id = %s")
            params.append(target_id)

        where_clause = " AND ".join(conditions) if conditions else "TRUE"

        with get_cursor(row_factory=dict_row) as cur:
            # Get total count
            cur.execute(
                f"SELECT COUNT(*) as count FROM auth_audit_log WHERE {where_clause}",  # nosec B608
                params,
            )
            row = cur.fetchone()
            total = row["count"] if row else 0

            # Get paginated entries
            offset = (page - 1) * limit
            cur.execute(
                f"""
                SELECT * FROM auth_audit_log
                WHERE {where_clause}
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,  # nosec B608
                params + [limit, offset],
            )
            rows = cur.fetchall()

        return [_row_to_audit_entry(row) for row in rows], total


# Global instance
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    """Get or create the global audit logger instance."""
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
