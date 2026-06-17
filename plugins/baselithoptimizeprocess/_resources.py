"""Resource-management mixin for :class:`BopService`.

Owns the tenant-scoped resource pool (CRUD) and the act of assigning a resource
to a process step. Assignment is where the resource becomes the source of truth
for a step's economics: :func:`apply_resource_costs` materializes the resource's
rate/role onto the node, a new immutable version is minted, and the graph is
re-synced — so cost rollups and simulation immediately reflect real numbers.

When a resource's rate (or role) changes, :meth:`update_resource` re-materializes
every process that references it within the tenant, keeping derived node costs in
lock-step with the pool without the pure cost layer ever needing a resource
lookup. Depends only on ``self._store`` + tenant/actor context and the sibling
governance/graph-sync mixins (reached via ``cast``), so it composes cleanly.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, cast

from .models import ProcessGraph
from .resources import Resource, apply_resource_costs, resource_map
from .store import ProcessStore
from .tenancy import current_tenant
from .versioning_models import AuditAction

if TYPE_CHECKING:  # reach sibling-mixin methods (_record_save, _sync_graph, _audit)
    from .service import BopService


def _utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(timezone.utc)


class ResourceMixin:
    """Resource pool CRUD + step assignment behaviour for the BOP service."""

    _store: ProcessStore

    # -- Reads -------------------------------------------------------------

    async def list_resources(self) -> list[Resource]:
        """List the tenant's resource pool."""
        return await self._store.list_resources(current_tenant())

    async def get_resource(self, resource_id: str) -> Resource | None:
        """Fetch one resource by id, or None if unknown."""
        return await self._store.get_resource(current_tenant(), resource_id)

    # -- Writes ------------------------------------------------------------

    async def create_resource(self, resource: Resource) -> Resource:
        """Persist a new resource and audit the creation."""
        tenant = current_tenant()
        saved = await self._store.save_resource(tenant, resource)
        await cast("BopService", self)._audit(
            tenant, AuditAction.RESOURCE_CREATE, "resource", saved.id, "", saved.name
        )
        return saved

    async def update_resource(
        self, resource_id: str, patch: dict[str, object]
    ) -> Resource | None:
        """Update a resource and re-materialize the processes that use it.

        Only the supplied fields change; ``updated_at`` is refreshed. If the rate
        or role moved, every process with a node assigned to this resource is
        re-costed and re-saved so derived node economics never drift from the
        pool. Returns the updated resource, or None when the id is unknown.
        """
        tenant = current_tenant()
        existing = await self._store.get_resource(tenant, resource_id)
        if existing is None:
            return None
        updated = existing.model_copy(update={**patch, "updated_at": _utcnow()})
        saved = await self._store.save_resource(tenant, updated)
        await cast("BopService", self)._audit(
            tenant, AuditAction.RESOURCE_UPDATE, "resource", saved.id, "", saved.name
        )
        if saved.cost_per_hour != existing.cost_per_hour or saved.role != existing.role:
            await self._repropagate(tenant, saved)
        return saved

    async def delete_resource(self, resource_id: str) -> bool:
        """Delete a resource and unassign it from any step that referenced it."""
        tenant = current_tenant()
        existing = await self._store.get_resource(tenant, resource_id)
        deleted = await self._store.delete_resource(tenant, resource_id)
        if deleted:
            await self._unassign_everywhere(tenant, resource_id)
            await cast("BopService", self)._audit(
                tenant,
                AuditAction.RESOURCE_DELETE,
                "resource",
                resource_id,
                "",
                existing.name if existing else "",
            )
        return deleted

    async def assign_resource(
        self, process_id: str, node_id: str, resource_id: str | None
    ) -> ProcessGraph | None:
        """Assign (or clear, when ``resource_id`` is None) a step's resource.

        Returns the updated process, or None if the process or node is unknown.
        """
        tenant = current_tenant()
        process = await self._store.get_process(tenant, process_id)
        if process is None:
            return None
        node = next((n for n in process.nodes if n.id == node_id), None)
        if node is None:
            return None
        if resource_id and await self._store.get_resource(tenant, resource_id) is None:
            return None
        node.resource_id = resource_id or None
        await self._materialize_resources(tenant, process)
        saved = await self._store.save_process(tenant, process)
        action = (
            AuditAction.RESOURCE_ASSIGN
            if resource_id
            else AuditAction.RESOURCE_UNASSIGN
        )
        svc = cast("BopService", self)
        await svc._record_save(tenant, saved, action)
        await svc._sync_graph(tenant, saved)
        return saved

    # -- Internals ---------------------------------------------------------

    async def _materialize_resources(
        self, tenant: str, graph: ProcessGraph
    ) -> ProcessGraph:
        """Derive assigned resources' rate/role onto a graph's nodes (in place)."""
        resources = await self._store.list_resources(tenant)
        return apply_resource_costs(graph, resource_map(resources))

    async def _repropagate(self, tenant: str, resource: Resource) -> None:
        """Re-cost and persist every process that references a changed resource."""
        mapping = {resource.id: resource}
        for process in await self._store.list_processes(tenant):
            if any(n.resource_id == resource.id for n in process.nodes):
                apply_resource_costs(process, mapping)
                await self._store.save_process(tenant, process)
                await cast("BopService", self)._sync_graph(tenant, process)

    async def _unassign_everywhere(self, tenant: str, resource_id: str) -> None:
        """Clear a deleted resource's id from every step that still references it."""
        for process in await self._store.list_processes(tenant):
            touched = False
            for node in process.nodes:
                if node.resource_id == resource_id:
                    node.resource_id = None
                    touched = True
            if touched:
                await self._store.save_process(tenant, process)
                await cast("BopService", self)._sync_graph(tenant, process)


__all__ = ["ResourceMixin"]
