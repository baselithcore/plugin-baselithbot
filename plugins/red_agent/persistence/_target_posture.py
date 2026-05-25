"""Posture / diff analytics for ``red_agent_targets``.

Split from ``targets.py`` to keep that module under the 500-line cap.
Mixed into ``TargetPersistence``; relies on ``self.dsn`` /
``self.available`` and ``self._conn()`` from the host.
"""

from __future__ import annotations

from typing import Any, List
from uuid import UUID

from psycopg.rows import DictRow
import psycopg

from plugins.red_agent.models import Finding

from ._conn import open_conn


class TargetPostureMixin:
    """Diff and posture aggregation queries."""

    dsn: str

    @property
    def available(self) -> bool:
        return bool(self.dsn)

    async def _conn(self) -> psycopg.AsyncConnection[DictRow]:
        return await open_conn(self.dsn)

    async def diff_runs(
        self, baseline_scan_id: UUID, latest_scan_id: UUID
    ) -> dict[str, Any]:
        """Compare two scans of the same target.

        Findings matched by ``(title, scanner, endpoint, target)``. Returns
        buckets ``new``, ``fixed``, ``regressed`` (severity worsened),
        plus ``unchanged`` count (full set is omitted to keep payload small).
        """
        if not self.available:
            return {}

        sev_order = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}

        async def _findings(scan_id: UUID) -> List[Finding]:
            async with await self._conn() as conn:
                rows = await (
                    await conn.execute(
                        "SELECT * FROM red_agent_findings WHERE scan_id = %s",
                        (str(scan_id),),
                    )
                ).fetchall()
                return [Finding.model_validate(r) for r in rows]

        base = await _findings(baseline_scan_id)
        head = await _findings(latest_scan_id)

        def _key(f: Finding) -> tuple[str, str, str, str]:
            return (f.title, f.scanner, f.endpoint or "", f.target)

        base_map = {_key(f): f for f in base}
        head_map = {_key(f): f for f in head}
        new = [head_map[k] for k in head_map.keys() - base_map.keys()]
        fixed = [base_map[k] for k in base_map.keys() - head_map.keys()]
        regressed: List[dict[str, Any]] = []
        unchanged = 0
        for k in head_map.keys() & base_map.keys():
            b, h = base_map[k], head_map[k]
            if sev_order.get(h.severity.value, 0) > sev_order.get(b.severity.value, 0):
                regressed.append(
                    {
                        "finding": h.model_dump(mode="json"),
                        "from_severity": b.severity.value,
                        "to_severity": h.severity.value,
                    }
                )
            else:
                unchanged += 1
        return {
            "baseline_scan_id": str(baseline_scan_id),
            "latest_scan_id": str(latest_scan_id),
            "new": [f.model_dump(mode="json") for f in new],
            "fixed": [f.model_dump(mode="json") for f in fixed],
            "regressed": regressed,
            "unchanged": unchanged,
        }

    async def posture(self, target_id: UUID) -> dict[str, Any]:
        """Aggregated posture for a target.

        Counts findings by severity and lifecycle state, plus SLA stats and
        a 30-day daily new-finding histogram. Cheap enough to compute on
        each request; pre-aggregation can come later if it ever shows up
        in profiling.
        """
        if not self.available:
            return {}
        async with await self._conn() as conn:
            sev = await (
                await conn.execute(
                    """
                    SELECT f.severity, count(*) AS n
                      FROM red_agent_findings f
                      JOIN red_agent_scans s ON s.id = f.scan_id
                     WHERE s.target_id = %s AND f.state IN ('open','triaged')
                  GROUP BY f.severity
                    """,
                    (str(target_id),),
                )
            ).fetchall()
            state_rows = await (
                await conn.execute(
                    """
                    SELECT f.state, count(*) AS n
                      FROM red_agent_findings f
                      JOIN red_agent_scans s ON s.id = f.scan_id
                     WHERE s.target_id = %s
                  GROUP BY f.state
                    """,
                    (str(target_id),),
                )
            ).fetchall()
            overdue = await (
                await conn.execute(
                    """
                    SELECT count(*) AS n
                      FROM red_agent_findings f
                      JOIN red_agent_scans s ON s.id = f.scan_id
                     WHERE s.target_id = %s
                       AND f.state IN ('open','triaged')
                       AND f.due_at IS NOT NULL AND f.due_at < now()
                    """,
                    (str(target_id),),
                )
            ).fetchone()
            scans = await (
                await conn.execute(
                    """
                    SELECT count(*) AS total,
                           count(*) FILTER (WHERE status = 'completed') AS completed,
                           count(*) FILTER (WHERE status = 'failed') AS failed,
                           max(started_at) AS last_started_at
                      FROM red_agent_scans
                     WHERE target_id = %s
                    """,
                    (str(target_id),),
                )
            ).fetchone()
            histogram = await (
                await conn.execute(
                    """
                    SELECT date_trunc('day', f.discovered_at) AS day,
                           f.severity, count(*) AS n
                      FROM red_agent_findings f
                      JOIN red_agent_scans s ON s.id = f.scan_id
                     WHERE s.target_id = %s
                       AND f.discovered_at > now() - interval '30 days'
                  GROUP BY day, f.severity
                  ORDER BY day
                    """,
                    (str(target_id),),
                )
            ).fetchall()
        sev_counts = {r["severity"]: int(r["n"]) for r in sev}
        state_counts = {r["state"]: int(r["n"]) for r in state_rows}
        return {
            "severity_counts": sev_counts,
            "state_counts": state_counts,
            "overdue": int((overdue or {}).get("n", 0) or 0),
            "scans_total": int((scans or {}).get("total", 0) or 0),
            "scans_completed": int((scans or {}).get("completed", 0) or 0),
            "scans_failed": int((scans or {}).get("failed", 0) or 0),
            "last_scan_at": (scans or {}).get("last_started_at"),
            "histogram": [
                {
                    "day": r["day"],
                    "severity": r["severity"],
                    "count": int(r["n"]),
                }
                for r in histogram
            ],
        }
