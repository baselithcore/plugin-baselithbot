"""Audit-chain and cross-scan activity read paths.

Split out of the original monolithic ``scans.py`` to keep every file
under the 500-line cap. Mixed into ``RedAgentPersistence`` — relies on
``self.dsn`` / ``self.available`` provided by the host class.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import sql

from core.observability.logging import get_logger

from .._conn import acquire

logger = get_logger(__name__)


class AuditQueryMixin:
    """Audit chain, activity feed, and event-count read paths.

    Mixed into ``RedAgentPersistence``; depends on ``self.dsn`` and
    ``self.available`` from the host class.
    """

    dsn: str
    available: bool

    async def list_scan_audit(
        self, scan_id: UUID, *, limit: int = 500
    ) -> list[dict[str, Any]]:
        """Append-only audit chain for a scan, ordered oldest → newest.

        Drives the replay view: every guardrail decision, RoE
        adjustment, planner step, critic veto, scanner result and
        status change tied to ``scan_id`` is returned in execution
        order.
        """
        if not self.available:
            return []
        try:
            async with acquire(self.dsn) as conn:
                rows = await (
                    await conn.execute(
                        """
                        SELECT id, scan_id, actor, event, payload, created_at
                          FROM red_agent_audit
                         WHERE scan_id = %s
                      ORDER BY created_at ASC, id ASC
                         LIMIT %s
                        """,
                        (str(scan_id), limit),
                    )
                ).fetchall()
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.persistence.list_scan_audit_failed",
                extra={"err": str(e)},
            )
            return []
        return [
            {
                "id": int(r["id"]),
                "scan_id": str(r["scan_id"]) if r.get("scan_id") else None,
                "actor": r.get("actor"),
                "event": r["event"],
                "payload": r.get("payload") or {},
                "created_at": r.get("created_at"),
            }
            for r in rows
        ]

    async def list_recent_activity(
        self,
        *,
        events_prefix: list[str] | None = None,
        tenant_id: str | None = None,
        engagement_id: UUID | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Cross-scan activity feed, newest first.

        ``events_prefix`` filters by event-name prefix(es) (e.g.
        ``["scan.roe_", "scan.critic_"]`` for the cockpit feed). When
        ``tenant_id`` is set, the join filters audit rows whose parent
        scan belongs to the tenant; rows with NULL ``scan_id`` (legacy)
        fall through unfiltered. ``engagement_id`` scopes the feed to
        events from scans within a specific engagement.
        """
        if not self.available:
            return []
        clauses: list[sql.Composable] = []
        params: list[Any] = []
        join: sql.Composable = sql.SQL("")
        needs_join = tenant_id is not None or engagement_id is not None
        if needs_join:
            join = sql.SQL("LEFT JOIN red_agent_scans s ON s.id = a.scan_id")
        if tenant_id is not None:
            clauses.append(sql.SQL("(s.tenant_id IS NULL OR s.tenant_id = %s)"))
            params.append(tenant_id)
        if engagement_id is not None:
            clauses.append(sql.SQL("s.engagement_id = %s"))
            params.append(str(engagement_id))
        if events_prefix:
            ors = sql.SQL(" OR ").join(
                sql.SQL("a.event LIKE %s") for _ in events_prefix
            )
            clauses.append(sql.SQL("({})").format(ors))
            params.extend([f"{p}%" for p in events_prefix])
        where = (
            sql.SQL("WHERE ") + sql.SQL(" AND ").join(clauses)
            if clauses
            else sql.SQL("")
        )
        params.append(limit)
        query = sql.SQL(
            """
            SELECT a.id, a.scan_id, a.actor, a.event, a.payload, a.created_at
              FROM red_agent_audit a
              {join}
              {where}
          ORDER BY a.created_at DESC, a.id DESC
             LIMIT %s
            """
        ).format(join=join, where=where)
        try:
            async with acquire(self.dsn) as conn:
                rows = await (await conn.execute(query, tuple(params))).fetchall()
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.persistence.list_recent_activity_failed",
                extra={"err": str(e)},
            )
            return []
        return [
            {
                "id": int(r["id"]),
                "scan_id": str(r["scan_id"]) if r.get("scan_id") else None,
                "actor": r.get("actor"),
                "event": r["event"],
                "payload": r.get("payload") or {},
                "created_at": r.get("created_at"),
            }
            for r in rows
        ]

    async def bucket_recent_events(
        self,
        *,
        events: list[str],
        tenant_id: str | None = None,
        engagement_id: UUID | None = None,
        since_hours: int = 24,
        bucket: str = "hour",
    ) -> list[dict[str, Any]]:
        """Time-bucketed counts per event for trend visualization.

        Output shape::

            [
              {"bucket": <datetime>, "event": "scan.critic_veto", "count": 3},
              ...
            ]

        ``bucket`` is passed straight to ``date_trunc`` so callers can
        request ``minute``/``hour``/``day`` granularity. Returns empty
        on missing DSN or query error (fail-open like every other
        read path).
        """
        if not self.available or not events:
            return []
        if bucket not in {"minute", "hour", "day"}:
            bucket = "hour"
        clauses: list[sql.Composable] = [
            sql.SQL("a.event = ANY(%s)"),
            sql.SQL("a.created_at >= now() - make_interval(hours => %s)"),
        ]
        params: list[Any] = [events, since_hours]
        join: sql.Composable = sql.SQL("")
        if tenant_id is not None or engagement_id is not None:
            join = sql.SQL("LEFT JOIN red_agent_scans s ON s.id = a.scan_id")
        if tenant_id is not None:
            clauses.append(sql.SQL("(s.tenant_id IS NULL OR s.tenant_id = %s)"))
            params.append(tenant_id)
        if engagement_id is not None:
            clauses.append(sql.SQL("s.engagement_id = %s"))
            params.append(str(engagement_id))
        query = sql.SQL(
            """
            SELECT date_trunc(%s, a.created_at) AS bucket,
                   a.event AS event,
                   COUNT(*) AS n
              FROM red_agent_audit a
              {join}
             WHERE {where}
          GROUP BY bucket, a.event
          ORDER BY bucket ASC
            """
        ).format(
            join=join,
            where=sql.SQL(" AND ").join(clauses),
        )
        try:
            async with acquire(self.dsn) as conn:
                rows = await (await conn.execute(query, (bucket, *params))).fetchall()
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.persistence.bucket_recent_events_failed",
                extra={"err": str(e)},
            )
            return []
        return [
            {
                "bucket": r["bucket"],
                "event": r["event"],
                "count": int(r["n"] or 0),
            }
            for r in rows
        ]

    async def count_recent_events(
        self,
        *,
        events: list[str],
        tenant_id: str | None = None,
        engagement_id: UUID | None = None,
        since_hours: int = 24,
    ) -> dict[str, int]:
        """Per-event count over the trailing window.

        Returns one entry per requested event name (zero when absent),
        scoped by tenant or engagement when set. Backbone of the
        governance KPIs surfaced on the operator cockpit Dashboard
        and on the engagement detail page.
        """
        if not self.available or not events:
            return {e: 0 for e in events}
        clauses: list[sql.Composable] = [
            sql.SQL("a.event = ANY(%s)"),
            sql.SQL("a.created_at >= now() - make_interval(hours => %s)"),
        ]
        params: list[Any] = [events, since_hours]
        join: sql.Composable = sql.SQL("")
        needs_join = tenant_id is not None or engagement_id is not None
        if needs_join:
            join = sql.SQL("LEFT JOIN red_agent_scans s ON s.id = a.scan_id")
        if tenant_id is not None:
            clauses.append(sql.SQL("(s.tenant_id IS NULL OR s.tenant_id = %s)"))
            params.append(tenant_id)
        if engagement_id is not None:
            clauses.append(sql.SQL("s.engagement_id = %s"))
            params.append(str(engagement_id))
        query = sql.SQL(
            """
            SELECT a.event, COUNT(*) AS n
              FROM red_agent_audit a
              {join}
             WHERE {where}
          GROUP BY a.event
            """
        ).format(
            join=join,
            where=sql.SQL(" AND ").join(clauses),
        )
        try:
            async with acquire(self.dsn) as conn:
                rows = await (await conn.execute(query, tuple(params))).fetchall()
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.persistence.count_recent_events_failed",
                extra={"err": str(e)},
            )
            return {e: 0 for e in events}
        out = {e: 0 for e in events}
        for row in rows:
            name = row.get("event")
            if name in out:
                out[name] = int(row.get("n") or 0)
        return out
