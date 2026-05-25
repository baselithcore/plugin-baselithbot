"""Finding lifecycle operations: external-ref linkage and triage transitions.

Split out from ``scans.py`` to keep that module under the 500-line cap.
Mixed into ``RedAgentPersistence`` — relies on ``self.dsn`` /
``self.available`` provided by the host class.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from psycopg import sql

from core.observability.logging import get_logger
from plugins.red_agent.models import FindingState, FindingTriageUpdate

from ._conn import acquire

logger = get_logger(__name__)


class FindingLifecycleMixin:
    """External-ref linkage and triage state transitions.

    Mixed into ``RedAgentPersistence``; provides default ``available``
    based on ``self.dsn`` (set by host ``__init__``).
    """

    dsn: str

    @property
    def available(self) -> bool:
        return bool(self.dsn)

    async def find_by_external_ref(self, external_ref: str) -> UUID | None:
        """Resolve a downstream ticket reference back to the finding UUID.

        Used by the inbound webhook receiver to apply ``state``/``notes``
        updates from the SOAR system to the original finding. Returns
        the most recently discovered match when more than one finding
        carries the same ref (rare; should not happen with proper
        ticket→finding 1:1 mapping).
        """
        if not self.available or not external_ref:
            return None
        try:
            async with acquire(self.dsn) as conn:
                row = await (
                    await conn.execute(
                        """
                        SELECT id FROM red_agent_findings
                        WHERE external_ref = %s
                        ORDER BY discovered_at DESC
                        LIMIT 1
                        """,
                        (external_ref,),
                    )
                ).fetchone()
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.persistence.find_by_external_ref_failed",
                extra={"err": str(e)},
            )
            return None
        if not row:
            return None
        fid = row["id"]
        if isinstance(fid, UUID):
            return fid
        try:
            return UUID(str(fid))
        except ValueError:
            return None

    async def update_finding_external_ref(
        self, finding_id: UUID, external_ref: str | None
    ) -> bool:
        """Set or clear the external system reference (Jira / ServiceNow / Linear).

        Returns True if a row was updated. Used by the SOAR integration
        to remember the downstream ticket ID per finding so subsequent
        webhook events can resolve the original.
        """
        if not self.available:
            return False
        async with acquire(self.dsn) as conn:
            cur = await conn.execute(
                "UPDATE red_agent_findings SET external_ref = %s WHERE id = %s",
                (external_ref, str(finding_id)),
            )
            await conn.commit()
            return (cur.rowcount or 0) > 0

    async def update_finding_triage(
        self,
        finding_id: UUID,
        update: FindingTriageUpdate,
        actor: str,
    ) -> bool:
        """Apply a triage transition. Returns True if a row was updated.

        State transitions auto-stamp lifecycle timestamps:
            triaged → triaged_at, fixed/wontfix/accepted → resolved_at.
        """
        if not self.available:
            return False
        sets: list[sql.Composable] = []
        params: list[Any] = []
        if update.state is not None:
            sets.append(sql.SQL("state = %s"))
            params.append(update.state.value)
            if update.state == FindingState.TRIAGED:
                sets.append(sql.SQL("triaged_at = COALESCE(triaged_at, now())"))
            elif update.state in {
                FindingState.FIXED,
                FindingState.WONTFIX,
                FindingState.ACCEPTED,
            }:
                sets.append(sql.SQL("resolved_at = now()"))
            elif update.state == FindingState.OPEN:
                sets.append(sql.SQL("resolved_at = NULL"))
        if update.assignee is not None:
            sets.append(sql.SQL("assignee = %s"))
            params.append(update.assignee)
        if update.notes is not None:
            sets.append(sql.SQL("notes = %s"))
            params.append(update.notes)
        if update.due_at is not None:
            sets.append(sql.SQL("due_at = %s"))
            params.append(update.due_at)
        if not sets:
            return False
        del actor  # reserved for future audit-log hook
        params.append(str(finding_id))
        query = sql.SQL("UPDATE red_agent_findings SET {sets} WHERE id = %s").format(
            sets=sql.SQL(", ").join(sets)
        )
        async with acquire(self.dsn) as conn:
            cur = await conn.execute(query, tuple(params))
            await conn.commit()
            return (cur.rowcount or 0) > 0
