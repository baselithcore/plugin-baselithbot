"""Dependency injection utilities for CVE Hunter plugin.

Provides FastAPI dependency functions for injecting services into route handlers.
"""

from typing import TYPE_CHECKING

from fastapi import HTTPException

from core.di import ServiceRegistry, ServiceNotFoundError

if TYPE_CHECKING:
    from .swarm.coordinator import CVEHunterSwarm


async def get_swarm_dependency() -> "CVEHunterSwarm":
    """FastAPI dependency for obtaining the CVE Hunter swarm from DI container.

    Returns:
        CVEHunterSwarm: The swarm coordinator instance

    Raises:
        HTTPException: If swarm is not initialized or not found

    Usage:
        @router.get("/status")
        async def get_status(
            swarm: CVEHunterSwarm = Depends(get_swarm_dependency)
        ):
            return await swarm.get_status()
    """
    try:
        # Import here to avoid circular dependency
        from .swarm.coordinator import CVEHunterSwarm

        swarm = ServiceRegistry.get(CVEHunterSwarm)
        if swarm is None:
            raise HTTPException(
                status_code=503, detail="CVE Hunter swarm not initialized"
            )
        return swarm
    except ServiceNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="CVE Hunter swarm not registered. Plugin may not be initialized.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"Failed to resolve CVE Hunter swarm: {str(e)}"
        )


__all__ = [
    "get_swarm_dependency",
]
