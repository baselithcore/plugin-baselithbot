"""Postgres-backed store for scans and findings.

Single source of truth for the immutable scan/finding records. The
graph layer is a downstream projection optimized for traversal queries.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from psycopg import sql
from psycopg.rows import DictRow

import psycopg

from core.observability.logging import get_logger
from plugins.red_agent.models import (
    SLA_DAYS,
    Finding,
    ScanRequest,
    ScanResult,
    ScanStatus,
)

from ._conn import acquire, jsonb, open_conn
from ._finding_lifecycle import FindingLifecycleMixin

logger = get_logger(__name__)


class RedAgentPersistence(FindingLifecycleMixin):
    """Async psycopg wrapper for scan + finding tables.

    Tolerates a missing DSN or DB outage: read paths return empty
    collections, write paths log and no-op. The plugin therefore
    boots in dev environments without Postgres provisioned.
    """

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    async def _conn(self) -> psycopg.AsyncConnection[DictRow]:
        # Retained for sub-classes / external callers that grab a one-shot
        # connection. Internal hot paths now use ``acquire`` against the pool.
        return await open_conn(self.dsn)

    async def insert_scan(self, scan_id: UUID, request: ScanRequest) -> None:
        # Always populate the live-stream cache, even when DSN is missing,
        # so dev / in-memory mode preserves engagement scoping on the WS feed.
        try:
            from core.di.container import ServiceRegistry
            from plugins.red_agent.events import ScanEngagementIndex

            index = ServiceRegistry.get(ScanEngagementIndex)
        except Exception:  # noqa: BLE001
            index = None
        if index is not None:
            try:
                index.remember(scan_id, request.engagement_id)
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "red_agent.engagement_index.remember_failed",
                    extra={"err": str(e)},
                )
        if not self.available:
            logger.warning("red_agent.persistence.no_dsn", extra={"op": "insert_scan"})
            return
        async with acquire(self.dsn) as conn:
            await conn.execute(
                """
                INSERT INTO red_agent_scans
                  (id, status, target_type, target_value, target_id, engagement_id, intensity,
                   scanners, tenant_id, requested_by, bug_bounty_program, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    str(scan_id),
                    ScanStatus.QUEUED.value,
                    request.target.type.value,
                    request.target.value,
                    str(request.target_id) if request.target_id else None,
                    str(request.engagement_id) if request.engagement_id else None,
                    request.intensity.value,
                    request.scanners,
                    request.tenant_id,
                    request.requested_by,
                    request.bug_bounty_program,
                    request.notes,
                ),
            )
            if request.target_id:
                await conn.execute(
                    "UPDATE red_agent_targets SET last_scan_at = now(), updated_at = now()"
                    " WHERE id = %s",
                    (str(request.target_id),),
                )
            await conn.commit()

    async def delete_scan(self, scan_id: UUID) -> bool:
        """Hard-delete a scan and its findings (FK cascade).

        Caller must verify the scan is in a terminal state — this method
        does not check, so it can be reused for forced cleanup tasks.
        Returns True if a row was deleted.
        """
        if not self.available:
            return False
        async with acquire(self.dsn) as conn:
            cur = await conn.execute(
                "DELETE FROM red_agent_scans WHERE id = %s",
                (str(scan_id),),
            )
            await conn.commit()
            return (cur.rowcount or 0) > 0

    async def update_status(
        self, scan_id: UUID, status: ScanStatus, error: str | None = None
    ) -> None:
        if not self.available:
            return
        async with acquire(self.dsn) as conn:
            await conn.execute(
                """
                UPDATE red_agent_scans
                   SET status = %s,
                       error = %s,
                       finished_at = CASE WHEN %s IN ('completed','failed','cancelled')
                                          THEN now() ELSE finished_at END
                 WHERE id = %s
                """,
                (status.value, error, status.value, str(scan_id)),
            )
            await conn.commit()

    async def reconcile_orphaned_scans(
        self, error: str = "orphaned by backend restart"
    ) -> int:
        """Mark `running`/`queued` scans as `failed` after a restart.

        In-memory asyncio tasks driving each scan are lost on restart, so
        any row left in a non-terminal active state is unreachable. Returns
        the count of rows reconciled (0 when DSN missing or no orphans).
        """
        if not self.available:
            return 0
        async with acquire(self.dsn) as conn:
            cur = await conn.execute(
                """
                UPDATE red_agent_scans
                   SET status = 'failed',
                       error = %s,
                       finished_at = now()
                 WHERE status IN ('running','queued')
                """,
                (error,),
            )
            await conn.commit()
            return cur.rowcount or 0

    async def insert_findings(self, scan_id: UUID, findings: list[Finding]) -> None:
        if not findings or not self.available:
            return
        for f in findings:
            if f.due_at is None:
                f.due_at = f.discovered_at + timedelta(days=SLA_DAYS[f.severity])
        async with acquire(self.dsn) as conn:
            async with conn.cursor() as cur:
                await cur.executemany(
                    """
                    INSERT INTO red_agent_findings
                      (id, scan_id, scanner, title, description, severity,
                       cvss_score, cwe, cve, target, endpoint, port, service,
                       evidence, raw, remediation, discovered_at,
                       state, assignee, triaged_at, resolved_at, due_at, notes,
                       risk_score, controls, external_ref)
                    VALUES
                      (%s, %s, %s, %s, %s, %s,
                       %s, %s, %s, %s, %s, %s, %s,
                       %s::jsonb, %s::jsonb, %s, %s,
                       %s, %s, %s, %s, %s, %s,
                       %s, %s, %s)
                    """,
                    [
                        (
                            str(f.id),
                            str(scan_id),
                            f.scanner,
                            f.title,
                            f.description,
                            f.severity.value,
                            f.cvss_score,
                            f.cwe,
                            f.cve,
                            f.target,
                            f.endpoint,
                            f.port,
                            f.service,
                            jsonb(f.evidence),
                            jsonb(f.raw),
                            f.remediation,
                            f.discovered_at,
                            f.state.value,
                            f.assignee,
                            f.triaged_at,
                            f.resolved_at,
                            f.due_at,
                            f.notes,
                            f.risk_score,
                            f.controls,
                            f.external_ref,
                        )
                        for f in findings
                    ],
                )
            await conn.commit()

    async def get_scan(self, scan_id: UUID) -> ScanResult | None:
        if not self.available:
            return None
        try:
            return await self._get_scan_impl(scan_id)
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.persistence.get_scan_failed", extra={"err": str(e)}
            )
            return None

    async def _get_scan_impl(self, scan_id: UUID) -> ScanResult | None:
        async with acquire(self.dsn) as conn:
            row = await (
                await conn.execute(
                    "SELECT * FROM red_agent_scans WHERE id = %s",
                    (str(scan_id),),
                )
            ).fetchone()
            if not row:
                return None
            findings_rows = await (
                await conn.execute(
                    "SELECT * FROM red_agent_findings WHERE scan_id = %s",
                    (str(scan_id),),
                )
            ).fetchall()
            row_id = row["id"]
            tid = row.get("target_id")
            eid = row.get("engagement_id")
            return ScanResult(
                scan_id=row_id if isinstance(row_id, UUID) else UUID(str(row_id)),
                status=ScanStatus(row["status"]),
                started_at=row["started_at"] or datetime.now(timezone.utc),
                finished_at=row["finished_at"],
                duration_seconds=row.get("duration_seconds"),
                error=row.get("error"),
                findings=[Finding.model_validate(r) for r in findings_rows],
                target_id=tid
                if tid is None or isinstance(tid, UUID)
                else UUID(str(tid)),
                engagement_id=eid
                if eid is None or isinstance(eid, UUID)
                else UUID(str(eid)),
            )

    async def list_scans(
        self,
        *,
        tenant_id: str | None = None,
        status_filter: ScanStatus | None = None,
        target_id: UUID | None = None,
        engagement_id: UUID | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        if not self.available:
            return []
        try:
            return await self._list_scans_impl(
                tenant_id=tenant_id,
                status_filter=status_filter,
                target_id=target_id,
                engagement_id=engagement_id,
                limit=limit,
                offset=offset,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.persistence.list_scans_failed", extra={"err": str(e)}
            )
            return []

    async def _list_scans_impl(
        self,
        *,
        tenant_id: str | None,
        status_filter: ScanStatus | None,
        target_id: UUID | None,
        engagement_id: UUID | None,
        limit: int,
        offset: int,
    ) -> list[dict[str, Any]]:
        clauses: list[sql.Composable] = []
        params: list[Any] = []
        if tenant_id is not None:
            clauses.append(sql.SQL("tenant_id = %s"))
            params.append(tenant_id)
        if status_filter is not None:
            clauses.append(sql.SQL("status = %s"))
            params.append(status_filter.value)
        if target_id is not None:
            clauses.append(sql.SQL("target_id = %s"))
            params.append(str(target_id))
        if engagement_id is not None:
            clauses.append(sql.SQL("engagement_id = %s"))
            params.append(str(engagement_id))
        where = (
            sql.SQL("WHERE ") + sql.SQL(" AND ").join(clauses)
            if clauses
            else sql.SQL("")
        )
        params.extend([limit, offset])

        query = sql.SQL(
            """
            SELECT id, status, target_value, target_id, engagement_id, intensity, scanners,
                   requested_by, started_at, finished_at, error
              FROM red_agent_scans
              {where}
          ORDER BY started_at DESC
             LIMIT %s OFFSET %s
            """
        ).format(where=where)

        async with acquire(self.dsn) as conn:
            rows = await (await conn.execute(query, tuple(params))).fetchall()
            return [dict(r) for r in rows]

    async def get_finding(self, finding_id: UUID) -> tuple[Finding, UUID] | None:
        """Resolve a finding by id along with its parent scan_id.

        Backbone of the evidence-ledger endpoint: callers join the
        returned scan_id against the audit chain to reconstruct the
        full provenance of a finding (planner step that produced it,
        critic decisions, scanner output, etc.).
        """
        if not self.available:
            return None
        try:
            async with acquire(self.dsn) as conn:
                row = await (
                    await conn.execute(
                        "SELECT * FROM red_agent_findings WHERE id = %s",
                        (str(finding_id),),
                    )
                ).fetchone()
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.persistence.get_finding_failed", extra={"err": str(e)}
            )
            return None
        if not row:
            return None
        sid = row["scan_id"]
        scan_uuid = sid if isinstance(sid, UUID) else UUID(str(sid))
        return Finding.model_validate(row), scan_uuid

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

    async def list_findings(
        self,
        *,
        tenant_id: str | None = None,
        severity: str | None = None,
        cwe: str | None = None,
        scanner: str | None = None,
        target: str | None = None,
        target_id: UUID | None = None,
        state: str | None = None,
        assignee: str | None = None,
        overdue: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Finding]:
        if not self.available:
            return []
        try:
            return await self._list_findings_impl(
                tenant_id=tenant_id,
                severity=severity,
                cwe=cwe,
                scanner=scanner,
                target=target,
                target_id=target_id,
                state=state,
                assignee=assignee,
                overdue=overdue,
                limit=limit,
                offset=offset,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.persistence.list_findings_failed", extra={"err": str(e)}
            )
            return []

    async def _list_findings_impl(
        self,
        *,
        tenant_id: str | None,
        severity: str | None,
        cwe: str | None,
        scanner: str | None,
        target: str | None,
        target_id: UUID | None,
        state: str | None,
        assignee: str | None,
        overdue: bool,
        limit: int,
        offset: int,
    ) -> list[Finding]:
        clauses: list[sql.Composable] = []
        params: list[Any] = []
        join: sql.Composable = sql.SQL("")
        if tenant_id is not None or target_id is not None:
            join = sql.SQL("JOIN red_agent_scans s ON s.id = f.scan_id")
        if tenant_id is not None:
            clauses.append(sql.SQL("s.tenant_id = %s"))
            params.append(tenant_id)
        if target_id is not None:
            clauses.append(sql.SQL("s.target_id = %s"))
            params.append(str(target_id))
        if severity:
            clauses.append(sql.SQL("f.severity = %s"))
            params.append(severity)
        if cwe:
            clauses.append(sql.SQL("f.cwe = %s"))
            params.append(cwe)
        if scanner:
            clauses.append(sql.SQL("f.scanner = %s"))
            params.append(scanner)
        if target:
            clauses.append(sql.SQL("f.target = %s"))
            params.append(target)
        if state:
            clauses.append(sql.SQL("f.state = %s"))
            params.append(state)
        if assignee:
            clauses.append(sql.SQL("f.assignee = %s"))
            params.append(assignee)
        if overdue:
            clauses.append(sql.SQL("f.due_at IS NOT NULL AND f.due_at < now()"))
            clauses.append(sql.SQL("f.state IN ('open','triaged')"))
        where = (
            sql.SQL("WHERE ") + sql.SQL(" AND ").join(clauses)
            if clauses
            else sql.SQL("")
        )
        params.extend([limit, offset])

        query = sql.SQL(
            """
            SELECT f.*
              FROM red_agent_findings f
              {join}
              {where}
          ORDER BY f.discovered_at DESC
             LIMIT %s OFFSET %s
            """
        ).format(join=join, where=where)

        async with acquire(self.dsn) as conn:
            rows = await (await conn.execute(query, tuple(params))).fetchall()
            return [Finding.model_validate(r) for r in rows]
