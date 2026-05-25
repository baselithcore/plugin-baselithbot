"""Sinkhole WebSocket Routes.

Real-time updates for sinkhole monitoring.
"""

from core.observability.logging import get_logger

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ..services.websocket_manager import get_connection_manager

logger = get_logger(__name__)

router = APIRouter(
    prefix="/sinkhole/ws",
    tags=["sinkhole-websocket"],
)


@router.websocket("/updates")
async def websocket_global_updates(websocket: WebSocket):
    """WebSocket endpoint for global sinkhole updates.

    Riceve tutti gli eventi di tutti i domini sinkholed.
    Utile per dashboard globale.
    """
    manager = get_connection_manager()
    await manager.connect(websocket, domain_id=None)

    try:
        # Send initial connection confirmation
        await websocket.send_json(
            {
                "event": "connected",
                "message": "Connected to global sinkhole updates",
            }
        )

        # Keep connection alive and handle client messages
        while True:
            # Wait for client messages (mostly keep-alive pings)
            data = await websocket.receive_text()

            # Handle ping/pong
            if data == "ping":
                await websocket.send_json({"event": "pong"})

    except WebSocketDisconnect:
        logger.info("Global WebSocket disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        await manager.disconnect(websocket, domain_id=None)


@router.websocket("/domain/{domain_id}")
async def websocket_domain_updates(
    websocket: WebSocket,
    domain_id: int,
):
    """WebSocket endpoint for domain-specific updates.

    Riceve solo eventi relativi a un domain specifico.

    Args:
        domain_id: Sinkholed domain ID to subscribe to
    """
    manager = get_connection_manager()
    await manager.connect(websocket, domain_id=domain_id)

    try:
        # Send initial connection confirmation
        await websocket.send_json(
            {
                "event": "connected",
                "message": f"Connected to updates for domain {domain_id}",
                "domain_id": domain_id,
            }
        )

        # Keep connection alive
        while True:
            data = await websocket.receive_text()

            # Handle ping/pong
            if data == "ping":
                await websocket.send_json({"event": "pong"})

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for domain {domain_id}")
    except Exception as e:
        logger.error(f"WebSocket error for domain {domain_id}: {e}")
    finally:
        await manager.disconnect(websocket, domain_id=domain_id)


@router.get("/connections/stats")
async def get_connection_stats():
    """Get WebSocket connection statistics.

    Returns:
        Dictionary with connection counts
    """
    manager = get_connection_manager()

    domain_stats = {}
    for domain_id in list(manager.active_connections.keys()):
        domain_stats[domain_id] = manager.get_connection_count(domain_id)

    return {
        "total_connections": manager.get_connection_count(),
        "global_connections": len(manager.global_connections),
        "domain_connections": domain_stats,
    }
