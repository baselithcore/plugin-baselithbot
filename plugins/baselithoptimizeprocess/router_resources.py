"""Resource sub-router: the tenant resource pool + step assignment.

Kept separate from the core CRUD/monitoring router so neither file approaches the
size cap. Mounted into the main router via ``include_router``. Thin and async:
validates, delegates to :class:`BopService`, shapes HTTP responses. Resources are
tenant-scoped (process-independent), so CRUD lives at ``/resources`` while the
assignment endpoint targets a specific step under its process.
"""

from __future__ import annotations

import uuid
from typing import Any

from .api_models import (
    AssignResourceRequest,
    ResourceCreateRequest,
    ResourceUpdateRequest,
)
from .models import ProcessGraph
from .resources import Resource
from .service import BopService


def build_resources_router(
    service: BopService, viewer: Any, editor: Any, approver: Any
) -> Any:
    """Build the resource-pool APIRouter bound to the BOP service.

    Args:
        service: The shared BOP service.
        viewer: A FastAPI read gate (no-op unless RBAC is on).
        editor: A FastAPI write gate (no-op unless RBAC is on).
        approver: A FastAPI privileged gate (unused here; kept for symmetry).
    """
    from fastapi import APIRouter, HTTPException, Query, Response

    router = APIRouter(tags=["bop-resources"])

    @router.post(
        "/resources",
        response_model=Resource,
        status_code=201,
        dependencies=[editor],
    )
    async def create_resource(body: ResourceCreateRequest) -> Resource:
        """Add a resource to the tenant pool."""
        resource = Resource(
            id=body.id or uuid.uuid4().hex,
            name=body.name,
            role=body.role,
            cost_per_hour=body.cost_per_hour,
            currency=body.currency,
            capacity_hours_per_week=body.capacity_hours_per_week,
            skills=body.skills,
            active=body.active,
            metadata=body.metadata,
        )
        return await service.create_resource(resource)

    @router.get(
        "/resources",
        response_model=list[Resource],
        dependencies=[viewer],
    )
    async def list_resources(
        response: Response,
        limit: int | None = Query(default=None, ge=1, le=1000),
        offset: int = Query(default=0, ge=0),
    ) -> list[Resource]:
        """List the tenant's resource pool (paginated; total in ``X-Total-Count``)."""
        resources = await service.list_resources()
        response.headers["X-Total-Count"] = str(len(resources))
        window = resources[offset:] if offset else resources
        return window[:limit] if limit is not None else window

    @router.get(
        "/resources/{resource_id}",
        response_model=Resource,
        dependencies=[viewer],
    )
    async def get_resource(resource_id: str) -> Resource:
        """Fetch a single resource by id."""
        resource = await service.get_resource(resource_id)
        if resource is None:
            raise HTTPException(status_code=404, detail="resource not found")
        return resource

    @router.put(
        "/resources/{resource_id}",
        response_model=Resource,
        dependencies=[editor],
    )
    async def update_resource(
        resource_id: str, body: ResourceUpdateRequest
    ) -> Resource:
        """Update a resource; a rate/role change re-costs the processes using it."""
        patch = body.model_dump(exclude_none=True)
        updated = await service.update_resource(resource_id, patch)
        if updated is None:
            raise HTTPException(status_code=404, detail="resource not found")
        return updated

    @router.delete("/resources/{resource_id}", dependencies=[editor])
    async def delete_resource(resource_id: str) -> dict[str, str]:
        """Delete a resource and unassign it from every step that used it."""
        if not await service.delete_resource(resource_id):
            raise HTTPException(status_code=404, detail="resource not found")
        return {"deleted": resource_id}

    @router.post(
        "/processes/{process_id}/nodes/{node_id}/resource",
        response_model=ProcessGraph,
        dependencies=[editor],
    )
    async def assign_resource(
        process_id: str, node_id: str, body: AssignResourceRequest
    ) -> ProcessGraph:
        """Assign (or clear) the resource on a process step."""
        process = await service.assign_resource(process_id, node_id, body.resource_id)
        if process is None:
            raise HTTPException(
                status_code=404, detail="process, step, or resource not found"
            )
        return process

    return router


__all__ = ["build_resources_router"]
