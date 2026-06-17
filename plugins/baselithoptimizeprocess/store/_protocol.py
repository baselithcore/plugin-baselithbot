"""The :class:`ProcessStore` persistence contract shared by every backend.

The domain talks to this small Protocol, never to a concrete backend. Both the
in-memory default and the durable Postgres implementation satisfy it, so the
service, agent, and router stay backend-agnostic (Dogma III). Every method is
``async`` (Dogma I) even where an in-memory impl could be synchronous, so a real
I/O backend never ripples through callers.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

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

# Per-(process, kpi) ring buffer size. Bounds the read window; recent samples win.
MAX_SAMPLES_PER_SERIES = 512
# Per-process automation-firing history cap.
MAX_FIRINGS_PER_PROCESS = 200
# Per-process retained event-log window (bounds memory; recent events win). The
# insight engines (variants, performance, root-cause) analyse this window.
MAX_EVENTS_PER_PROCESS = 20000


@runtime_checkable
class ProcessStore(Protocol):
    """Abstract persistence contract for processes, metrics, and proposals."""

    async def initialize(self) -> None:
        """Prepare the backend (e.g. create schema). No-op for in-memory."""
        ...

    async def save_process(self, tenant_id: str, process: ProcessGraph) -> ProcessGraph:
        """Insert or replace a process graph within a tenant."""
        ...

    async def get_process(self, tenant_id: str, process_id: str) -> ProcessGraph | None:
        """Fetch a tenant's process by id, or None if unknown."""
        ...

    async def list_processes(self, tenant_id: str) -> list[ProcessGraph]:
        """Return all processes registered within a tenant."""
        ...

    async def delete_process(self, tenant_id: str, process_id: str) -> bool:
        """Delete a tenant's process and derived state; True if it existed."""
        ...

    async def save_resource(self, tenant_id: str, resource: Resource) -> Resource:
        """Insert or replace a resource within a tenant's pool."""
        ...

    async def get_resource(self, tenant_id: str, resource_id: str) -> Resource | None:
        """Fetch a tenant's resource by id, or None if unknown."""
        ...

    async def list_resources(self, tenant_id: str) -> list[Resource]:
        """Return all resources in a tenant's pool."""
        ...

    async def delete_resource(self, tenant_id: str, resource_id: str) -> bool:
        """Delete a tenant's resource; True if it existed."""
        ...

    async def add_samples(self, tenant_id: str, samples: list[MetricSample]) -> int:
        """Append metric samples to a tenant; return the count accepted."""
        ...

    async def recent_samples(
        self, tenant_id: str, process_id: str, kpi_id: str
    ) -> list[MetricSample]:
        """Return the recent sample window for one KPI series in a tenant."""
        ...

    async def save_proposal(
        self, tenant_id: str, proposal: OptimizationProposal
    ) -> OptimizationProposal:
        """Insert or replace an optimization proposal within a tenant."""
        ...

    async def get_proposal(
        self, tenant_id: str, proposal_id: str
    ) -> OptimizationProposal | None:
        """Fetch a tenant's proposal by id, or None if unknown."""
        ...

    async def list_proposals(
        self, tenant_id: str, process_id: str | None = None
    ) -> list[OptimizationProposal]:
        """List a tenant's proposals, optionally filtered to one process."""
        ...

    async def save_bottlenecks(
        self, tenant_id: str, process_id: str, bottlenecks: list[Bottleneck]
    ) -> None:
        """Replace the latest known bottlenecks for a tenant's process."""
        ...

    async def list_bottlenecks(
        self, tenant_id: str, process_id: str
    ) -> list[Bottleneck]:
        """Return the latest known bottlenecks for a tenant's process."""
        ...

    async def save_rule(self, tenant_id: str, rule: AutomationRule) -> AutomationRule:
        """Insert or replace an automation rule within a tenant."""
        ...

    async def get_rule(self, tenant_id: str, rule_id: str) -> AutomationRule | None:
        """Fetch a tenant's automation rule by id."""
        ...

    async def list_rules(
        self, tenant_id: str, process_id: str | None = None
    ) -> list[AutomationRule]:
        """List a tenant's automation rules, optionally filtered to one process."""
        ...

    async def delete_rule(self, tenant_id: str, rule_id: str) -> bool:
        """Delete a tenant's automation rule; True if it existed."""
        ...

    async def add_firings(self, tenant_id: str, firings: list[RuleFiring]) -> None:
        """Append automation-rule firings to a tenant's process history."""
        ...

    async def list_firings(self, tenant_id: str, process_id: str) -> list[RuleFiring]:
        """Return recent automation-rule firings for a tenant's process."""
        ...

    async def save_mining_result(self, tenant_id: str, result: MiningResult) -> None:
        """Store the latest mining analytics for a tenant's process."""
        ...

    async def get_mining_result(
        self, tenant_id: str, process_id: str
    ) -> MiningResult | None:
        """Fetch the latest mining analytics for a tenant's process."""
        ...

    async def save_event_log(
        self, tenant_id: str, process_id: str, events: list[Event]
    ) -> int:
        """Replace a process's retained event log; return the count stored."""
        ...

    async def get_event_log(self, tenant_id: str, process_id: str) -> list[Event]:
        """Return the retained event-log window for a tenant's process."""
        ...

    async def save_sla(self, tenant_id: str, sla: SlaDefinition) -> SlaDefinition:
        """Insert or replace a service-level agreement within a tenant."""
        ...

    async def get_sla(self, tenant_id: str, sla_id: str) -> SlaDefinition | None:
        """Fetch a tenant's SLA definition by id, or None if unknown."""
        ...

    async def list_slas(
        self, tenant_id: str, process_id: str | None = None
    ) -> list[SlaDefinition]:
        """List a tenant's SLAs, optionally filtered to one process."""
        ...

    async def delete_sla(self, tenant_id: str, sla_id: str) -> bool:
        """Delete a tenant's SLA definition; True if it existed."""
        ...

    async def add_version(
        self, tenant_id: str, version: ProcessVersion
    ) -> ProcessVersion:
        """Append an immutable process version snapshot."""
        ...

    async def list_versions(
        self, tenant_id: str, process_id: str
    ) -> list[ProcessVersion]:
        """List a process's versions, newest first."""
        ...

    async def get_version(
        self, tenant_id: str, process_id: str, version: int
    ) -> ProcessVersion | None:
        """Fetch one numbered version of a process."""
        ...

    async def latest_version(
        self, tenant_id: str, process_id: str
    ) -> ProcessVersion | None:
        """Return the most recent version of a process, or None."""
        ...

    async def add_audit(self, tenant_id: str, event: AuditEvent) -> None:
        """Append an immutable audit event."""
        ...

    async def list_audit(
        self, tenant_id: str, process_id: str | None = None, limit: int = 100
    ) -> list[AuditEvent]:
        """List recent audit events, newest first, optionally per process."""
        ...

    async def save_change(self, tenant_id: str, change: AppliedChange) -> AppliedChange:
        """Insert or update an applied-change record."""
        ...

    async def get_change(self, tenant_id: str, change_id: str) -> AppliedChange | None:
        """Fetch an applied change by id."""
        ...

    async def list_changes(
        self, tenant_id: str, process_id: str
    ) -> list[AppliedChange]:
        """List a process's applied changes, newest first."""
        ...


__all__ = [
    "ProcessStore",
    "MAX_SAMPLES_PER_SERIES",
    "MAX_FIRINGS_PER_PROCESS",
    "MAX_EVENTS_PER_PROCESS",
]
