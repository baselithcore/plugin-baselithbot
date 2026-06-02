"""Filtered finding-listing read path.

Split out of the original monolithic ``scans.py`` to keep every file
under the 500-line cap. Mixed into ``RedAgentPersistence`` — relies on
``self.dsn`` / ``self.available`` provided by the host class.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import sql

from core.observability.logging import get_logger
from plugins.red_agent.models import Finding

from .._conn import acquire

logger = get_logger(__name__)


class FindingsQueryMixin:
    """Filtered ``list_findings`` read path.

    Mixed into ``RedAgentPersistence``; depends on ``self.dsn`` and
    ``self.available`` from the host class.
    """

    dsn: str
    available: bool

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
