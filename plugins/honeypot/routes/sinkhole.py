"""Sinkhole API Routes.

Endpoints for managing sinkholed domains.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from core.auth import AuthRole
from plugins.auth.dependencies import require_roles

from ..persistence.sinkhole_dao import SinkholeDAO
from ..models.sinkhole import SinkholeStatus

router = APIRouter(
    prefix="/sinkhole",
    tags=["sinkhole"],
    dependencies=[Depends(require_roles(AuthRole.ADMIN, AuthRole.USER))],
)

# ============================================================================
# Request/Response Models
# ============================================================================


class CreateSinkholeRequest(BaseModel):
    """Request to create a new sinkholed domain."""

    domain: str = Field(..., description="Domain name to sinkhole")
    anomaly_id: Optional[str] = Field(None, description="Associated anomaly ID")
    detection_method: str = Field("dga", description="Detection method")
    entropy: Optional[float] = Field(None, ge=0, le=5, description="Shannon entropy")
    confidence: float = Field(..., ge=0, le=1, description="Detection confidence")
    redirect_target: Optional[str] = Field(None, description="Honeypot target")
    associated_cluster_id: Optional[str] = Field(None, description="Cluster ID")
    tags: List[str] = Field(default_factory=list, description="Detection tags")
    notes: Optional[str] = Field(None, description="Admin notes")


class UpdateSinkholeStatusRequest(BaseModel):
    """Request to update sinkhole status."""

    status: SinkholeStatus = Field(..., description="New status")


class SinkholeResponse(BaseModel):
    """Sinkhole domain response."""

    id: int
    domain: str
    anomaly_id: Optional[str]
    detection_method: str
    entropy: Optional[float]
    confidence: float
    status: str
    redirect_target: Optional[str]
    request_count: int
    unique_ips_count: int
    unique_ips: List[str]
    first_seen: Optional[str]
    last_activity: Optional[str]
    associated_cluster_id: Optional[str]
    tags: List[str]
    notes: Optional[str]
    created_at: Optional[str]
    activated_at: Optional[str]
    updated_at: Optional[str]


class ActivityLogResponse(BaseModel):
    """Sinkhole activity log response."""

    id: int
    sinkholed_domain_id: int
    source_ip: str
    timestamp: Optional[str]
    request_type: Optional[str]
    payload: Optional[str]
    user_agent: Optional[str]
    honeypot_id: Optional[str]
    response_type: Optional[str]
    created_at: Optional[str]


class SinkholeStatsResponse(BaseModel):
    """Sinkhole statistics response."""

    total_domains: int
    active: int
    paused: int
    terminated: int
    total_requests: int


# ============================================================================
# Dependency: Get DAO
# ============================================================================


def get_dao() -> SinkholeDAO:
    """Get SinkholeDAO instance."""
    return SinkholeDAO()


# ============================================================================
# Endpoints
# ============================================================================


@router.post("/domains", response_model=SinkholeResponse, status_code=201)
async def create_sinkhole(
    request: CreateSinkholeRequest,
    dao: SinkholeDAO = Depends(get_dao),
) -> SinkholeResponse:
    """Create a new sinkholed domain.

    Creates an entry for a domain to be sinkholed, typically from DGA detection.
    Default status is PAUSED until explicitly activated.
    """
    try:
        sinkholed = dao.create_sinkholed_domain(
            domain=request.domain,
            anomaly_id=request.anomaly_id,
            detection_method=request.detection_method,
            entropy=request.entropy,
            confidence=request.confidence,
            status=SinkholeStatus.PAUSED,  # Always start paused
            redirect_target=request.redirect_target,
            associated_cluster_id=request.associated_cluster_id,
            tags=request.tags,
            notes=request.notes,
        )
        return SinkholeResponse(**sinkholed.to_dict())
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create sinkhole: {e}")


@router.get("/domains", response_model=List[SinkholeResponse])
async def list_sinkholes(
    status: Optional[SinkholeStatus] = Query(None, description="Filter by status"),
    cluster_id: Optional[str] = Query(None, description="Filter by cluster"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    dao: SinkholeDAO = Depends(get_dao),
) -> List[SinkholeResponse]:
    """List sinkholed domains with optional filters."""
    try:
        domains = dao.list_sinkholed_domains(
            status=status,
            cluster_id=cluster_id,
            limit=limit,
            offset=offset,
        )
        return [SinkholeResponse(**d.to_dict()) for d in domains]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list sinkholes: {e}")


@router.get("/domains/{domain_id}", response_model=SinkholeResponse)
async def get_sinkhole(
    domain_id: int,
    dao: SinkholeDAO = Depends(get_dao),
) -> SinkholeResponse:
    """Get a specific sinkholed domain by ID."""
    domain = dao.get_sinkholed_domain(domain_id)
    if not domain:
        raise HTTPException(status_code=404, detail="Sinkholed domain not found")

    return SinkholeResponse(**domain.to_dict())


@router.patch("/domains/{domain_id}/status", response_model=SinkholeResponse)
async def update_sinkhole_status(
    domain_id: int,
    request: UpdateSinkholeStatusRequest,
    dao: SinkholeDAO = Depends(get_dao),
) -> SinkholeResponse:
    """Update sinkhole status (activate/pause/terminate).

    - ACTIVE: Domain is being actively sinkholed
    - PAUSED: Domain sinkholing is temporarily disabled
    - TERMINATED: Domain sinkholing is permanently disabled
    """
    domain = dao.update_sinkhole_status(domain_id, request.status)
    if not domain:
        raise HTTPException(status_code=404, detail="Sinkholed domain not found")

    return SinkholeResponse(**domain.to_dict())


@router.delete("/domains/{domain_id}", status_code=204)
async def delete_sinkhole(
    domain_id: int,
    dao: SinkholeDAO = Depends(get_dao),
) -> None:
    """Delete a sinkholed domain entry.

    WARNING: This also deletes all associated activity logs.
    """
    success = dao.delete_sinkholed_domain(domain_id)
    if not success:
        raise HTTPException(status_code=404, detail="Sinkholed domain not found")


@router.get("/activity", response_model=List[ActivityLogResponse])
async def list_activity_logs(
    domain_id: Optional[int] = Query(None, description="Filter by domain ID"),
    source_ip: Optional[str] = Query(None, description="Filter by source IP"),
    limit: int = Query(100, ge=1, le=500, description="Max results"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    dao: SinkholeDAO = Depends(get_dao),
) -> List[ActivityLogResponse]:
    """List sinkhole activity logs."""
    try:
        logs = dao.get_activity_logs(
            domain_id=domain_id,
            source_ip=source_ip,
            limit=limit,
            offset=offset,
        )
        return [ActivityLogResponse(**log.to_dict()) for log in logs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch logs: {e}")


@router.get("/stats", response_model=SinkholeStatsResponse)
async def get_sinkhole_stats(
    dao: SinkholeDAO = Depends(get_dao),
) -> SinkholeStatsResponse:
    """Get overall sinkhole statistics."""
    try:
        stats = dao.get_sinkhole_stats()
        return SinkholeStatsResponse(**stats)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch stats: {e}")


# ============================================================================
# Bulk Operations
# ============================================================================


@router.post("/domains/bulk/activate", status_code=200)
async def bulk_activate(
    domain_ids: List[int] = Query(..., description="List of domain IDs to activate"),
    dao: SinkholeDAO = Depends(get_dao),
) -> dict:
    """Bulk activate multiple sinkholes."""
    activated = []
    failed = []

    for domain_id in domain_ids:
        try:
            result = dao.update_sinkhole_status(domain_id, SinkholeStatus.ACTIVE)
            if result:
                activated.append(domain_id)
            else:
                failed.append({"id": domain_id, "reason": "Not found"})
        except Exception as e:
            failed.append({"id": domain_id, "reason": str(e)})

    return {
        "activated": len(activated),
        "failed": len(failed),
        "activated_ids": activated,
        "failed_ids": failed,
    }


@router.post("/domains/bulk/pause", status_code=200)
async def bulk_pause(
    domain_ids: List[int] = Query(..., description="List of domain IDs to pause"),
    dao: SinkholeDAO = Depends(get_dao),
) -> dict:
    """Bulk pause multiple sinkholes."""
    paused = []
    failed = []

    for domain_id in domain_ids:
        try:
            result = dao.update_sinkhole_status(domain_id, SinkholeStatus.PAUSED)
            if result:
                paused.append(domain_id)
            else:
                failed.append({"id": domain_id, "reason": "Not found"})
        except Exception as e:
            failed.append({"id": domain_id, "reason": str(e)})

    return {
        "paused": len(paused),
        "failed": len(failed),
        "paused_ids": paused,
        "failed_ids": failed,
    }
