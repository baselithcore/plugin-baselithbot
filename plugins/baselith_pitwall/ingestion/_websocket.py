"""WebSocket telemetry source — live push feed from a telemetry broker.

Connects to an upstream ``ws(s)://`` endpoint and emits each received JSON
message as a raw payload. The ``websockets`` library is imported lazily inside
:meth:`run` so the dependency is optional: the plugin boots and the simulated /
file / UDP sources work even when ``websockets`` is not installed — only this
adapter requires it. Reconnects with capped backoff on transient drops.
"""

from __future__ import annotations

import asyncio
import json
from typing import Awaitable, Callable

from core.observability.logging import get_logger

logger = get_logger(__name__)

_MAX_BACKOFF_S = 30.0


class WebSocketSource:
    """Stream telemetry payloads from a websocket broker with auto-reconnect."""

    def __init__(
        self,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        max_reconnects: int | None = None,
    ) -> None:
        self.url = url
        self.headers = headers or {}
        self.max_reconnects = max_reconnects

    async def run(self, emit: Callable[[dict], Awaitable[None]]) -> None:
        """Connect, stream, and reconnect with backoff until cancelled."""
        try:
            import websockets  # type: ignore[import-not-found]
        except ImportError:
            logger.error(
                "pitwall_ws_unavailable",
                hint="install the 'websockets' package to use the websocket source",
            )
            return

        attempts = 0
        backoff = 1.0
        while True:
            try:
                async with websockets.connect(
                    self.url, additional_headers=self.headers
                ) as ws:
                    logger.info("pitwall_ws_connected", url=self.url)
                    backoff = 1.0
                    async for message in ws:
                        await self._on_message(message, emit)
            except asyncio.CancelledError:
                raise
            except Exception as exc:  # noqa: BLE001 — reconnect on any transport error
                attempts += 1
                if self.max_reconnects is not None and attempts > self.max_reconnects:
                    logger.error("pitwall_ws_giving_up", url=self.url, error=str(exc))
                    return
                logger.warning(
                    "pitwall_ws_reconnect",
                    url=self.url,
                    error=str(exc),
                    backoff=backoff,
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, _MAX_BACKOFF_S)

    @staticmethod
    async def _on_message(
        message: str | bytes, emit: Callable[[dict], Awaitable[None]]
    ) -> None:
        """Decode one websocket frame and emit it; drop undecodable payloads."""
        try:
            raw = message.decode() if isinstance(message, bytes) else message
            payload = json.loads(raw)
        except (json.JSONDecodeError, UnicodeDecodeError):
            logger.debug("pitwall_ws_bad_payload")
            return
        if isinstance(payload, dict):
            await emit(payload)


__all__ = ["WebSocketSource"]
