"""OpenWA REST backend for the :class:`WhatsAppGateway`.

Targets a running ``@open-wa/wa-automate`` sidecar started in REST mode
(``--api``). Outbound sends map to the EASY API ``/sendText`` /
``/sendImage`` endpoints; inbound delivery is push-based via the OpenWA webhook
(handled by :mod:`router_realtime`), so this backend is send-and-health only.

``httpx`` is imported lazily and the backend degrades to a non-fatal receipt if
the client library is unavailable, keeping the plugin importable with no extra
deps installed.
"""

from __future__ import annotations

from typing import Any

from core.observability.logging import get_logger

from .models import MediaKind, OutboundMessage, SendReceipt

logger = get_logger(__name__)


class OpenWAGateway:
    """A thin async REST client for the OpenWA EASY API."""

    def __init__(
        self,
        base_url: str,
        session: str,
        api_key: str = "",
        timeout: float = 15.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._session = session
        self._api_key = api_key
        self._timeout = timeout
        self._connected = False

    def _headers(self) -> dict[str, str]:
        """Build request headers, including the bearer key when configured."""
        headers = {"Content-Type": "application/json"}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"
        return headers

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        """POST JSON to the sidecar, returning the decoded body."""
        import httpx  # lazy: optional dependency

        url = f"{self._base_url}/{path.lstrip('/')}"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json=payload, headers=self._headers())
            response.raise_for_status()
            return response.json() if response.content else {}

    async def connect(self) -> None:
        """Probe the sidecar's health endpoint to confirm the session is live."""
        try:
            await self._post("getConnectionState", {"args": {}})
            self._connected = True
        except Exception as exc:  # noqa: BLE001 — degrade, never crash boot
            logger.warning("openwa_connect_failed", error=str(exc))
            self._connected = False

    async def disconnect(self) -> None:
        """Mark the local session state as down (OpenWA owns its own lifecycle)."""
        self._connected = False

    async def is_connected(self) -> bool:
        """Return the last-known connection state without a network round-trip."""
        return self._connected

    async def send(self, message: OutboundMessage) -> SendReceipt:
        """Send a text or media message via the EASY API."""
        try:
            if message.media and message.media.kind is not MediaKind.TEXT:
                body = {
                    "args": {
                        "to": message.contact_id,
                        "url": message.media.url,
                        "caption": message.media.caption or message.text,
                    }
                }
                data = await self._post("sendImage", body)
            else:
                body = {"args": {"to": message.contact_id, "content": message.text}}
                data = await self._post("sendText", body)
            self._connected = True
            return SendReceipt(
                ok=True, message_id=str(data.get("response", "")) or None
            )
        except Exception as exc:  # noqa: BLE001 — surface as a failed receipt
            logger.warning("openwa_send_failed", error=str(exc))
            return SendReceipt(ok=False, error=str(exc))


__all__ = ["OpenWAGateway"]
