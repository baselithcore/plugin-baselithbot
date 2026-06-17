"""High-rate asynchronous telemetry fan-in.

The realtime hot-path is a pure-``asyncio`` pipeline (no Redis/RQ in the loop):
a :class:`TelemetrySource` produces raw payloads, the :class:`TelemetryBus`
validates each against :class:`~..models.TelemetryFrame` at the boundary and
hands only well-formed frames downstream. Malformed payloads are counted and
dropped — never fed half-parsed into the swarm. The :class:`TelemetrySource`
Protocol is the seam for every adapter (simulated / file replay / websocket /
UDP) without touching the bus.
"""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable, Protocol, runtime_checkable

from pydantic import ValidationError

from core.observability.logging import get_logger

from ..models import TelemetryFrame

logger = get_logger(__name__)

FrameHandler = Callable[[TelemetryFrame], Awaitable[None]]


@runtime_checkable
class TelemetrySource(Protocol):
    """A producer of raw telemetry payloads.

    Implementations push ``dict`` payloads onto the bus via ``emit``; the bus
    owns validation. This keeps external adapters dumb and the trust boundary in
    one place.
    """

    async def run(self, emit: Callable[[dict], Awaitable[None]]) -> None:
        """Produce payloads until cancelled, calling ``emit`` per sample."""
        ...


class TelemetryBus:
    """Validated, backpressured async fan-in for telemetry frames.

    Raw payloads are validated against :class:`TelemetryFrame`; only valid frames
    enter the bounded queue. A single consumer task drains the queue and invokes
    the registered handler, so ordering per producer is preserved.
    """

    def __init__(self, maxsize: int = 2048) -> None:
        self._queue: asyncio.Queue[TelemetryFrame] = asyncio.Queue(maxsize=maxsize)
        self._handler: FrameHandler | None = None
        self._consumer: asyncio.Task[None] | None = None
        self._producers: list[asyncio.Task[None]] = []
        self._frames_ingested = 0
        self._frames_rejected = 0
        self._running = False

    @property
    def running(self) -> bool:
        """True while the consumer task is active."""
        return self._running

    @property
    def frames_ingested(self) -> int:
        """Count of valid frames accepted onto the queue."""
        return self._frames_ingested

    @property
    def frames_rejected(self) -> int:
        """Count of payloads dropped for failing validation."""
        return self._frames_rejected

    def depth(self) -> int:
        """Current number of frames awaiting consumption."""
        return self._queue.qsize()

    async def emit(self, payload: dict) -> None:
        """Validate a raw payload and enqueue it; drop on validation failure."""
        try:
            frame = TelemetryFrame.model_validate(payload)
        except ValidationError as exc:
            self._frames_rejected += 1
            logger.debug("telemetry_rejected", errors=exc.error_count())
            return
        await self._queue.put(frame)
        self._frames_ingested += 1

    async def submit_frame(self, frame: TelemetryFrame) -> None:
        """Enqueue an already-validated frame (used by trusted callers/tests)."""
        await self._queue.put(frame)
        self._frames_ingested += 1

    def start(self, handler: FrameHandler, sources: list[TelemetrySource]) -> None:
        """Launch the consumer loop and any telemetry source producers."""
        if self._running:
            return
        self._handler = handler
        self._running = True
        self._consumer = asyncio.create_task(self._consume(), name="pitwall-consumer")
        for src in sources:
            self._producers.append(
                asyncio.create_task(src.run(self.emit), name="pitwall-source")
            )
        logger.info("telemetry_bus_started", sources=len(sources))

    async def _consume(self) -> None:
        """Drain the queue and dispatch each frame to the handler."""
        assert self._handler is not None
        while self._running:
            try:
                frame = await self._queue.get()
            except asyncio.CancelledError:
                break
            try:
                await self._handler(frame)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 — one bad frame can't kill the loop
                logger.error("frame_handler_error", error=str(exc))
            finally:
                self._queue.task_done()

    async def stop(self) -> None:
        """Cancel producers and the consumer, releasing the loop."""
        self._running = False
        for task in (*self._producers, self._consumer):
            if task is not None:
                task.cancel()
        for task in (*self._producers, self._consumer):
            if task is not None:
                try:
                    await task
                except (asyncio.CancelledError, Exception):  # noqa: BLE001
                    pass
        self._producers.clear()
        self._consumer = None
        logger.info("telemetry_bus_stopped")


__all__ = ["TelemetrySource", "TelemetryBus", "FrameHandler"]
