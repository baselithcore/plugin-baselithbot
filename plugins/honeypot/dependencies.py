"""Dependency injection utilities for Honeypot plugin.

Provides FastAPI dependency functions for injecting services into route handlers.
"""

from typing import TYPE_CHECKING

from fastapi import HTTPException

from core.di import ServiceRegistry, ServiceNotFoundError

if TYPE_CHECKING:
    from .swarm.coordinator import HoneypotSwarmCoordinator


async def get_coordinator_dependency() -> "HoneypotSwarmCoordinator":
    """FastAPI dependency for obtaining the coordinator from DI container.

    Returns:
        HoneypotSwarmCoordinator: The global coordinator instance

    Raises:
        HTTPException: If coordinator is not initialized or not found

    Usage:
        @router.get("/status")
        async def get_status(
            coordinator: HoneypotSwarmCoordinator = Depends(get_coordinator_dependency)
        ):
            return await coordinator.get_status()
    """
    try:
        # Import here to avoid circular dependency
        from .swarm.coordinator import HoneypotSwarmCoordinator

        coordinator = ServiceRegistry.get(HoneypotSwarmCoordinator)
        if coordinator is None:
            raise HTTPException(
                status_code=503, detail="Honeypot coordinator not initialized"
            )
        return coordinator
    except ServiceNotFoundError:
        raise HTTPException(
            status_code=503,
            detail="Honeypot coordinator not registered. Plugin may not be initialized.",
        )
    except Exception as e:
        raise HTTPException(
            status_code=503, detail=f"Failed to resolve coordinator: {str(e)}"
        )


__all__ = [
    "get_coordinator_dependency",
]
