"""Outbound webhook notifier for SOAR / ticketing integration.

Fires an HTTP POST per qualifying finding to an operator-supplied
endpoint. Payload is the OCSF Vulnerability Finding event so the
receiver can ingest the same shape used by the
``/reports/{scan_id}/ocsf`` exporter — no per-vendor adapter required.

Security:

* Each request is signed with HMAC-SHA256 over the raw body using
  ``webhook_secret``. The signature is sent in two headers:
  ``X-RedAgent-Signature: sha256=<hex>`` (canonical) and
  ``X-Hub-Signature-256: sha256=<hex>`` (GitHub-compatible alias).
* TLS only; HTTP URLs are accepted in dev but logged as a warning
  so operators see them.

Throughput:

* Findings are filtered by configurable severity floor before any
  HTTP work happens.
* Calls fan out concurrently per scan iteration, bounded by an
  ``asyncio.Semaphore``.
* A single retry on transient (5xx / network) failure; no infinite
  retry loop.

Fail-open: any error is logged + swallowed so a flaky receiver never
blocks the scan flow.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import time
import uuid
from typing import Any
from uuid import UUID

import httpx

from core.observability.logging import get_logger
from plugins.red_agent.exporters import to_ocsf_event
from plugins.red_agent.models import Finding, Severity

logger = get_logger(__name__)


_SEVERITY_ORDER: dict[Severity, int] = {
    Severity.INFO: 0,
    Severity.LOW: 1,
    Severity.MEDIUM: 2,
    Severity.HIGH: 3,
    Severity.CRITICAL: 4,
}


class WebhookNotifier:
    """Send HMAC-signed OCSF events to a SOAR / ticketing webhook URL."""

    def __init__(
        self,
        *,
        enabled: bool = False,
        url: str | None = None,
        secret: str | None = None,
        min_severity: Severity = Severity.HIGH,
        request_timeout_seconds: float = 10.0,
        max_concurrent_requests: int = 4,
        retry_count: int = 1,
        replay_protection: bool = False,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.enabled = enabled and bool(url)
        self.url = url
        self.secret = secret
        self.min_severity = min_severity
        self.request_timeout_seconds = request_timeout_seconds
        self.retry_count = max(0, retry_count)
        self.replay_protection = replay_protection
        self._semaphore = asyncio.Semaphore(max(1, max_concurrent_requests))
        self._client = client
        self._owned_client: httpx.AsyncClient | None = None
        self._client_lock = asyncio.Lock()
        if url and not url.lower().startswith("https://"):
            logger.warning(
                "red_agent.webhook.insecure_url",
                extra={
                    "url": url,
                    "reason": "non-HTTPS endpoint — consider TLS for production",
                },
            )

    async def notify(
        self,
        findings: list[Finding],
        *,
        scan_id: UUID | None = None,
        tenant_id: str | None = None,
    ) -> int:
        """Notify every qualifying finding. Returns count of successful deliveries."""
        if not self.enabled or not findings or self.url is None:
            return 0
        floor = _SEVERITY_ORDER[self.min_severity]
        eligible = [f for f in findings if _SEVERITY_ORDER[f.severity] >= floor]
        if not eligible:
            return 0
        client = await self._get_client()
        results = await asyncio.gather(
            *(
                self._send_one(client, f, scan_id=scan_id, tenant_id=tenant_id)
                for f in eligible
            ),
            return_exceptions=True,
        )
        return sum(1 for r in results if r is True)

    async def aclose(self) -> None:
        client = self._owned_client
        self._owned_client = None
        if client is not None:
            try:
                await client.aclose()
            except Exception:  # noqa: BLE001
                pass

    # --- internals ----------------------------------------------------

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        if self._owned_client is not None:
            return self._owned_client
        async with self._client_lock:
            if self._owned_client is None:
                self._owned_client = httpx.AsyncClient(
                    timeout=self.request_timeout_seconds
                )
            return self._owned_client

    async def _send_one(
        self,
        client: httpx.AsyncClient,
        f: Finding,
        *,
        scan_id: UUID | None,
        tenant_id: str | None,
    ) -> bool:
        if self.url is None:
            return False
        event = to_ocsf_event(
            f,
            scan_id=str(scan_id) if scan_id else None,
            tenant_id=tenant_id,
        )
        body = json.dumps(event, default=str).encode()
        headers = self._headers(body)
        async with self._semaphore:
            ok = await self._post_with_retry(client, body, headers, finding_id=f.id)
        return ok

    def _headers(self, body: bytes) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "X-RedAgent-Event": "vulnerability_finding.create",
            "User-Agent": "baselith-red-agent/0.1",
        }
        if not self.secret:
            return headers
        if self.replay_protection:
            ts = str(int(time.time()))
            nonce = uuid.uuid4().hex
            payload = f"{ts}.".encode() + body
            sig = hmac.new(self.secret.encode(), payload, hashlib.sha256).hexdigest()
            headers["X-RedAgent-Timestamp"] = ts
            headers["X-RedAgent-Nonce"] = nonce
            headers["X-RedAgent-Signature"] = f"sha256={sig}"
            # Hub-style alias intentionally omitted: GitHub does not bind
            # timestamp into the signature, so reusing the header would
            # mislead consumers about the verification semantics.
        else:
            sig = hmac.new(self.secret.encode(), body, hashlib.sha256).hexdigest()
            headers["X-RedAgent-Signature"] = f"sha256={sig}"
            headers["X-Hub-Signature-256"] = f"sha256={sig}"
        return headers

    async def _post_with_retry(
        self,
        client: httpx.AsyncClient,
        body: bytes,
        headers: dict[str, str],
        *,
        finding_id: Any,
    ) -> bool:
        attempt = 0
        last_err: str | None = None
        while attempt <= self.retry_count:
            try:
                resp = await client.post(self.url or "", content=body, headers=headers)
                if 200 <= resp.status_code < 300:
                    return True
                # Only retry server-side / rate-limit errors.
                if resp.status_code in (429,) or 500 <= resp.status_code < 600:
                    last_err = f"status={resp.status_code}"
                else:
                    logger.warning(
                        "red_agent.webhook.rejected",
                        extra={
                            "finding_id": str(finding_id),
                            "status": resp.status_code,
                        },
                    )
                    return False
            except Exception as exc:  # noqa: BLE001
                last_err = str(exc)
            attempt += 1
        logger.warning(
            "red_agent.webhook.delivery_failed",
            extra={"finding_id": str(finding_id), "err": last_err or "unknown"},
        )
        return False
