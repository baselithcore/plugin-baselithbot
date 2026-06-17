"""Durable Postgres-backed :class:`ProcessStore`.

Uses the shared async connection pool from :mod:`core.db.connection` (the same
pool the rest of the platform shares, so cost-tracking and timezone handling come
for free). Each entity round-trips losslessly through a JSONB ``data`` column via
``model_dump(mode="json")`` / ``model_validate``; scalar columns exist only for
keying and insertion-order reads. Schema is self-initialized on :meth:`initialize`
(idempotent DDL), mirroring :class:`core.storage.postgres.PostgresStorage`.
"""

from __future__ import annotations

from typing import Any

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from core.config import get_storage_config
from core.db.connection import get_async_connection, get_async_cursor
from core.observability.logging import get_logger

from ..automation_models import AutomationRule, RuleFiring
from ..event_models import Event, MiningResult
from ..models import (
    Bottleneck,
    MetricSample,
    OptimizationProposal,
    ProcessGraph,
)
from ..resources import Resource
from ..sla_models import SlaDefinition
from ._pg_util import _blob
from ._postgres_governance import _PgGovernanceMixin
from ._protocol import (
    MAX_EVENTS_PER_PROCESS,
    MAX_FIRINGS_PER_PROCESS,
    MAX_SAMPLES_PER_SERIES,
)
from ._schema import _CHILD_TABLES, SCHEMA_DDL

logger = get_logger(__name__)


class PostgresProcessStore(_PgGovernanceMixin):
    """Durable :class:`ProcessStore` backed by PostgreSQL JSONB tables.

    Versioning, audit, and applied-change persistence live in
    :class:`_PgGovernanceMixin` (split out only to respect the file-size cap);
    the methods below cover processes, resources, samples, proposals,
    bottlenecks, rules, firings, mining, the event log, and SLAs.
    """

    async def initialize(self) -> None:
        """Create the BOP tables if absent. Fails fast if Postgres is disabled."""
        if not get_storage_config().postgres_enabled:
            raise RuntimeError(
                "BOP persistence='postgres' requires POSTGRES_ENABLED=true."
            )
        async with get_async_cursor() as cur:
            await cur.execute(SCHEMA_DDL)
        logger.info("bop_postgres_store_initialized")

    # -- Processes ---------------------------------------------------------

    async def save_process(self, tenant_id: str, process: ProcessGraph) -> ProcessGraph:
        sql = """
            INSERT INTO bop_processes (tenant_id, id, data, updated_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (tenant_id, id) DO UPDATE
                SET data = EXCLUDED.data, updated_at = NOW()
        """
        async with get_async_cursor() as cur:
            await cur.execute(sql, (tenant_id, process.id, _blob(process)))
        return process

    async def get_process(self, tenant_id: str, process_id: str) -> ProcessGraph | None:
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore
            await cur.execute(
                "SELECT data FROM bop_processes WHERE tenant_id = %s AND id = %s",
                (tenant_id, process_id),
            )
            row = await cur.fetchone()
        return ProcessGraph.model_validate(row["data"]) if row else None

    async def list_processes(self, tenant_id: str) -> list[ProcessGraph]:
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore
            await cur.execute(
                "SELECT data FROM bop_processes WHERE tenant_id = %s ORDER BY created_at",
                (tenant_id,),
            )
            rows = await cur.fetchall()
        return [ProcessGraph.model_validate(r["data"]) for r in rows]

    async def delete_process(self, tenant_id: str, process_id: str) -> bool:
        """Delete a tenant's process and all derived rows in one transaction."""
        async with get_async_connection() as conn:
            async with conn.transaction():
                async with conn.cursor() as cur:
                    for table in _CHILD_TABLES:
                        await cur.execute(
                            f"DELETE FROM {table} WHERE tenant_id = %s AND process_id = %s",  # type: ignore[arg-type]  # noqa: S608
                            (tenant_id, process_id),
                        )
                    await cur.execute(
                        "DELETE FROM bop_processes WHERE tenant_id = %s AND id = %s "
                        "RETURNING id",
                        (tenant_id, process_id),
                    )
                    return await cur.fetchone() is not None

    # -- Resources ---------------------------------------------------------

    async def save_resource(self, tenant_id: str, resource: Resource) -> Resource:
        sql = """
            INSERT INTO bop_resources (tenant_id, id, data, updated_at)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (tenant_id, id) DO UPDATE
                SET data = EXCLUDED.data, updated_at = NOW()
        """
        async with get_async_cursor() as cur:
            await cur.execute(sql, (tenant_id, resource.id, _blob(resource)))
        return resource

    async def get_resource(self, tenant_id: str, resource_id: str) -> Resource | None:
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore
            await cur.execute(
                "SELECT data FROM bop_resources WHERE tenant_id = %s AND id = %s",
                (tenant_id, resource_id),
            )
            row = await cur.fetchone()
        return Resource.model_validate(row["data"]) if row else None

    async def list_resources(self, tenant_id: str) -> list[Resource]:
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore
            await cur.execute(
                "SELECT data FROM bop_resources WHERE tenant_id = %s ORDER BY created_at",
                (tenant_id,),
            )
            rows = await cur.fetchall()
        return [Resource.model_validate(r["data"]) for r in rows]

    async def delete_resource(self, tenant_id: str, resource_id: str) -> bool:
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore
            await cur.execute(
                "DELETE FROM bop_resources WHERE tenant_id = %s AND id = %s "
                "RETURNING id",
                (tenant_id, resource_id),
            )
            return await cur.fetchone() is not None

    # -- Samples -----------------------------------------------------------

    async def add_samples(self, tenant_id: str, samples: list[MetricSample]) -> int:
        if not samples:
            return 0
        rows = [(tenant_id, s.process_id, s.kpi_id, _blob(s)) for s in samples]
        async with get_async_cursor() as cur:
            await cur.executemany(
                "INSERT INTO bop_samples (tenant_id, process_id, kpi_id, data) "
                "VALUES (%s, %s, %s, %s)",
                rows,
            )
        return len(samples)

    async def recent_samples(
        self, tenant_id: str, process_id: str, kpi_id: str
    ) -> list[MetricSample]:
        """Return the most-recent window oldest-first (matches in-memory order)."""
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore
            await cur.execute(
                "SELECT data FROM bop_samples WHERE tenant_id = %s AND process_id = %s "
                "AND kpi_id = %s ORDER BY seq DESC LIMIT %s",
                (tenant_id, process_id, kpi_id, MAX_SAMPLES_PER_SERIES),
            )
            rows = await cur.fetchall()
        return [MetricSample.model_validate(r["data"]) for r in reversed(rows)]

    # -- Proposals ---------------------------------------------------------

    async def save_proposal(
        self, tenant_id: str, proposal: OptimizationProposal
    ) -> OptimizationProposal:
        sql = """
            INSERT INTO bop_proposals (tenant_id, id, process_id, data)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (tenant_id, id) DO UPDATE SET data = EXCLUDED.data
        """
        async with get_async_cursor() as cur:
            await cur.execute(
                sql, (tenant_id, proposal.id, proposal.process_id, _blob(proposal))
            )
        return proposal

    async def get_proposal(
        self, tenant_id: str, proposal_id: str
    ) -> OptimizationProposal | None:
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore
            await cur.execute(
                "SELECT data FROM bop_proposals WHERE tenant_id = %s AND id = %s",
                (tenant_id, proposal_id),
            )
            row = await cur.fetchone()
        return OptimizationProposal.model_validate(row["data"]) if row else None

    async def list_proposals(
        self, tenant_id: str, process_id: str | None = None
    ) -> list[OptimizationProposal]:
        params: tuple[Any, ...] = (tenant_id,)
        sql = "SELECT data FROM bop_proposals WHERE tenant_id = %s"
        if process_id is not None:
            sql += " AND process_id = %s"
            params = (tenant_id, process_id)
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore
            await cur.execute(sql, params)
            rows = await cur.fetchall()
        return [OptimizationProposal.model_validate(r["data"]) for r in rows]

    # -- Bottlenecks -------------------------------------------------------

    async def save_bottlenecks(
        self, tenant_id: str, process_id: str, bottlenecks: list[Bottleneck]
    ) -> None:
        payload = Jsonb([b.model_dump(mode="json") for b in bottlenecks])
        sql = """
            INSERT INTO bop_bottlenecks (tenant_id, process_id, data)
            VALUES (%s, %s, %s)
            ON CONFLICT (tenant_id, process_id) DO UPDATE SET data = EXCLUDED.data
        """
        async with get_async_cursor() as cur:
            await cur.execute(sql, (tenant_id, process_id, payload))

    async def list_bottlenecks(
        self, tenant_id: str, process_id: str
    ) -> list[Bottleneck]:
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore
            await cur.execute(
                "SELECT data FROM bop_bottlenecks WHERE tenant_id = %s "
                "AND process_id = %s",
                (tenant_id, process_id),
            )
            row = await cur.fetchone()
        if not row:
            return []
        return [Bottleneck.model_validate(b) for b in row["data"]]

    # -- Rules -------------------------------------------------------------

    async def save_rule(self, tenant_id: str, rule: AutomationRule) -> AutomationRule:
        sql = """
            INSERT INTO bop_rules (tenant_id, id, process_id, data)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (tenant_id, id) DO UPDATE SET data = EXCLUDED.data
        """
        async with get_async_cursor() as cur:
            await cur.execute(sql, (tenant_id, rule.id, rule.process_id, _blob(rule)))
        return rule

    async def get_rule(self, tenant_id: str, rule_id: str) -> AutomationRule | None:
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore
            await cur.execute(
                "SELECT data FROM bop_rules WHERE tenant_id = %s AND id = %s",
                (tenant_id, rule_id),
            )
            row = await cur.fetchone()
        return AutomationRule.model_validate(row["data"]) if row else None

    async def list_rules(
        self, tenant_id: str, process_id: str | None = None
    ) -> list[AutomationRule]:
        params: tuple[Any, ...] = (tenant_id,)
        sql = "SELECT data FROM bop_rules WHERE tenant_id = %s"
        if process_id is not None:
            sql += " AND process_id = %s"
            params = (tenant_id, process_id)
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore
            await cur.execute(sql, params)
            rows = await cur.fetchall()
        return [AutomationRule.model_validate(r["data"]) for r in rows]

    async def delete_rule(self, tenant_id: str, rule_id: str) -> bool:
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore
            await cur.execute(
                "DELETE FROM bop_rules WHERE tenant_id = %s AND id = %s RETURNING id",
                (tenant_id, rule_id),
            )
            return await cur.fetchone() is not None

    # -- Firings -----------------------------------------------------------

    async def add_firings(self, tenant_id: str, firings: list[RuleFiring]) -> None:
        if not firings:
            return
        rows = [(tenant_id, f.process_id, _blob(f)) for f in firings]
        async with get_async_cursor() as cur:
            await cur.executemany(
                "INSERT INTO bop_firings (tenant_id, process_id, data) "
                "VALUES (%s, %s, %s)",
                rows,
            )

    async def list_firings(self, tenant_id: str, process_id: str) -> list[RuleFiring]:
        """Return the most-recent firing window oldest-first (in-memory order)."""
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore
            await cur.execute(
                "SELECT data FROM bop_firings WHERE tenant_id = %s AND process_id = %s "
                "ORDER BY seq DESC LIMIT %s",
                (tenant_id, process_id, MAX_FIRINGS_PER_PROCESS),
            )
            rows = await cur.fetchall()
        return [RuleFiring.model_validate(r["data"]) for r in reversed(rows)]

    # -- Mining ------------------------------------------------------------

    async def save_mining_result(self, tenant_id: str, result: MiningResult) -> None:
        sql = """
            INSERT INTO bop_mining (tenant_id, process_id, data)
            VALUES (%s, %s, %s)
            ON CONFLICT (tenant_id, process_id) DO UPDATE SET data = EXCLUDED.data
        """
        async with get_async_cursor() as cur:
            await cur.execute(sql, (tenant_id, result.process_id, _blob(result)))

    async def get_mining_result(
        self, tenant_id: str, process_id: str
    ) -> MiningResult | None:
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore
            await cur.execute(
                "SELECT data FROM bop_mining WHERE tenant_id = %s AND process_id = %s",
                (tenant_id, process_id),
            )
            row = await cur.fetchone()
        return MiningResult.model_validate(row["data"]) if row else None

    # -- Event log + SLAs --------------------------------------------------

    async def save_event_log(
        self, tenant_id: str, process_id: str, events: list[Event]
    ) -> int:
        """Replace the retained event log (most-recent window) for a process."""
        window = events[-MAX_EVENTS_PER_PROCESS:]
        payload = Jsonb([e.model_dump(mode="json") for e in window])
        sql = """
            INSERT INTO bop_events (tenant_id, process_id, data)
            VALUES (%s, %s, %s)
            ON CONFLICT (tenant_id, process_id) DO UPDATE SET data = EXCLUDED.data
        """
        async with get_async_cursor() as cur:
            await cur.execute(sql, (tenant_id, process_id, payload))
        return len(window)

    async def get_event_log(self, tenant_id: str, process_id: str) -> list[Event]:
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore
            await cur.execute(
                "SELECT data FROM bop_events WHERE tenant_id = %s AND process_id = %s",
                (tenant_id, process_id),
            )
            row = await cur.fetchone()
        if not row:
            return []
        return [Event.model_validate(e) for e in row["data"]]

    async def save_sla(self, tenant_id: str, sla: SlaDefinition) -> SlaDefinition:
        sql = """
            INSERT INTO bop_slas (tenant_id, id, process_id, data)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (tenant_id, id) DO UPDATE SET data = EXCLUDED.data
        """
        async with get_async_cursor() as cur:
            await cur.execute(sql, (tenant_id, sla.id, sla.process_id, _blob(sla)))
        return sla

    async def get_sla(self, tenant_id: str, sla_id: str) -> SlaDefinition | None:
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore
            await cur.execute(
                "SELECT data FROM bop_slas WHERE tenant_id = %s AND id = %s",
                (tenant_id, sla_id),
            )
            row = await cur.fetchone()
        return SlaDefinition.model_validate(row["data"]) if row else None

    async def list_slas(
        self, tenant_id: str, process_id: str | None = None
    ) -> list[SlaDefinition]:
        params: tuple[Any, ...] = (tenant_id,)
        sql = "SELECT data FROM bop_slas WHERE tenant_id = %s"
        if process_id is not None:
            sql += " AND process_id = %s"
            params = (tenant_id, process_id)
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore
            await cur.execute(sql, params)
            rows = await cur.fetchall()
        return [SlaDefinition.model_validate(r["data"]) for r in rows]

    async def delete_sla(self, tenant_id: str, sla_id: str) -> bool:
        async with get_async_cursor(row_factory=dict_row) as cur:  # type: ignore
            await cur.execute(
                "DELETE FROM bop_slas WHERE tenant_id = %s AND id = %s RETURNING id",
                (tenant_id, sla_id),
            )
            return await cur.fetchone() is not None


__all__ = ["PostgresProcessStore"]
