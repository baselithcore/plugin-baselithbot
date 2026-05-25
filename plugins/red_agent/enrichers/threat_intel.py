"""Multi-source threat-intel enrichers.

Annotates findings with reputation / exposure data from four
sources operators ask for in the field. Each enricher is fail-open
and off-by-default; toggles + API keys live in
``_ThreatIntelConfig``.

| Enricher | Anchors on | Adds to ``evidence`` |
| --- | --- | --- |
| :class:`VirusTotalEnricher` | Public IP / domain (``Finding.target``) | ``vt_malicious``, ``vt_suspicious``, ``vt_total_engines``, ``vt_categories`` |
| :class:`ShodanEnricher` | Public IP | ``shodan_open_ports``, ``shodan_vulns``, ``shodan_tags``, ``shodan_org`` |
| :class:`CensysEnricher` | Public IP | ``censys_services``, ``censys_open_ports``, ``censys_autonomous_system`` |
| :class:`OTXEnricher` | Public IP / CVE | ``otx_pulse_count``, ``otx_pulses``, ``otx_adversaries`` |

Common shape: each enricher takes a list of findings, gathers the
unique anchors, performs concurrent lookups bounded by a semaphore,
and writes back into ``Finding.evidence`` only when the upstream
returned a useful payload. None of them mutate severity — that's
the risk scorer's job.
"""

from __future__ import annotations

import asyncio
import ipaddress
import re
from typing import Any

import httpx

from core.observability.logging import get_logger
from plugins.red_agent.models import Finding

logger = get_logger(__name__)


_VT_HOSTNAME_RE = re.compile(r"^[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
_CVE_RE = re.compile(r"^CVE-\d{4}-\d{4,7}$", re.IGNORECASE)


def _public_ip(value: str) -> str | None:
    """Return ``value`` as a routable public IP, or None."""

    value = (value or "").strip()
    try:
        ip = ipaddress.ip_address(value)
    except ValueError:
        return None
    if (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_multicast
        or ip.is_reserved
    ):
        return None
    return str(ip)


def _domain(value: str) -> str | None:
    """Return ``value`` as a bare domain, or None."""

    value = (value or "").strip().lower()
    if not value or _public_ip(value) is not None:
        return None
    if _VT_HOSTNAME_RE.match(value):
        return value
    return None


class _BaseTIClient:
    """Shared scaffolding for the four enrichers.

    Owns its own ``httpx.AsyncClient`` lifecycle and a per-anchor
    cache so a single scan never hits the upstream twice for the
    same IP / domain.
    """

    def __init__(
        self,
        *,
        enabled: bool,
        request_timeout_seconds: float,
        max_concurrent_requests: int,
        headers: dict[str, str] | None = None,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.enabled = enabled
        self._timeout = request_timeout_seconds
        self._headers = headers or {}
        self._client = client
        self._owned_client: httpx.AsyncClient | None = None
        self._client_lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(max(1, max_concurrent_requests))
        self._cache: dict[str, dict[str, Any] | None] = {}

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
                self._owned_client = httpx.AsyncClient(
                    timeout=self._timeout, headers=self._headers
                )
            return self._owned_client

    async def _fetch_json(self, url: str, *, key: str) -> dict[str, Any] | None:
        if key in self._cache:
            return self._cache[key]
        client = await self._get_client()
        async with self._semaphore:
            try:
                resp = await client.get(url)
            except httpx.HTTPError as exc:
                logger.debug(
                    "red_agent.threat_intel.lookup_failed",
                    extra={"key": key, "err": str(exc)},
                )
                self._cache[key] = None
                return None
        if resp.status_code == 404:
            self._cache[key] = {}
            return {}
        if resp.status_code != 200:
            self._cache[key] = None
            return None
        try:
            payload = resp.json()
        except ValueError:
            self._cache[key] = None
            return None
        self._cache[key] = payload if isinstance(payload, dict) else None
        return self._cache[key]


# --- VirusTotal -----------------------------------------------------------


class VirusTotalEnricher(_BaseTIClient):
    """Annotate findings with VirusTotal v3 reputation data.

    Anchors on the finding's ``target``. Both public IP and bare
    domain are recognised; URL targets are normalised to the host.
    """

    _IP_ENDPOINT = "https://www.virustotal.com/api/v3/ip_addresses/{anchor}"
    _DOMAIN_ENDPOINT = "https://www.virustotal.com/api/v3/domains/{anchor}"

    def __init__(
        self,
        *,
        enabled: bool = False,
        api_key: str | None = None,
        request_timeout_seconds: float = 15.0,
        max_concurrent_requests: int = 4,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(
            enabled=enabled and bool(api_key),
            request_timeout_seconds=request_timeout_seconds,
            max_concurrent_requests=max_concurrent_requests,
            headers={"x-apikey": api_key} if api_key else {},
            client=client,
        )

    async def enrich(self, findings: list[Finding]) -> list[Finding]:
        if not self.enabled or not findings:
            return findings
        anchors: dict[str, list[Finding]] = {}
        for f in findings:
            anchor = _public_ip(f.target) or _domain(f.target)
            if anchor:
                anchors.setdefault(anchor, []).append(f)
        if not anchors:
            return findings

        async def _lookup(anchor: str) -> None:
            url = (
                self._IP_ENDPOINT.format(anchor=anchor)
                if _public_ip(anchor)
                else self._DOMAIN_ENDPOINT.format(anchor=anchor)
            )
            await self._fetch_json(url, key=anchor)

        await asyncio.gather(*(_lookup(a) for a in anchors), return_exceptions=True)
        for anchor, group in anchors.items():
            data = self._cache.get(anchor)
            if not data:
                continue
            attrs = (data.get("data") or {}).get("attributes") or {}
            stats = attrs.get("last_analysis_stats") or {}
            categories = attrs.get("categories") or {}
            for f in group:
                if not isinstance(f.evidence, dict):
                    continue
                f.evidence["vt_malicious"] = stats.get("malicious", 0)
                f.evidence["vt_suspicious"] = stats.get("suspicious", 0)
                total = sum(v for v in stats.values() if isinstance(v, int))
                f.evidence["vt_total_engines"] = total
                if isinstance(categories, dict) and categories:
                    f.evidence["vt_categories"] = sorted(set(categories.values()))
        return findings


# --- Shodan ---------------------------------------------------------------


class ShodanEnricher(_BaseTIClient):
    """Annotate IP-typed findings with Shodan banner data."""

    _ENDPOINT = "https://api.shodan.io/shodan/host/{ip}?key={key}"

    def __init__(
        self,
        *,
        enabled: bool = False,
        api_key: str | None = None,
        request_timeout_seconds: float = 15.0,
        max_concurrent_requests: int = 4,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(
            enabled=enabled and bool(api_key),
            request_timeout_seconds=request_timeout_seconds,
            max_concurrent_requests=max_concurrent_requests,
            headers={},
            client=client,
        )
        self._api_key = api_key or ""

    async def enrich(self, findings: list[Finding]) -> list[Finding]:
        if not self.enabled or not findings:
            return findings
        anchors: dict[str, list[Finding]] = {}
        for f in findings:
            ip = _public_ip(f.target)
            if ip:
                anchors.setdefault(ip, []).append(f)
        if not anchors:
            return findings
        await asyncio.gather(
            *(
                self._fetch_json(
                    self._ENDPOINT.format(ip=ip, key=self._api_key), key=ip
                )
                for ip in anchors
            ),
            return_exceptions=True,
        )
        for ip, group in anchors.items():
            data = self._cache.get(ip)
            if not data:
                continue
            for f in group:
                if not isinstance(f.evidence, dict):
                    continue
                ports = data.get("ports")
                if isinstance(ports, list):
                    f.evidence["shodan_open_ports"] = sorted(
                        {p for p in ports if isinstance(p, int)}
                    )
                vulns = data.get("vulns")
                if isinstance(vulns, list):
                    f.evidence["shodan_vulns"] = sorted(
                        {str(v) for v in vulns if isinstance(v, str)}
                    )
                tags = data.get("tags")
                if isinstance(tags, list):
                    f.evidence["shodan_tags"] = sorted(
                        {str(t) for t in tags if isinstance(t, str)}
                    )
                if isinstance(data.get("org"), str):
                    f.evidence["shodan_org"] = data["org"]
        return findings


# --- Censys ---------------------------------------------------------------


class CensysEnricher(_BaseTIClient):
    """Annotate IP-typed findings with Censys host metadata."""

    _ENDPOINT = "https://search.censys.io/api/v2/hosts/{ip}"

    def __init__(
        self,
        *,
        enabled: bool = False,
        api_id: str | None = None,
        api_secret: str | None = None,
        request_timeout_seconds: float = 15.0,
        max_concurrent_requests: int = 4,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        import base64

        headers: dict[str, str] = {}
        configured = bool(api_id and api_secret)
        if configured:
            blob = f"{api_id}:{api_secret}".encode("utf-8")
            headers["Authorization"] = "Basic " + base64.b64encode(blob).decode("ascii")
        super().__init__(
            enabled=enabled and configured,
            request_timeout_seconds=request_timeout_seconds,
            max_concurrent_requests=max_concurrent_requests,
            headers=headers,
            client=client,
        )

    async def enrich(self, findings: list[Finding]) -> list[Finding]:
        if not self.enabled or not findings:
            return findings
        anchors: dict[str, list[Finding]] = {}
        for f in findings:
            ip = _public_ip(f.target)
            if ip:
                anchors.setdefault(ip, []).append(f)
        if not anchors:
            return findings
        await asyncio.gather(
            *(self._fetch_json(self._ENDPOINT.format(ip=ip), key=ip) for ip in anchors),
            return_exceptions=True,
        )
        for ip, group in anchors.items():
            data = self._cache.get(ip)
            if not data:
                continue
            host = (data.get("result") or data) if isinstance(data, dict) else {}
            services = host.get("services") if isinstance(host, dict) else None
            for f in group:
                if not isinstance(f.evidence, dict):
                    continue
                if isinstance(services, list):
                    f.evidence["censys_services"] = sorted(
                        {
                            str(s.get("service_name"))
                            for s in services
                            if isinstance(s, dict)
                            and isinstance(s.get("service_name"), str)
                        }
                    )
                    f.evidence["censys_open_ports"] = sorted(
                        {
                            port
                            for s in services
                            if isinstance(s, dict)
                            and isinstance(port := s.get("port"), int)
                        }
                    )
                asn = host.get("autonomous_system") if isinstance(host, dict) else None
                if isinstance(asn, dict):
                    f.evidence["censys_autonomous_system"] = {
                        "asn": asn.get("asn"),
                        "name": asn.get("name"),
                    }
        return findings


# --- OTX ------------------------------------------------------------------


class OTXEnricher(_BaseTIClient):
    """Annotate IP- or CVE-anchored findings with AlienVault OTX pulses.

    OTX pulse counts are a coarse but useful indicator that an IP /
    CVE has been observed in named adversary campaigns. Anchors:

    - ``Finding.target`` parsed as a public IP, or
    - ``Finding.cve`` matching the CVE-YYYY-NNNN pattern.
    """

    _IP_ENDPOINT = "https://otx.alienvault.com/api/v1/indicators/IPv4/{anchor}/general"
    _CVE_ENDPOINT = "https://otx.alienvault.com/api/v1/indicators/cve/{anchor}/general"

    def __init__(
        self,
        *,
        enabled: bool = False,
        api_key: str | None = None,
        request_timeout_seconds: float = 15.0,
        max_concurrent_requests: int = 4,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(
            enabled=enabled,
            request_timeout_seconds=request_timeout_seconds,
            max_concurrent_requests=max_concurrent_requests,
            headers={"X-OTX-API-KEY": api_key} if api_key else {},
            client=client,
        )

    async def enrich(self, findings: list[Finding]) -> list[Finding]:
        if not self.enabled or not findings:
            return findings
        ip_anchors: dict[str, list[Finding]] = {}
        cve_anchors: dict[str, list[Finding]] = {}
        for f in findings:
            ip = _public_ip(f.target)
            if ip:
                ip_anchors.setdefault(ip, []).append(f)
            cve = (f.cve or "").strip().upper()
            if cve and _CVE_RE.match(cve):
                cve_anchors.setdefault(cve, []).append(f)
        if not ip_anchors and not cve_anchors:
            return findings

        await asyncio.gather(
            *(
                self._fetch_json(self._IP_ENDPOINT.format(anchor=ip), key=f"ip:{ip}")
                for ip in ip_anchors
            ),
            *(
                self._fetch_json(
                    self._CVE_ENDPOINT.format(anchor=cve), key=f"cve:{cve}"
                )
                for cve in cve_anchors
            ),
            return_exceptions=True,
        )

        for ip, group in ip_anchors.items():
            self._apply_pulse_data(self._cache.get(f"ip:{ip}"), group)
        for cve, group in cve_anchors.items():
            self._apply_pulse_data(self._cache.get(f"cve:{cve}"), group)
        return findings

    def _apply_pulse_data(
        self, data: dict[str, Any] | None, group: list[Finding]
    ) -> None:
        if not data:
            return
        pulse_info = data.get("pulse_info") or {}
        if not isinstance(pulse_info, dict):
            return
        pulses = pulse_info.get("pulses") or []
        if not isinstance(pulses, list):
            return
        names: list[str] = []
        adversaries: set[str] = set()
        for p in pulses[:25]:
            if not isinstance(p, dict):
                continue
            if isinstance(p.get("name"), str):
                names.append(p["name"])
            if isinstance(p.get("adversary"), str) and p["adversary"]:
                adversaries.add(p["adversary"])
        for f in group:
            if not isinstance(f.evidence, dict):
                continue
            count = pulse_info.get("count")
            f.evidence["otx_pulse_count"] = (
                count if isinstance(count, int) else len(pulses)
            )
            if names:
                f.evidence["otx_pulses"] = names
            if adversaries:
                f.evidence["otx_adversaries"] = sorted(adversaries)
