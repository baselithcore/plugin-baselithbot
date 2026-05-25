"""Internal metrics endpoint (cache hit ratio etc.)."""

from typing import Any

from fastapi import APIRouter, Depends

from ..core.security import Principal
from ..services.cache import get_metrics
from .deps import current_principal

router = APIRouter()


@router.get("/metrics/cache")
async def cache_metrics(_: Principal = Depends(current_principal)) -> dict[str, Any]:
    return get_metrics()
