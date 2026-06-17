"""In-memory :class:`ProcessStore` implementation (the zero-config default).

Backed by plain dicts plus per-series ring buffers, guarded by a single
:class:`asyncio.Lock`. Suitable for single-process deployments and tests; state
is not durable across restarts. For durable, multi-replica deployments select
the Postgres backend via :func:`..build_store`.
"""

from __future__ import annotations

import asyncio
from collections import defaultdict, deque

from ..apply_models import AppliedChange
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
from ..versioning_models import AuditEvent, ProcessVersion
from ._protocol import (
    MAX_EVENTS_PER_PROCESS,
    MAX_FIRINGS_PER_PROCESS,
    MAX_SAMPLES_PER_SERIES,
)

# Per-tenant audit ring buffer cap (append-only ledger; bounds memory).
_MAX_AUDIT_PER_TENANT = 1000


class InMemoryProcessStore:
    """Thread/async-safe in-memory implementation of :class:`ProcessStore`."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        # All keys are tenant-scoped tuples so tenants never see each other's
        # state, mirroring the row-level isolation of the Postgres backend.
        self._processes: dict[tuple[str, str], ProcessGraph] = {}
        self._samples: dict[tuple[str, str, str], deque[MetricSample]] = defaultdict(
            lambda: deque(maxlen=MAX_SAMPLES_PER_SERIES)
        )
        self._proposals: dict[tuple[str, str], OptimizationProposal] = {}
        self._bottlenecks: dict[tuple[str, str], list[Bottleneck]] = {}
        self._rules: dict[tuple[str, str], AutomationRule] = {}
        self._firings: dict[tuple[str, str], deque[RuleFiring]] = defaultdict(
            lambda: deque(maxlen=MAX_FIRINGS_PER_PROCESS)
        )
        self._mining: dict[tuple[str, str], MiningResult] = {}
        self._events: dict[tuple[str, str], deque[Event]] = defaultdict(
            lambda: deque(maxlen=MAX_EVENTS_PER_PROCESS)
        )
        self._slas: dict[tuple[str, str], SlaDefinition] = {}
        self._versions: dict[tuple[str, str], list[ProcessVersion]] = defaultdict(list)
        self._audit: dict[str, deque[AuditEvent]] = defaultdict(
            lambda: deque(maxlen=_MAX_AUDIT_PER_TENANT)
        )
        self._changes: dict[tuple[str, str], AppliedChange] = {}
        self._resources: dict[tuple[str, str], Resource] = {}

    async def initialize(self) -> None:
        """No schema to prepare for the in-memory backend."""
        return None

    async def save_process(self, tenant_id: str, process: ProcessGraph) -> ProcessGraph:
        async with self._lock:
            self._processes[(tenant_id, process.id)] = process
            return process

    async def get_process(self, tenant_id: str, process_id: str) -> ProcessGraph | None:
        async with self._lock:
            return self._processes.get((tenant_id, process_id))

    async def list_processes(self, tenant_id: str) -> list[ProcessGraph]:
        async with self._lock:
            return [v for (t, _), v in self._processes.items() if t == tenant_id]

    async def delete_process(self, tenant_id: str, process_id: str) -> bool:
        async with self._lock:
            existed = self._processes.pop((tenant_id, process_id), None) is not None
            self._bottlenecks.pop((tenant_id, process_id), None)
            self._firings.pop((tenant_id, process_id), None)
            self._mining.pop((tenant_id, process_id), None)
            self._events.pop((tenant_id, process_id), None)
            self._versions.pop((tenant_id, process_id), None)  # audit is retained
            for skey in [
                k
                for k, s in self._slas.items()
                if k[0] == tenant_id and s.process_id == process_id
            ]:
                del self._slas[skey]
            for ckey in [
                k
                for k, c in self._changes.items()
                if k[0] == tenant_id and c.process_id == process_id
            ]:
                del self._changes[ckey]
            for key in [
                k for k in self._samples if k[0] == tenant_id and k[1] == process_id
            ]:
                del self._samples[key]
            for pkey in [
                k
                for k, p in self._proposals.items()
                if k[0] == tenant_id and p.process_id == process_id
            ]:
                del self._proposals[pkey]
            for rkey in [
                k
                for k, r in self._rules.items()
                if k[0] == tenant_id and r.process_id == process_id
            ]:
                del self._rules[rkey]
            return existed

    # -- Resources ---------------------------------------------------------

    async def save_resource(self, tenant_id: str, resource: Resource) -> Resource:
        async with self._lock:
            self._resources[(tenant_id, resource.id)] = resource
            return resource

    async def get_resource(self, tenant_id: str, resource_id: str) -> Resource | None:
        async with self._lock:
            return self._resources.get((tenant_id, resource_id))

    async def list_resources(self, tenant_id: str) -> list[Resource]:
        async with self._lock:
            return [v for (t, _), v in self._resources.items() if t == tenant_id]

    async def delete_resource(self, tenant_id: str, resource_id: str) -> bool:
        async with self._lock:
            return self._resources.pop((tenant_id, resource_id), None) is not None

    async def add_samples(self, tenant_id: str, samples: list[MetricSample]) -> int:
        async with self._lock:
            for sample in samples:
                self._samples[(tenant_id, sample.process_id, sample.kpi_id)].append(
                    sample
                )
            return len(samples)

    async def recent_samples(
        self, tenant_id: str, process_id: str, kpi_id: str
    ) -> list[MetricSample]:
        async with self._lock:
            return list(self._samples.get((tenant_id, process_id, kpi_id), ()))

    async def save_proposal(
        self, tenant_id: str, proposal: OptimizationProposal
    ) -> OptimizationProposal:
        async with self._lock:
            self._proposals[(tenant_id, proposal.id)] = proposal
            return proposal

    async def get_proposal(
        self, tenant_id: str, proposal_id: str
    ) -> OptimizationProposal | None:
        async with self._lock:
            return self._proposals.get((tenant_id, proposal_id))

    async def list_proposals(
        self, tenant_id: str, process_id: str | None = None
    ) -> list[OptimizationProposal]:
        async with self._lock:
            values = [v for (t, _), v in self._proposals.items() if t == tenant_id]
        if process_id is None:
            return values
        return [p for p in values if p.process_id == process_id]

    async def save_bottlenecks(
        self, tenant_id: str, process_id: str, bottlenecks: list[Bottleneck]
    ) -> None:
        async with self._lock:
            self._bottlenecks[(tenant_id, process_id)] = list(bottlenecks)

    async def list_bottlenecks(
        self, tenant_id: str, process_id: str
    ) -> list[Bottleneck]:
        async with self._lock:
            return list(self._bottlenecks.get((tenant_id, process_id), ()))

    async def save_rule(self, tenant_id: str, rule: AutomationRule) -> AutomationRule:
        async with self._lock:
            self._rules[(tenant_id, rule.id)] = rule
            return rule

    async def get_rule(self, tenant_id: str, rule_id: str) -> AutomationRule | None:
        async with self._lock:
            return self._rules.get((tenant_id, rule_id))

    async def list_rules(
        self, tenant_id: str, process_id: str | None = None
    ) -> list[AutomationRule]:
        async with self._lock:
            values = [v for (t, _), v in self._rules.items() if t == tenant_id]
        if process_id is None:
            return values
        return [r for r in values if r.process_id == process_id]

    async def delete_rule(self, tenant_id: str, rule_id: str) -> bool:
        async with self._lock:
            return self._rules.pop((tenant_id, rule_id), None) is not None

    async def add_firings(self, tenant_id: str, firings: list[RuleFiring]) -> None:
        async with self._lock:
            for firing in firings:
                self._firings[(tenant_id, firing.process_id)].append(firing)

    async def list_firings(self, tenant_id: str, process_id: str) -> list[RuleFiring]:
        async with self._lock:
            return list(self._firings.get((tenant_id, process_id), ()))

    async def save_mining_result(self, tenant_id: str, result: MiningResult) -> None:
        async with self._lock:
            self._mining[(tenant_id, result.process_id)] = result

    async def get_mining_result(
        self, tenant_id: str, process_id: str
    ) -> MiningResult | None:
        async with self._lock:
            return self._mining.get((tenant_id, process_id))

    # -- Event log + SLAs --------------------------------------------------

    async def save_event_log(
        self, tenant_id: str, process_id: str, events: list[Event]
    ) -> int:
        async with self._lock:
            buffer: deque[Event] = deque(events, maxlen=MAX_EVENTS_PER_PROCESS)
            self._events[(tenant_id, process_id)] = buffer
            return len(buffer)

    async def get_event_log(self, tenant_id: str, process_id: str) -> list[Event]:
        async with self._lock:
            return list(self._events.get((tenant_id, process_id), ()))

    async def save_sla(self, tenant_id: str, sla: SlaDefinition) -> SlaDefinition:
        async with self._lock:
            self._slas[(tenant_id, sla.id)] = sla
            return sla

    async def get_sla(self, tenant_id: str, sla_id: str) -> SlaDefinition | None:
        async with self._lock:
            return self._slas.get((tenant_id, sla_id))

    async def list_slas(
        self, tenant_id: str, process_id: str | None = None
    ) -> list[SlaDefinition]:
        async with self._lock:
            values = [v for (t, _), v in self._slas.items() if t == tenant_id]
        if process_id is None:
            return values
        return [s for s in values if s.process_id == process_id]

    async def delete_sla(self, tenant_id: str, sla_id: str) -> bool:
        async with self._lock:
            return self._slas.pop((tenant_id, sla_id), None) is not None

    # -- Versioning & audit ------------------------------------------------

    async def add_version(
        self, tenant_id: str, version: ProcessVersion
    ) -> ProcessVersion:
        async with self._lock:
            self._versions[(tenant_id, version.process_id)].append(version)
            return version

    async def list_versions(
        self, tenant_id: str, process_id: str
    ) -> list[ProcessVersion]:
        async with self._lock:
            return list(reversed(self._versions.get((tenant_id, process_id), [])))

    async def get_version(
        self, tenant_id: str, process_id: str, version: int
    ) -> ProcessVersion | None:
        async with self._lock:
            for candidate in self._versions.get((tenant_id, process_id), []):
                if candidate.version == version:
                    return candidate
            return None

    async def latest_version(
        self, tenant_id: str, process_id: str
    ) -> ProcessVersion | None:
        async with self._lock:
            versions = self._versions.get((tenant_id, process_id), [])
            return versions[-1] if versions else None

    async def add_audit(self, tenant_id: str, event: AuditEvent) -> None:
        async with self._lock:
            self._audit[tenant_id].append(event)

    async def list_audit(
        self, tenant_id: str, process_id: str | None = None, limit: int = 100
    ) -> list[AuditEvent]:
        async with self._lock:
            events = list(reversed(self._audit.get(tenant_id, ())))
        if process_id is not None:
            events = [e for e in events if e.process_id == process_id]
        return events[: max(0, limit)]

    async def save_change(self, tenant_id: str, change: AppliedChange) -> AppliedChange:
        async with self._lock:
            self._changes[(tenant_id, change.id)] = change
            return change

    async def get_change(self, tenant_id: str, change_id: str) -> AppliedChange | None:
        async with self._lock:
            return self._changes.get((tenant_id, change_id))

    async def list_changes(
        self, tenant_id: str, process_id: str
    ) -> list[AppliedChange]:
        async with self._lock:
            items = [
                c
                for (t, _), c in self._changes.items()
                if t == tenant_id and c.process_id == process_id
            ]
        return sorted(items, key=lambda c: c.applied_at, reverse=True)


__all__ = ["InMemoryProcessStore"]
