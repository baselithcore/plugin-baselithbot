"""Honeypot Real-Time Streaming.

Provides Server-Sent Events (SSE) endpoints for real-time
attack visualization and geo data streaming.
"""

import asyncio
import json
from core.observability.logging import get_logger
from datetime import datetime, timezone
from typing import Any, AsyncGenerator, Dict, List, Optional

from .geo import get_geo_service
from .models import AttackEvent, DiscoveryLog

logger = get_logger(__name__)


class AttackStreamManager:
    """Manages real-time attack event streaming."""

    def __init__(self, max_history: int = 100):
        """Initialize stream manager.

        Args:
            max_history: Maximum events to keep in history
        """
        self._subscribers: List[asyncio.Queue] = []
        self._history: List[Dict[str, Any]] = []
        self._max_history = max_history
        self._geo_service = get_geo_service()
        # Default honeypot location (can be configured)
        self._honeypot_location = {"lat": 41.9028, "lng": 12.4964}  # Rome, Italy

    def set_honeypot_location(self, lat: float, lng: float) -> None:
        """Set the honeypot's geographic location for visualization.

        Args:
            lat: Latitude
            lng: Longitude
        """
        self._honeypot_location = {"lat": lat, "lng": lng}

    async def broadcast(self, event: AttackEvent) -> None:
        """Broadcast attack event to all subscribers.

        Args:
            event: Attack event to broadcast
        """
        # Enrich with geo data
        geo_data = await self._enrich_with_geo(event)

        # Create stream payload
        payload = {
            "type": "attack",
            "data": {
                "id": event.event_id,
                "session_id": event.session_id,
                "honeypot_id": event.honeypot_id,
                "protocol": event.protocol.value
                if hasattr(event.protocol, "value")
                else str(event.protocol),
                "source_ip": event.source_ip,
                "source": geo_data.get("source"),
                "target": self._honeypot_location,
                "severity": event.severity.value
                if hasattr(event.severity, "value")
                else str(event.severity),
                "category": event.category.value
                if hasattr(event.category, "value")
                else str(event.category),
                "patterns": event.detected_patterns,
                "command": event.command,
                "http_path": event.http_path,
                "timestamp": event.timestamp.isoformat()
                if event.timestamp
                else datetime.now(timezone.utc).isoformat(),
            },
        }

        # Add to history
        self._history.append(payload)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

        # Broadcast to all subscribers
        dead_queues = []
        if self._subscribers:
            logger.debug(
                f"Broadcasting event {event.event_id} to {len(self._subscribers)} subscribers"
            )

        for queue in self._subscribers:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                logger.warning("Subscriber queue full, dropping event for one client")
                dead_queues.append(queue)

        # Remove dead queues
        for queue in dead_queues:
            self._subscribers.remove(queue)

    async def broadcast_log(self, log: DiscoveryLog) -> None:
        """Broadcast discovery log to all subscribers.

        Args:
            log: Discovery log to broadcast
        """
        payload = {
            "type": "log",
            "data": {
                "timestamp": log.timestamp.isoformat()
                if log.timestamp
                else datetime.now(timezone.utc).isoformat(),
                "message": log.message,
                "is_alert": log.is_alert,
                "is_error": log.is_error,
                "agent_type": log.agent_type,
            },
        }

        # Broadcast to all subscribers
        dead_queues = []
        if self._subscribers:
            logger.debug(
                f"Broadcasting log to {len(self._subscribers)} subscribers: {log.message[:50]}..."
            )

        for queue in self._subscribers:
            try:
                queue.put_nowait(payload)
            except asyncio.QueueFull:
                dead_queues.append(queue)

        # Remove dead queues
        for queue in dead_queues:
            self._subscribers.remove(queue)

    def clear_history(self) -> None:
        """Clear broadcast history."""
        self._history.clear()
        logger.info("♻️ Stream history cleared")

    async def _enrich_with_geo(self, event: AttackEvent) -> Dict[str, Any]:
        """Enrich event with geographic data.

        Args:
            event: Attack event

        Returns:
            Dict with geo data
        """
        result: Dict[str, Any] = {"source": None}

        try:
            geo = await self._geo_service.lookup(event.source_ip)
            if geo and geo.latitude and geo.longitude:
                result["source"] = {
                    "lat": geo.latitude,
                    "lng": geo.longitude,
                    "country": geo.country,
                    "country_code": geo.country_code,
                    "city": geo.city,
                }
        except Exception as e:
            logger.debug(f"Geo lookup failed for {event.source_ip}: {e}")

        return result

    def subscribe(self) -> asyncio.Queue:
        """Subscribe to attack stream.

        Returns:
            Queue to receive events from
        """
        queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._subscribers.append(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        """Unsubscribe from attack stream.

        Args:
            queue: Queue to remove
        """
        if queue in self._subscribers:
            self._subscribers.remove(queue)

    def get_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent attack history.

        Args:
            limit: Maximum events to return

        Returns:
            List of recent events
        """
        return self._history[-limit:]

    @property
    def subscriber_count(self) -> int:
        """Get number of active subscribers."""
        return len(self._subscribers)


# Global stream manager instance
_stream_manager: Optional[AttackStreamManager] = None


def get_stream_manager() -> AttackStreamManager:
    """Get global stream manager instance."""
    global _stream_manager
    if _stream_manager is None:
        _stream_manager = AttackStreamManager()
    return _stream_manager


async def attack_event_generator(
    queue: asyncio.Queue,
    include_history: bool = True,
) -> AsyncGenerator[str, None]:
    """Generate SSE events for attack stream.

    Args:
        queue: Subscriber queue
        include_history: Whether to send history first

    Yields:
        SSE formatted event strings
    """
    manager = get_stream_manager()

    # Send connection event
    yield f"event: connected\ndata: {json.dumps({'subscribers': manager.subscriber_count})}\n\n"

    # Send history if requested
    if include_history:
        history = manager.get_history()
        for event in history:
            yield f"event: attack\ndata: {json.dumps(event)}\n\n"

    # Stream new events
    try:
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=30.0)
                event_type = event.get("type", "attack")
                # debug log for traffic trace
                # logger.debug(f"Yielding SSE event: {event_type}")
                yield f"event: {event_type}\ndata: {json.dumps(event)}\n\n"
            except asyncio.TimeoutError:
                # Send heartbeat
                yield f"event: heartbeat\ndata: {json.dumps({'time': datetime.now(timezone.utc).isoformat()})}\n\n"
    except asyncio.CancelledError:
        pass
    finally:
        manager.unsubscribe(queue)


class GeoAttackData:
    """Helper class for geo attack visualization data."""

    def __init__(self):
        """Initialize geo attack data helper."""
        self._geo_service = get_geo_service()
        self._attack_flows: List[Dict[str, Any]] = []
        self._country_stats: Dict[str, int] = {}

    async def process_events(
        self,
        events: List[AttackEvent],
        honeypot_location: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """Process events and generate geo visualization data.

        Args:
            events: List of attack events
            honeypot_location: Optional honeypot location override

        Returns:
            Geo visualization data
        """
        target = honeypot_location or {"lat": 41.9028, "lng": 12.4964}
        flows = []
        markers = []
        country_counts: Dict[str, int] = {}

        for event in events:
            try:
                geo = await self._geo_service.lookup(event.source_ip)
                if geo and geo.latitude and geo.longitude:
                    # Create attack flow
                    flow = {
                        "id": event.event_id,
                        "source": {
                            "lat": geo.latitude,
                            "lng": geo.longitude,
                            "country": geo.country,
                            "country_code": geo.country_code,
                            "city": geo.city,
                        },
                        "target": target,
                        "severity": event.severity.value
                        if hasattr(event.severity, "value")
                        else str(event.severity),
                        "protocol": event.protocol.value
                        if hasattr(event.protocol, "value")
                        else str(event.protocol),
                        "timestamp": event.timestamp.isoformat()
                        if event.timestamp
                        else None,
                    }
                    flows.append(flow)

                    # Create marker
                    markers.append(
                        {
                            "lat": geo.latitude,
                            "lng": geo.longitude,
                            "count": 1,
                            "severity": flow["severity"],
                            "country_code": geo.country_code,
                        }
                    )

                    # Count by country
                    if geo.country_code:
                        country_counts[geo.country_code] = (
                            country_counts.get(geo.country_code, 0) + 1
                        )
                else:
                    # Handle unmapped IPs (Localhost, LAN, or lookup failed)
                    is_local = event.source_ip in [
                        "127.0.0.1",
                        "::1",
                        "localhost",
                    ] or event.source_ip.startswith(("192.168.", "10.", "172."))
                    cc = "LAN" if is_local else "UNK"
                    country_counts[cc] = country_counts.get(cc, 0) + 1

                    # Create fallback flow/marker for LAN attacks (near honeypot with offset)
                    # Use slight random-ish offset based on event_id hash for visual spread
                    offset = (hash(event.event_id) % 100) / 100  # 0.0 to 0.99
                    fallback_lat = target["lat"] + (offset - 0.5) * 2  # ±1 degree
                    fallback_lng = target["lng"] + (offset - 0.5) * 3  # ±1.5 degrees

                    flow = {
                        "id": event.event_id,
                        "source": {
                            "lat": fallback_lat,
                            "lng": fallback_lng,
                            "country": "Local Network" if is_local else "Unknown",
                            "country_code": cc,
                            "city": "LAN" if is_local else None,
                        },
                        "source_ip": event.source_ip,
                        "target": target,
                        "severity": event.severity.value
                        if hasattr(event.severity, "value")
                        else str(event.severity),
                        "protocol": event.protocol.value
                        if hasattr(event.protocol, "value")
                        else str(event.protocol),
                        "timestamp": event.timestamp.isoformat()
                        if event.timestamp
                        else None,
                    }
                    flows.append(flow)

                    markers.append(
                        {
                            "lat": fallback_lat,
                            "lng": fallback_lng,
                            "count": 1,
                            "severity": flow["severity"],
                            "country_code": cc,
                        }
                    )

            except Exception as e:
                logger.debug(f"Failed to process geo for event {event.event_id}: {e}")
                continue

        # Aggregate markers by location
        aggregated_markers = self._aggregate_markers(markers)

        # Create heatmap data
        heatmap = [
            {"country_code": code, "count": count, "intensity": min(1.0, count / 10)}
            for code, count in sorted(
                country_counts.items(), key=lambda x: x[1], reverse=True
            )
        ]

        return {
            "flows": flows,
            "markers": aggregated_markers,
            "heatmap": heatmap,
            "target": target,
            "total_attacks": len(events),
            "unique_countries": len(country_counts),
        }

    def _aggregate_markers(self, markers: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Aggregate markers by approximate location.

        Args:
            markers: List of marker data

        Returns:
            Aggregated markers
        """
        # Simple grid-based aggregation
        grid: Dict[str, Dict[str, Any]] = {}
        precision = 1  # 1 degree grid

        for marker in markers:
            grid_key = (
                f"{round(marker['lat'] / precision)},{round(marker['lng'] / precision)}"
            )
            if grid_key not in grid:
                grid[grid_key] = {
                    "lat": marker["lat"],
                    "lng": marker["lng"],
                    "count": 0,
                    "severities": [],
                    "country_code": marker.get("country_code"),
                }
            grid[grid_key]["count"] += 1
            grid[grid_key]["severities"].append(marker["severity"])

        # Determine dominant severity for each aggregated marker
        result = []
        for data in grid.values():
            severities = data["severities"]
            # Priority: critical > high > medium > low > info
            priority_order = ["critical", "high", "medium", "low", "info"]
            dominant = "info"
            for sev in priority_order:
                if sev in severities:
                    dominant = sev
                    break
            result.append(
                {
                    "lat": data["lat"],
                    "lng": data["lng"],
                    "count": data["count"],
                    "severity": dominant,
                    "country_code": data["country_code"],
                }
            )

        return result
