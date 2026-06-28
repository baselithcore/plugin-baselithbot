"""Persistence for per-user LLM cost governance.

A monthly spend cap can be set globally, per group, or per user. The effective
cap for a user is the **most specific** one set (user > group > global; ``NULL``
inherits the level below) — collapsed into a single query for the hot path.
Spend is metered per user per calendar month. All money is integer **micro-USD**
(1 USD = 1_000_000) so accumulation is exact (sub-cent LLM calls never round to
zero). Mirrors the MFA :class:`SecurityPolicyMixin` shape.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Optional

from psycopg.rows import dict_row

from core.db.connection import get_cursor
from core.observability.logging import get_logger

logger = get_logger(__name__)


def month_period(today: Optional[date] = None) -> date:
    """First day of the current (UTC) calendar month — the usage bucket key."""
    d = today or date.today()
    return date(d.year, d.month, 1)


class CostGovernanceMixin:
    """Read/write monthly spend caps + per-user monthly usage."""

    # ----- global policy --------------------------------------------------

    def get_cost_policy(self) -> dict[str, Any]:
        """Global default cap (micro-USD, None=unlimited), warn %, enforce flag."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT monthly_cap_micros, warn_threshold_pct, enforce "
                "FROM auth_cost_policy WHERE id = 1"
            )
            row = cur.fetchone()
        if not row:
            return {
                "monthly_cap_micros": None,
                "warn_threshold_pct": 80,
                "enforce": True,
            }
        return dict(row)

    def set_cost_policy(
        self,
        *,
        monthly_cap_micros: Optional[int],
        warn_threshold_pct: int,
        enforce: bool,
    ) -> None:
        """Upsert the org-wide cost policy singleton."""
        with get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO auth_cost_policy
                    (id, monthly_cap_micros, warn_threshold_pct, enforce, updated_at)
                VALUES (1, %s, %s, %s, NOW())
                ON CONFLICT (id) DO UPDATE SET
                    monthly_cap_micros = EXCLUDED.monthly_cap_micros,
                    warn_threshold_pct = EXCLUDED.warn_threshold_pct,
                    enforce = EXCLUDED.enforce,
                    updated_at = NOW()
                """,
                (monthly_cap_micros, warn_threshold_pct, enforce),
            )

    # ----- per-user / per-group caps -------------------------------------

    def set_user_cap(self, user_id: str, cap_micros: Optional[int]) -> None:
        """Set (or clear, with ``None``) a user's monthly cap override."""
        with get_cursor() as cur:
            cur.execute(
                "UPDATE auth_users SET monthly_cap_micros = %s, updated_at = NOW() "
                "WHERE id = %s",
                (cap_micros, user_id),
            )

    def set_group_cap(self, group_id: str, cap_micros: Optional[int]) -> None:
        """Set (or clear) a group's monthly cap."""
        with get_cursor() as cur:
            cur.execute(
                "UPDATE auth_groups SET monthly_cap_micros = %s, updated_at = NOW() "
                "WHERE id = %s",
                (cap_micros, group_id),
            )

    def effective_cap_micros(self, user_id: str) -> Optional[int]:
        """Most-specific cap for a user: user > min(group) > global (None=unlimited)."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT COALESCE(
                    u.monthly_cap_micros,
                    (SELECT MIN(g.monthly_cap_micros)
                     FROM auth_group_members gm
                     JOIN auth_groups g ON g.id = gm.group_id
                     WHERE gm.user_id = %s AND g.monthly_cap_micros IS NOT NULL),
                    (SELECT monthly_cap_micros FROM auth_cost_policy WHERE id = 1)
                ) AS cap
                FROM auth_users u WHERE u.id = %s
                """,
                (user_id, user_id),
            )
            row = cur.fetchone()
        return row["cap"] if row else None

    # ----- usage metering -------------------------------------------------

    def record_usage(
        self,
        user_id: str,
        *,
        spend_micros: int,
        prompt_tokens: int,
        completion_tokens: int,
        period: Optional[date] = None,
    ) -> None:
        """Add one call's usage to the user's monthly aggregate (upsert)."""
        with get_cursor() as cur:
            cur.execute(
                """
                INSERT INTO auth_llm_usage
                    (user_id, period, spend_micros, prompt_tokens,
                     completion_tokens, request_count, updated_at)
                VALUES (%s, %s, %s, %s, %s, 1, NOW())
                ON CONFLICT (user_id, period) DO UPDATE SET
                    spend_micros = auth_llm_usage.spend_micros + EXCLUDED.spend_micros,
                    prompt_tokens = auth_llm_usage.prompt_tokens + EXCLUDED.prompt_tokens,
                    completion_tokens =
                        auth_llm_usage.completion_tokens + EXCLUDED.completion_tokens,
                    request_count = auth_llm_usage.request_count + 1,
                    updated_at = NOW()
                """,
                (
                    user_id,
                    period or month_period(),
                    spend_micros,
                    prompt_tokens,
                    completion_tokens,
                ),
            )

    def monthly_spend_micros(self, user_id: str, period: Optional[date] = None) -> int:
        """Total spend (micro-USD) for a user in a month."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                "SELECT spend_micros FROM auth_llm_usage "
                "WHERE user_id = %s AND period = %s",
                (user_id, period or month_period()),
            )
            row = cur.fetchone()
        return int(row["spend_micros"]) if row else 0

    def reset_user_usage(self, user_id: str, period: Optional[date] = None) -> None:
        """Zero a user's usage for a month (admin override / dispute)."""
        with get_cursor() as cur:
            cur.execute(
                "DELETE FROM auth_llm_usage WHERE user_id = %s AND period = %s",
                (user_id, period or month_period()),
            )

    def all_usage(self, period: Optional[date] = None) -> list[dict[str, Any]]:
        """Per-user spend + effective cap for a month (admin overview)."""
        with get_cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT u.id AS user_id, u.email, u.username,
                       COALESCE(usage.spend_micros, 0) AS spend_micros,
                       COALESCE(usage.request_count, 0) AS request_count,
                       COALESCE(
                           u.monthly_cap_micros,
                           (SELECT MIN(g.monthly_cap_micros)
                            FROM auth_group_members gm
                            JOIN auth_groups g ON g.id = gm.group_id
                            WHERE gm.user_id = u.id
                              AND g.monthly_cap_micros IS NOT NULL),
                           (SELECT monthly_cap_micros FROM auth_cost_policy WHERE id = 1)
                       ) AS cap_micros,
                       u.monthly_cap_micros AS user_cap_micros
                FROM auth_users u
                LEFT JOIN auth_llm_usage usage
                    ON usage.user_id = u.id AND usage.period = %s
                WHERE COALESCE(usage.spend_micros, 0) > 0
                   OR u.monthly_cap_micros IS NOT NULL
                ORDER BY COALESCE(usage.spend_micros, 0) DESC
                """,
                (period or month_period(),),
            )
            return [dict(r) for r in cur.fetchall()]


__all__ = ["CostGovernanceMixin", "month_period"]
