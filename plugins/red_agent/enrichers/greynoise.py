"""GreyNoise IP-reputation enricher.

GreyNoise classifies internet-wide background scan traffic. For findings
whose target is an IP address, the community API (free, rate-limited)
returns:

* ``noise``: bool — IP seen scanning the internet en masse (prebuilt
  scanners, opportunistic recon)
* ``riot``: bool — IP belongs to a known benign service (CDN, search
  engine, business utility)
* ``classification``: ``"benign" | "malicious" | "unknown"``
* ``name``: provider / actor label
* ``last_seen``: ISO date

Annotates ``Finding.evidence``:

* ``greynoise_classification`` — pass-through of the classification field
* ``greynoise_noise`` / ``greynoise_riot`` — booleans
* ``greynoise_name`` / ``greynoise_link`` / ``greynoise_last_seen``

The enricher only runs against findings whose ``target`` is a routable
IPv4/IPv6 address, so DAST findings against URLs / hostnames are skipped
unconditionally (cheap pre-filter).
"""

from __future__ import annotations

import asyncio
import ipaddress
from typing import Any

import httpx

from core.observability.logging import get_logger
from plugins.red_agent.models import Finding

logger = get_logger(__name__)

_ENDPOINT = "https://api.greynoise.io/v3/community/{ip}"


class GreyNoiseEnricher:
    """Annotate findings keyed on an IP target with GreyNoise reputation data."""

    def __init__(
        self,
        *,
        enabled: bool = True,
        api_key: str | None = None,
        request_timeout_seconds: float = 10.0,
        max_concurrent_requests: int = 4,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.enabled = enabled
        self.api_key = api_key
        self.request_timeout_seconds = request_timeout_seconds
        self._client = client
        self._owned_client: httpx.AsyncClient | None = None
        self._client_lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max(1, max_concurrent_requests))
        self._cache: dict[str, dict[str, Any] | None] = {}

    async def enrich(self, findings: list[Finding]) -> list[Finding]:
        if not self.enabled or not findings:
            return findings
        unique_ips: dict[str, list[Finding]] = {}
        for f in findings:
            ip = _extract_ip(f)
            if ip is None:
                continue
            unique_ips.setdefault(ip, []).append(f)
        if not unique_ips:
            return findings
        client = await self._get_client()
        await asyncio.gather(
            *(self._fetch(client, ip) for ip in unique_ips),
            return_exceptions=True,
        )
        for ip, group in unique_ips.items():
            data = self._cache.get(ip)
            if not data:
                continue
            for f in group:
                _annotate(f, data)
        return findings

    async def aclose(self) -> None:
        client = self._owned_client
        self._owned_client = None
        if client is not None:
            try:
                await client.aclose()
            except Exception:  # noqa: BLE001
                pass

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is not None:
            return self._client
        if self._owned_client is not None:
            return self._owned_client
        async with self._client_lock:
            if self._owned_client is None:
                headers = {"key": self.api_key} if self.api_key else {}
                self._owned_client = httpx.AsyncClient(
                    timeout=self.request_timeout_seconds, headers=headers
                )
            return self._owned_client

    async def _fetch(self, client: httpx.AsyncClient, ip: str) -> None:
        if ip in self._cache:
            return
        async with self._semaphore:
            try:
                resp = await client.get(_ENDPOINT.format(ip=ip))
            except Exception as exc:  # noqa: BLE001
                logger.debug(
                    "red_agent.greynoise.lookup_failed",
                    extra={"ip": ip, "err": str(exc)},
                )
                self._cache[ip] = None
                return
        if resp.status_code == 404:
            self._cache[ip] = {
                "classification": "unknown",
                "noise": False,
                "riot": False,
            }
            return
        if resp.status_code != 200:
            self._cache[ip] = None
            return
        try:
            self._cache[ip] = resp.json()
        except ValueError:
            self._cache[ip] = None


def _extract_ip(f: Finding) -> str | None:
    """Return ``f.target`` as a routable IP address, or None."""
    target = f.target.strip() if isinstance(f.target, str) else ""
    if not target:
        return None
    try:
        ip_obj = ipaddress.ip_address(target)
    except ValueError:
        return None
    # Skip private / loopback / multicast — GreyNoise covers public space only.
    if (
        ip_obj.is_private
        or ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_multicast
    ):
        return None
    return str(ip_obj)


def _annotate(f: Finding, data: dict[str, Any]) -> None:
    if not isinstance(f.evidence, dict):
        return
    classification = data.get("classification")
    if isinstance(classification, str):
        f.evidence["greynoise_classification"] = classification
    if isinstance(data.get("noise"), bool):
        f.evidence["greynoise_noise"] = bool(data.get("noise"))
    if isinstance(data.get("riot"), bool):
        f.evidence["greynoise_riot"] = bool(data.get("riot"))
    name = data.get("name")
    if isinstance(name, str):
        f.evidence["greynoise_name"] = name
    link = data.get("link")
    if isinstance(link, str):
        f.evidence["greynoise_link"] = link
    last_seen = data.get("last_seen")
    if isinstance(last_seen, str):
        f.evidence["greynoise_last_seen"] = last_seen
