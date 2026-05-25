"""WebSocket Manager for Real-Time Updates.

Handles WebSocket connections and broadcasts for sinkhole events.
Modulare e riutilizzabile per altri servizi.
"""

import asyncio
from core.observability.logging import get_logger
from datetime import datetime, timezone
from typing import Dict, Set, Optional
from fastapi import WebSocket, WebSocketDisconnect

logger = get_logger(__name__)


class ConnectionManager:
    """Gestisce connessioni WebSocket attive."""

    def __init__(self):
        """Initialize connection manager."""
        # Map: domain_id -> set of connected websockets
        self.active_connections: Dict[int, Set[WebSocket]] = {}
        # Global connections (subscribed to all events)
        self.global_connections: Set[WebSocket] = set()
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, domain_id: Optional[int] = None):
        """Accetta una nuova connessione WebSocket.

        Args:
            websocket: WebSocket connection
            domain_id: Optional domain ID to subscribe to specific domain
        """
        await websocket.accept()

        async with self._lock:
            if domain_id is None:
                # Global subscription
                self.global_connections.add(websocket)
                logger.info("New global WebSocket connection established")
            else:
                # Domain-specific subscription
                if domain_id not in self.active_connections:
                    self.active_connections[domain_id] = set()
                self.active_connections[domain_id].add(websocket)
                logger.info(f"New WebSocket connection for domain {domain_id}")

    async def disconnect(self, websocket: WebSocket, domain_id: Optional[int] = None):
        """Rimuove una connessione WebSocket.

        Args:
            websocket: WebSocket connection
            domain_id: Optional domain ID if was subscribed to specific domain
        """
        async with self._lock:
            if domain_id is None:
                self.global_connections.discard(websocket)
                logger.info("Global WebSocket connection closed")
            else:
                if domain_id in self.active_connections:
                    self.active_connections[domain_id].discard(websocket)
                    # Cleanup empty sets
                    if not self.active_connections[domain_id]:
                        del self.active_connections[domain_id]
                logger.info(f"WebSocket connection closed for domain {domain_id}")

    async def send_to_domain(self, domain_id: int, message: dict):
        """Invia messaggio a tutti i client connessi a un domain specifico.

        Args:
            domain_id: Domain ID
            message: Message dictionary to send
        """
        if domain_id not in self.active_connections:
            return

        disconnected = set()
        connections = self.active_connections[domain_id].copy()

        for connection in connections:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                disconnected.add(connection)
            except Exception as e:
                logger.error(f"Error sending message to WebSocket: {e}")
                disconnected.add(connection)

        # Cleanup disconnected clients
        if disconnected:
            async with self._lock:
                self.active_connections[domain_id] -= disconnected

    async def broadcast_global(self, message: dict):
        """Broadcast a tutti i client connessi globalmente.

        Args:
            message: Message dictionary to broadcast
        """
        if not self.global_connections:
            return

        disconnected = set()
        connections = self.global_connections.copy()

        for connection in connections:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                disconnected.add(connection)
            except Exception as e:
                logger.error(f"Error broadcasting to WebSocket: {e}")
                disconnected.add(connection)

        # Cleanup disconnected clients
        if disconnected:
            async with self._lock:
                self.global_connections -= disconnected

    async def broadcast_all(self, message: dict):
        """Broadcast a TUTTI i client (domain-specific + global).

        Args:
            message: Message dictionary to broadcast
        """
        # Broadcast to global
        await self.broadcast_global(message)

        # Broadcast to all domain-specific
        for domain_id in list(self.active_connections.keys()):
            await self.send_to_domain(domain_id, message)

    def get_connection_count(self, domain_id: Optional[int] = None) -> int:
        """Conta le connessioni attive.

        Args:
            domain_id: Optional domain ID, None for global count

        Returns:
            Number of active connections
        """
        if domain_id is None:
            # Total count
            domain_count = sum(len(conns) for conns in self.active_connections.values())
            return len(self.global_connections) + domain_count
        else:
            return len(self.active_connections.get(domain_id, set()))


# Singleton instance
_manager: Optional[ConnectionManager] = None


def get_connection_manager() -> ConnectionManager:
    """Get or create singleton ConnectionManager instance."""
    global _manager
    if _manager is None:
        _manager = ConnectionManager()
    return _manager


class SinkholeEventBroadcaster:
    """Broadcaster per eventi sinkhole in tempo reale."""

    def __init__(self, manager: Optional[ConnectionManager] = None):
        """Initialize broadcaster.

        Args:
            manager: Optional ConnectionManager instance
        """
        self.manager = manager or get_connection_manager()

    async def broadcast_request_intercepted(
        self,
        domain_id: int,
        domain_name: str,
        source_ip: str,
        request_count: int,
        unique_ips_count: int,
    ):
        """Broadcast quando un sinkhole intercetta una richiesta.

        Args:
            domain_id: Sinkholed domain ID
            domain_name: Domain name
            source_ip: Source IP that made the request
            request_count: Updated total request count
            unique_ips_count: Updated unique IPs count
        """
        message = {
            "event": "request_intercepted",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "domain_id": domain_id,
                "domain": domain_name,
                "source_ip": source_ip,
                "request_count": request_count,
                "unique_ips_count": unique_ips_count,
            },
        }

        # Send to domain-specific subscribers
        await self.manager.send_to_domain(domain_id, message)
        # Also broadcast globally
        await self.manager.broadcast_global(message)

    async def broadcast_status_changed(
        self, domain_id: int, domain_name: str, old_status: str, new_status: str
    ):
        """Broadcast quando lo status di un sinkhole cambia.

        Args:
            domain_id: Sinkholed domain ID
            domain_name: Domain name
            old_status: Previous status
            new_status: New status
        """
        message = {
            "event": "status_changed",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "domain_id": domain_id,
                "domain": domain_name,
                "old_status": old_status,
                "new_status": new_status,
            },
        }

        await self.manager.send_to_domain(domain_id, message)
        await self.manager.broadcast_global(message)

    async def broadcast_domain_created(
        self, domain_id: int, domain_name: str, confidence: float
    ):
        """Broadcast quando un nuovo domain viene sinkholed.

        Args:
            domain_id: New sinkholed domain ID
            domain_name: Domain name
            confidence: Detection confidence
        """
        message = {
            "event": "domain_created",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {
                "domain_id": domain_id,
                "domain": domain_name,
                "confidence": confidence,
            },
        }

        await self.manager.broadcast_global(message)

    async def broadcast_stats_updated(self, stats: dict):
        """Broadcast quando le statistiche generali vengono aggiornate.

        Args:
            stats: Statistics dictionary
        """
        message = {
            "event": "stats_updated",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": stats,
        }

        await self.manager.broadcast_global(message)


def get_broadcaster() -> SinkholeEventBroadcaster:
    """Get SinkholeEventBroadcaster instance."""
    return SinkholeEventBroadcaster()
