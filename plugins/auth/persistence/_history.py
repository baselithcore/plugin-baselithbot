"""Login & security activity history persistence."""

import json
import uuid
from typing import Any, Dict, List, Optional

from psycopg.rows import dict_row

from core.db.connection import get_connection, get_cursor
from core.observability.logging import get_logger

logger = get_logger(__name__)


class HistoryPersistenceMixin:
    """Append-only login / security activity log."""

    def record_login_event(
        self,
        user_id: Optional[str],
        event: str,
        *,
        success: bool = True,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        location: Optional[str] = None,
        risk_score: int = 0,
        method: str = "password",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a single login/security event (best-effort)."""
        try:
            with get_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO auth_login_history
                            (id, user_id, event, ip_address, user_agent, location,
                             risk_score, method, success, details)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            str(uuid.uuid4()),
                            user_id,
                            event,
                            ip_address,
                            user_agent,
                            location,
                            risk_score,
                            method,
                            success,
                            json.dumps(details) if details else None,
                        ),
                    )
                conn.commit()
            if user_id and success and event == "login_success" and ip_address:
                self._set_last_login_ip(user_id, ip_address)
        except Exception as exc:  # pragma: no cover - history must never block auth
            logger.warning("Failed to record login event: %s", exc)

    def _set_last_login_ip(self, user_id: str, ip_address: str) -> None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE auth_users SET last_login_ip = %s WHERE id = %s",
                    (ip_address, user_id),
                )
            conn.commit()

    def get_login_history(
        self, user_id: str, limit: int = 50, offset: int = 0
    ) -> List[dict]:
        """Return recent login/security events for a user."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id, event, ip_address, user_agent, location, risk_score,
                       method, success, details, created_at
                FROM auth_login_history
                WHERE user_id = %s
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s
                """,
                (user_id, limit, offset),
            )
            return [dict(r) for r in cur.fetchall()]

    def recent_failed_ips(self, user_id: str, window_minutes: int = 1440) -> List[str]:
        """Distinct successful-login IPs in a window (for anomaly checks)."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT DISTINCT ip_address FROM auth_login_history
                WHERE user_id = %s AND success = TRUE AND ip_address IS NOT NULL
                  AND created_at > NOW() - (%s || ' minutes')::interval
                """,
                (user_id, window_minutes),
            )
            return [r["ip_address"] for r in cur.fetchall() if r["ip_address"]]
