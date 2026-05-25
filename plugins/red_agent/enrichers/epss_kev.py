"""EPSS + CISA KEV finding enricher.

Pulls two authoritative threat-intel feeds and annotates each finding that
carries a CVE:

* **FIRST EPSS** (https://api.first.org/data/v1/epss) — predicted
  exploitation probability over the next 30 days. Score [0..1] +
  percentile rank. Authoritative for prioritization.
* **CISA KEV** (https://www.cisa.gov/known-exploited-vulnerabilities-catalog) —
  CVEs known to be actively exploited in the wild. KEV listing is a strong
  "patch immediately" signal regardless of CVSS.

Behavior:
* Findings with no ``cve`` are passed through unchanged.
* KEV-listed CVEs cause severity to be bumped to at least HIGH (configurable),
  reflecting real-world exploitation.
* EPSS score above ``high_epss_threshold`` (default 0.5) bumps severity by
  one step (configurable).

Fail-open: any HTTP error or JSON parse error returns the input list
untouched. KEV catalog is cached in-process for ``kev_cache_ttl_seconds``.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

import httpx

from core.observability.logging import get_logger
from plugins.red_agent.models import Finding, Severity

logger = get_logger(__name__)


_SEVERITY_ORDER: list[Severity] = [
    Severity.INFO,
    Severity.LOW,
    Severity.MEDIUM,
    Severity.HIGH,
    Severity.CRITICAL,
]


def _bump_severity(current: Severity, *, steps: int = 1) -> Severity:
    idx = _SEVERITY_ORDER.index(current)
    return _SEVERITY_ORDER[min(idx + steps, len(_SEVERITY_ORDER) - 1)]


class EpssKevEnricher:
    """Annotate CVE-bearing findings with EPSS scores + KEV listing.

    The enricher batches EPSS lookups (up to ``epss_batch_size`` CVEs per
    request) and shares a single KEV catalog snapshot across calls.
    """

    EPSS_ENDPOINT = "https://api.first.org/data/v1/epss"
    KEV_ENDPOINT = (
        "https://www.cisa.gov/sites/default/files/feeds/"
        "known_exploited_vulnerabilities.json"
    )

    def __init__(
        self,
        *,
        enabled: bool = True,
        bump_severity_on_kev: bool = True,
        bump_severity_on_high_epss: bool = True,
        high_epss_threshold: float = 0.5,
        epss_batch_size: int = 100,
        request_timeout_seconds: float = 10.0,
        kev_cache_ttl_seconds: float = 3600.0,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        self.enabled = enabled
        self.bump_severity_on_kev = bump_severity_on_kev
        self.bump_severity_on_high_epss = bump_severity_on_high_epss
        self.high_epss_threshold = high_epss_threshold
        self.epss_batch_size = epss_batch_size
        self.request_timeout_seconds = request_timeout_seconds
        self.kev_cache_ttl_seconds = kev_cache_ttl_seconds
        self._client = client
        self._owned_client: httpx.AsyncClient | None = None
        self._client_lock = asyncio.Lock()
        self._kev_cache: dict[str, dict[str, Any]] = {}
        self._kev_cache_loaded_at: float = 0.0
        self._kev_lock = asyncio.Lock()

    async def _get_client(self) -> httpx.AsyncClient:
        """Return a long-lived ``AsyncClient``.

        Reuses TLS sockets across enrich calls — a fresh client per call
        paid the handshake to ``api.first.org`` every time. The owned
        client is closed on :meth:`aclose`.
        """
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

    async def aclose(self) -> None:
        """Close the owned httpx client. Safe to call multiple times."""
        client = self._owned_client
        self._owned_client = None
        if client is not None:
            try:
                await client.aclose()
            except Exception:  # noqa: BLE001
                pass

    async def enrich(self, findings: list[Finding]) -> list[Finding]:
        if not self.enabled or not findings:
            return findings
        cves = sorted({f.cve for f in findings if f.cve})
        if not cves:
            return findings
        try:
            kev = await self._get_kev_catalog()
            epss = await self._get_epss_scores(cves)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "red_agent.enricher.epss_kev.failed", extra={"err": str(exc)}
            )
            return findings

        for f in findings:
            if not f.cve:
                continue
            kev_entry = kev.get(f.cve)
            epss_entry = epss.get(f.cve)

            if isinstance(f.evidence, dict):
                if epss_entry is not None:
                    f.evidence["epss_score"] = epss_entry.get("epss")
                    f.evidence["epss_percentile"] = epss_entry.get("percentile")
                if kev_entry is not None:
                    f.evidence["kev_listed"] = True
                    f.evidence["kev_due_date"] = kev_entry.get("dueDate")
                    f.evidence["kev_short_description"] = kev_entry.get(
                        "shortDescription"
                    )
                    f.evidence["kev_required_action"] = kev_entry.get("requiredAction")

            if kev_entry is not None and self.bump_severity_on_kev:
                if _SEVERITY_ORDER.index(f.severity) < _SEVERITY_ORDER.index(
                    Severity.HIGH
                ):
                    f.severity = Severity.HIGH
            elif (
                epss_entry is not None
                and self.bump_severity_on_high_epss
                and self._is_high_epss(epss_entry)
            ):
                f.severity = _bump_severity(f.severity, steps=1)

        return findings

    def _is_high_epss(self, epss_entry: dict[str, Any]) -> bool:
        try:
            return float(epss_entry.get("epss", 0.0)) >= self.high_epss_threshold
        except (TypeError, ValueError):
            return False

    async def _get_kev_catalog(self) -> dict[str, dict[str, Any]]:
        now = time.monotonic()
        if (
            self._kev_cache
            and (now - self._kev_cache_loaded_at) < self.kev_cache_ttl_seconds
        ):
            return self._kev_cache
        async with self._kev_lock:
            now = time.monotonic()
            if (
                self._kev_cache
                and (now - self._kev_cache_loaded_at) < self.kev_cache_ttl_seconds
            ):
                return self._kev_cache
            client = await self._get_client()
            resp = await client.get(self.KEV_ENDPOINT)
            resp.raise_for_status()
            doc = resp.json()
            entries = doc.get("vulnerabilities", []) if isinstance(doc, dict) else []
            self._kev_cache = {
                str(item.get("cveID")): item
                for item in entries
                if isinstance(item, dict) and item.get("cveID")
            }
            self._kev_cache_loaded_at = now
            return self._kev_cache

    async def _get_epss_scores(self, cves: list[str]) -> dict[str, dict[str, Any]]:
        out: dict[str, dict[str, Any]] = {}
        client = await self._get_client()
        for batch_start in range(0, len(cves), self.epss_batch_size):
            batch = cves[batch_start : batch_start + self.epss_batch_size]
            resp = await client.get(self.EPSS_ENDPOINT, params={"cve": ",".join(batch)})
            resp.raise_for_status()
            doc = resp.json()
            for item in doc.get("data", []) or []:
                if not isinstance(item, dict):
                    continue
                cve_id = item.get("cve")
                if cve_id:
                    out[str(cve_id)] = item
        return out
