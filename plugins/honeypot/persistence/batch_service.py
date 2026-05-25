"""
Batch insert service for honeypot events.

Provides efficient event persistence through micro-batching:
- Accumulates events up to batch size (10 events) or timeout (100ms)
- Uses executemany() for single DB roundtrip
- Graceful degradation to single inserts on failure
"""

import asyncio
from core.observability.logging import get_logger
from collections import deque
from typing import List, Optional

from ..models import AttackEvent
from .database import get_connection
from psycopg.types.json import Json

logger = get_logger(__name__)


class EventBatcher:
    """Batches events for efficient database insertion.

    Strategies:
    - Size-triggered: Flush when batch reaches max_size (default: 10)
    - Time-triggered: Flush after timeout (default: 100ms)
    - Shutdown: Flush pending events on graceful shutdown
    """

    def __init__(
        self,
        max_batch_size: int = 50,  # Increased from 10 for high-volume loads
        flush_interval_ms: int = 50,  # Reduced from 100ms for lower latency
    ):
        """Initialize event batcher.

        Args:
            max_batch_size: Maximum events before auto-flush
            flush_interval_ms: Max milliseconds before auto-flush
        """
        self.max_batch_size = max_batch_size
        self.flush_interval = flush_interval_ms / 1000.0  # Convert to seconds

        self._batch: deque = deque()
        self._lock = asyncio.Lock()
        self._flush_task: Optional[asyncio.Task] = None
        self._running = False

        # Metrics
        self._total_batches = 0
        self._total_events = 0
        self._total_flush_time = 0.0

    async def start(self) -> None:
        """Start the batcher background flush task."""
        if self._running:
            return

        self._running = True
        self._flush_task = asyncio.create_task(self._periodic_flush())
        logger.info(
            f"EventBatcher started (batch_size={self.max_batch_size}, "
            f"flush_interval={self.flush_interval * 1000}ms)"
        )

    async def stop(self) -> None:
        """Stop batcher and flush pending events."""
        if not self._running:
            return

        self._running = False

        if self._flush_task:
            self._flush_task.cancel()
            try:
                await self._flush_task
            except asyncio.CancelledError:
                pass

        # Final flush
        await self._flush_batch()
        logger.info(
            f"EventBatcher stopped. Stats: {self._total_events} events, "
            f"{self._total_batches} batches, "
            f"avg_batch_size={self._total_events / max(1, self._total_batches):.1f}"
        )

    async def add_event(self, event: AttackEvent) -> None:
        """Add event to batch.

        Args:
            event: Attack event to batch
        """
        async with self._lock:
            self._batch.append(event)

            # Size-triggered flush
            if len(self._batch) >= self.max_batch_size:
                asyncio.create_task(self._flush_batch())

    async def _periodic_flush(self) -> None:
        """Periodic flush task (time-triggered)."""
        while self._running:
            try:
                await asyncio.sleep(self.flush_interval)
                if len(self._batch) > 0:
                    await self._flush_batch()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic flush: {e}")

    async def _flush_batch(self) -> None:
        """Flush current batch to database."""
        async with self._lock:
            if not self._batch:
                return

            # Swap batch for processing
            events_to_flush = list(self._batch)
            self._batch.clear()

        # Process batch outside lock
        start_time = asyncio.get_event_loop().time()
        success_count = await self._save_batch(events_to_flush)
        flush_time = asyncio.get_event_loop().time() - start_time

        # Update metrics
        self._total_batches += 1
        self._total_events += success_count
        self._total_flush_time += flush_time

        if success_count < len(events_to_flush):
            logger.warning(
                f"Partial batch flush: {success_count}/{len(events_to_flush)} events saved"
            )

    async def _save_batch(self, events: List[AttackEvent]) -> int:
        """Save batch of events using executemany.

        Args:
            events: List of events to save

        Returns:
            Number of successfully saved events
        """
        if not events:
            return 0

        try:
            async with get_connection() as conn:
                async with conn.cursor() as cur:
                    # Prepare batch data
                    batch_data = []
                    for event in events:
                        batch_data.append(
                            {
                                "event_id": event.event_id,
                                "session_id": event.session_id,
                                "honeypot_id": event.honeypot_id,
                                "protocol": event.protocol.value,
                                "timestamp": event.timestamp,
                                "source_ip": event.source_ip,
                                "event_type": event.event_type,
                                "command": event.command,
                                "path": event.http_path,
                                "raw_data": event.raw_data[:2000]
                                if event.raw_data
                                else None,
                                "category": event.category.value,
                                "severity": event.severity.value,
                                "ai_classification": event.ai_classification,
                                "matched_cves": Json(event.matched_cves),
                                "is_bot": event.is_bot,
                                "meta": Json(
                                    {
                                        "geo": event.geo.model_dump()
                                        if event.geo
                                        else None,
                                        "username": event.username,
                                        "password": event.password,
                                        "http_method": event.http_method,
                                        "http_headers": event.http_headers,
                                        "detected_patterns": event.detected_patterns,
                                        "bot_confidence": event.bot_confidence,
                                        "bot_classification": event.bot_classification,
                                        "bot_signals": event.bot_signals,
                                    }
                                ),
                            }
                        )

                    # Execute batch insert
                    await cur.executemany(
                        """
                        INSERT INTO honeypot_events (
                            event_id, session_id, honeypot_id, protocol, 
                            timestamp, source_ip, event_type,
                            command, path, raw_data,
                            category, severity, ai_classification,
                            matched_cves, is_bot, meta
                        ) VALUES (
                            %(event_id)s, %(session_id)s, %(honeypot_id)s, %(protocol)s,
                            %(timestamp)s, %(source_ip)s, %(event_type)s,
                            %(command)s, %(path)s, %(raw_data)s,
                            %(category)s, %(severity)s, %(ai_classification)s,
                            %(matched_cves)s, %(is_bot)s, %(meta)s
                        )
                        ON CONFLICT (event_id) DO NOTHING
                        """,
                        batch_data,
                    )

                    logger.debug(f"Batch saved: {len(events)} events")
                    return len(events)

        except Exception as e:
            logger.error(
                f"Batch insert failed, falling back to individual inserts: {e}"
            )
            # Fallback: Try saving events individually
            return await self._save_individually(events)

    async def _save_individually(self, events: List[AttackEvent]) -> int:
        """Fallback: Save events one by one.

        Args:
            events: List of events to save

        Returns:
            Number of successfully saved events
        """
        from .events import save_event

        success_count = 0
        for event in events:
            try:
                await save_event(event)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to save event {event.event_id} individually: {e}")

        return success_count

    def get_stats(self) -> dict:
        """Get batcher statistics.

        Returns:
            Dictionary with metrics
        """
        return {
            "total_events": self._total_events,
            "total_batches": self._total_batches,
            "avg_batch_size": self._total_events / max(1, self._total_batches),
            "avg_flush_time_ms": (self._total_flush_time / max(1, self._total_batches))
            * 1000,
            "pending_events": len(self._batch),
        }


# Global batcher instance
_batcher: Optional[EventBatcher] = None


async def get_batcher() -> EventBatcher:
    """Get or create global batcher instance.

    Returns:
        EventBatcher instance
    """
    global _batcher
    if _batcher is None:
        _batcher = EventBatcher()
        await _batcher.start()
    return _batcher


async def save_event_batched(event: AttackEvent) -> None:
    """Add event to batch for efficient persistence.

    Args:
        event: Attack event to save
    """
    batcher = await get_batcher()
    await batcher.add_event(event)


async def shutdown_batcher() -> None:
    """Shutdown batcher and flush pending events."""
    global _batcher
    if _batcher:
        await _batcher.stop()
        _batcher = None
