"""UDP telemetry source — raw datagram feed (sim-rig / game-style telemetry).

Binds an ``asyncio`` datagram endpoint (stdlib only, no external dependency) and
emits each datagram as a JSON payload. Designed for high-rate local feeds such as
a dyno bench or an F1-game UDP broadcast bridged to JSON. Datagrams that aren't
valid JSON objects are dropped; the bus validates the rest. Binds to loopback by
default — broadening the bind address is an explicit, deliberate choice.
"""

from __future__ import annotations

import asyncio
import json
from typing import Awaitable, Callable

from core.observability.logging import get_logger

logger = get_logger(__name__)


class _Protocol(asyncio.DatagramProtocol):
    """Forwards each datagram to an async queue for the run-loop to drain."""

    def __init__(self, queue: asyncio.Queue[bytes]) -> None:
        self._queue = queue

    def datagram_received(self, data: bytes, addr: object) -> None:
        try:
            self._queue.put_nowait(data)
        except asyncio.QueueFull:  # pragma: no cover — drop under flood
            logger.debug("pitwall_udp_overflow")


class UdpSource:
    """Receive telemetry payloads over UDP and emit them as raw dicts."""

    def __init__(
        self, host: str = "127.0.0.1", port: int = 20777, queue_maxsize: int = 4096
    ) -> None:
        self.host = host
        self.port = port
        self.queue_maxsize = queue_maxsize

    async def run(self, emit: Callable[[dict], Awaitable[None]]) -> None:
        """Bind the socket and forward decoded datagrams until cancelled."""
        loop = asyncio.get_running_loop()
        queue: asyncio.Queue[bytes] = asyncio.Queue(maxsize=self.queue_maxsize)
        transport, _ = await loop.create_datagram_endpoint(
            lambda: _Protocol(queue), local_addr=(self.host, self.port)
        )
        logger.info("pitwall_udp_bound", host=self.host, port=self.port)
        try:
            while True:
                data = await queue.get()
                await self._forward(data, emit)
        except asyncio.CancelledError:
            raise
        finally:
            transport.close()
            logger.info("pitwall_udp_closed", host=self.host, port=self.port)

    @staticmethod
    async def _forward(data: bytes, emit: Callable[[dict], Awaitable[None]]) -> None:
        """Decode one datagram and emit it; drop undecodable payloads."""
        try:
            payload = json.loads(data.decode())
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.debug("pitwall_udp_bad_payload")
            return
        if isinstance(payload, dict):
            await emit(payload)


__all__ = ["UdpSource"]
