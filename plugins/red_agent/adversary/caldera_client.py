"""Minimal MITRE Caldera REST client.

Used when the customer prefers a server-driven C2 plan over Atomic
dispatches. The client speaks the public Caldera v2 REST API:
authentication via an API key in the ``KEY`` header, JSON bodies, no
session affinity. Only the endpoints the orchestrator needs are
modelled — full Caldera surface coverage belongs in the Caldera
project, not here.

Operations modelled:

- ``submit_operation`` — POST ``/api/v2/operations``.
- ``get_operation`` — GET ``/api/v2/operations/{id}``.
- ``list_links`` — GET ``/api/v2/operations/{id}/links`` (per-step
  results).

Failures are surfaced as :class:`CalderaClientError` with the
upstream status + body trimmed to 1 KiB so we don't dump huge HTML
errors into the audit log.
"""

from __future__ import annotations

from typing import Any

import httpx

from core.observability.logging import get_logger

logger = get_logger(__name__)


class CalderaClientError(RuntimeError):
    """Raised on any non-2xx response or transport failure."""


class CalderaClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        timeout_seconds: float = 30.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {"KEY": self._api_key, "Content-Type": "application/json"}

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json_body: dict[str, Any] | None = None,
    ) -> Any:
        url = f"{self._base_url}{path}"
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.request(
                    method, url, headers=self._headers(), json=json_body
                )
        except httpx.HTTPError as exc:
            raise CalderaClientError(f"transport failure: {exc}") from exc
        if resp.status_code >= 400:
            body = (resp.text or "")[:1024]
            raise CalderaClientError(
                f"caldera {method} {path} -> {resp.status_code}: {body}"
            )
        if not resp.content:
            return None
        try:
            return resp.json()
        except ValueError as exc:
            raise CalderaClientError(
                f"caldera {method} {path}: invalid JSON: {exc}"
            ) from exc

    async def submit_operation(
        self,
        *,
        name: str,
        adversary_id: str,
        group: str,
        planner: str = "atomic",
        auto_close: bool = True,
    ) -> dict[str, Any]:
        """Create a new operation and return Caldera's record."""

        payload = {
            "name": name,
            "adversary": {"adversary_id": adversary_id},
            "group": group,
            "planner": {"id": planner},
            "auto_close": auto_close,
        }
        result = await self._request("POST", "/api/v2/operations", json_body=payload)
        if not isinstance(result, dict):
            raise CalderaClientError("submit_operation: expected object response")
        return result

    async def get_operation(self, operation_id: str) -> dict[str, Any]:
        result = await self._request("GET", f"/api/v2/operations/{operation_id}")
        if not isinstance(result, dict):
            raise CalderaClientError("get_operation: expected object response")
        return result

    async def list_links(self, operation_id: str) -> list[dict[str, Any]]:
        """Return per-step ``link`` records for an operation."""

        result = await self._request("GET", f"/api/v2/operations/{operation_id}/links")
        if isinstance(result, list):
            return [r for r in result if isinstance(r, dict)]
        return []
