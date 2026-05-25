"""CVE Scanner Agent.

Agent responsible for scanning CVE data sources (NVD, GitHub, etc.)
and extracting vulnerability information.
"""

import asyncio
import os
import random
from core.observability.logging import get_logger
from datetime import datetime, timedelta, timezone
from typing import Any, AsyncIterator, Dict, List, Optional
from uuid import uuid4
import httpx

# Support both relative imports (when installed) and absolute imports (when using sys.path)
try:
    from ..config import CVEHunterConfig, get_cve_hunter_config, get_nvd_api_key
    from ..models import (
        CVERecord,
        CVESource,
        ScanResult,
    )
    from .scanner_parsers import (
        parse_cisa_kev,
        parse_github_advisory,
        parse_nvd_cve,
    )
except ImportError:
    from config import CVEHunterConfig, get_cve_hunter_config, get_nvd_api_key  # type: ignore[no-redef]
    from models import (  # type: ignore[no-redef]
        CVERecord,
        CVESource,
        ScanResult,
    )
    from agents.scanner_parsers import (  # type: ignore[no-redef]
        parse_cisa_kev,
        parse_github_advisory,
        parse_nvd_cve,
    )

logger = get_logger(__name__)


# Transient HTTP failures we should retry rather than abort the whole scan.
_RETRYABLE_HTTP_EXC = (httpx.RequestError, httpx.ReadTimeout, httpx.ConnectError)


async def _fetch_with_retry(
    client: httpx.AsyncClient,
    url: str,
    *,
    params: Optional[Dict[str, Any]] = None,
    headers: Optional[Dict[str, str]] = None,
    max_attempts: int = 3,
    base_delay: float = 2.0,
    source_label: str = "external",
) -> Optional[httpx.Response]:
    """Issue a GET with exponential backoff on transient errors.

    Async generators cannot be safely wrapped by the global ``@retry``
    decorator (the decorator returns the generator factory, not the
    iterator), so we apply retry semantics around the individual HTTP
    call instead.

    Returns ``None`` after the final failed attempt; callers decide
    whether to abort iteration or continue.
    """
    last_exc: Optional[BaseException] = None
    for attempt in range(1, max_attempts + 1):
        try:
            return await client.get(url, params=params, headers=headers)
        except _RETRYABLE_HTTP_EXC as exc:
            last_exc = exc
            if attempt == max_attempts:
                logger.error(
                    "HTTP fetch failed after retries",
                    extra={
                        "source": source_label,
                        "url": url,
                        "attempts": attempt,
                        "error": str(exc),
                    },
                )
                return None
            delay = base_delay * (2 ** (attempt - 1)) * (0.5 + random.random())  # nosec B311
            logger.warning(
                "HTTP fetch attempt failed; retrying",
                extra={
                    "source": source_label,
                    "url": url,
                    "attempt": attempt,
                    "max_attempts": max_attempts,
                    "delay_s": round(delay, 2),
                    "error": str(exc),
                },
            )
            await asyncio.sleep(delay)
    if last_exc is not None:
        logger.debug(
            "retry loop exited with captured exception", extra={"error": str(last_exc)}
        )
    return None


class CVEScannerAgent:
    """Agent for scanning CVE data sources.

    Crawls NVD, GitHub Security Advisories, and other sources
    to collect vulnerability data.

    Example:
        ```python
        agent = CVEScannerAgent()
        async for cve in agent.scan_nvd(days_back=7):
            print(f"Found: {cve.cve_id}")
        ```
    """

    name = "cve-scanner"

    def __init__(
        self,
        config: Optional[CVEHunterConfig] = None,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        """Initialize scanner agent.

        Args:
            config: CVE Hunter configuration
            http_client: Optional HTTP client for dependency injection
        """
        self.config = config or get_cve_hunter_config()
        self._http_client = http_client
        self._owns_client = http_client is None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "User-Agent": "CVE-Hunter/1.0",
                    "Accept": "application/json",
                },
            )
        return self._http_client

    async def close(self) -> None:
        """Close HTTP client if owned."""
        if self._owns_client and self._http_client:
            await self._http_client.aclose()
            self._http_client = None

    async def scan_nvd(
        self,
        days_back: int = 7,
        results_per_page: int = 100,
    ) -> AsyncIterator[CVERecord]:
        """Scan NVD for recent CVEs.

        Args:
            days_back: Number of days to look back
            results_per_page: Results per API page

        Yields:
            CVERecord for each vulnerability found
        """
        if os.getenv("HF_HUB_OFFLINE") == "1":
            logger.info("Scanning NVD skipped (offline mode)")
            return

        client = await self._get_client()
        start_date = datetime.now(timezone.utc) - timedelta(days=days_back)
        params: Dict[str, Any] = {
            "lastModStartDate": start_date.strftime("%Y-%m-%dT%H:%M:%S.000"),
            "lastModEndDate": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.000"
            ),
            "resultsPerPage": results_per_page,
            "startIndex": 0,
        }

        api_key = get_nvd_api_key(self.config)
        headers: Dict[str, str] = {}
        if api_key:
            headers["apiKey"] = api_key

        # NVD limits: 50 req/30s with key (~0.6s), 5 req/30s without key (~6s)
        # Add a small buffer to stay safely below quota.
        delay = 1.0 if api_key else 6.5

        while True:
            response = await _fetch_with_retry(
                client,
                self.config.nvd_base_url,
                params=params,
                headers=headers,
                source_label="nvd",
            )
            if response is None:
                return

            if response.status_code == 429:
                retry_after = int(response.headers.get("Retry-After", 30))
                logger.warning(
                    "NVD rate limit hit; cooling down",
                    extra={"retry_after_s": retry_after},
                )
                await asyncio.sleep(retry_after)
                continue

            if response.status_code != 200:
                logger.error(
                    "NVD API error",
                    extra={"status_code": response.status_code},
                )
                return

            try:
                data = response.json()
            except ValueError as e:
                logger.error("NVD returned non-JSON payload", extra={"error": str(e)})
                return

            vulnerabilities = data.get("vulnerabilities", [])
            if not vulnerabilities:
                return

            for vuln in vulnerabilities:
                cve_data = vuln.get("cve", {})
                yield parse_nvd_cve(cve_data, self.config)

            total_results = data.get("totalResults", 0)
            params["startIndex"] += results_per_page
            if params["startIndex"] >= total_results:
                return

            await asyncio.sleep(delay)

    async def scan_github(
        self,
        severity: Optional[str] = None,
        per_page: int = 100,
    ) -> AsyncIterator[CVERecord]:
        """Scan GitHub Security Advisories.

        Args:
            severity: Filter by severity (critical, high, medium, low)
            per_page: Results per page

        Yields:
            CVERecord for each advisory found
        """
        if os.getenv("HF_HUB_OFFLINE") == "1":
            logger.info("Scanning GitHub skipped (offline mode)")
            return

        client = await self._get_client()
        params: Dict[str, Any] = {"per_page": per_page}
        if severity:
            params["severity"] = severity

        response = await _fetch_with_retry(
            client,
            self.config.github_advisories_url,
            params=params,
            source_label="github",
        )
        if response is None:
            return

        if response.status_code != 200:
            logger.error(
                "GitHub API error",
                extra={"status_code": response.status_code},
            )
            return

        try:
            advisories = response.json()
        except ValueError as e:
            logger.error("GitHub returned non-JSON payload", extra={"error": str(e)})
            return

        for advisory in advisories or []:
            cve = parse_github_advisory(advisory)
            if cve:
                yield cve

    async def scan_cisa_kev(self) -> AsyncIterator[CVERecord]:
        """Scan CISA KEV Known Exploited Vulnerabilities catalog.

        Yields:
            CVERecord for each actively exploited vulnerability
        """
        if os.getenv("HF_HUB_OFFLINE") == "1":
            logger.info("Scanning CISA KEV skipped (offline mode)")
            return

        client = await self._get_client()
        response = await _fetch_with_retry(
            client,
            self.config.cisa_kev_url,
            source_label="cisa_kev",
        )
        if response is None:
            return

        if response.status_code != 200:
            logger.error(
                "CISA KEV API error",
                extra={"status_code": response.status_code},
            )
            return

        try:
            data = response.json()
        except ValueError as e:
            logger.error("CISA KEV returned non-JSON payload", extra={"error": str(e)})
            return

        for vuln in data.get("vulnerabilities", []) or []:
            yield parse_cisa_kev(vuln)

    async def scan_osv(self, ecosystem: str = "PyPI") -> AsyncIterator[CVERecord]:
        """Scan OSV (Open Source Vulnerabilities) database.

        Args:
            ecosystem: Ecosystem to query (PyPI, npm, Go, etc.)

        Yields:
            CVERecord for each vulnerability found
        """
        # The OSV /query endpoint requires a package name; bulk export
        # over the entire ecosystem is not exposed through it. Until
        # the bulk-zip ingestion is implemented this method short-circuits.
        logger.warning(
            "Skipping OSV ecosystem scan (unsupported by /query endpoint)",
            extra={"ecosystem": ecosystem},
        )
        if False:  # pragma: no cover
            yield  # type: ignore[misc]
        return

    async def scan_source(self, source: str, days_back: int = 7) -> List[CVERecord]:
        """Scan a single source by name and return collected CVEs.

        Convenience wrapper used by `_targeted_cwe_scan` in the swarm
        coordinator. Returns an in-memory list rather than streaming.
        """
        cves: List[CVERecord] = []
        if source == "nvd":
            async for cve in self.scan_nvd(days_back=days_back):
                cves.append(cve)
        elif source == "github":
            async for cve in self.scan_github():
                cves.append(cve)
        elif source == "cisa_kev":
            async for cve in self.scan_cisa_kev():
                cves.append(cve)
        elif source == "osv":
            async for cve in self.scan_osv():
                cves.append(cve)
        else:
            logger.warning("Unknown CVE source requested", extra={"source": source})
        return cves

    async def scan_all_sources(self, days_back: int = 7) -> ScanResult:
        """Scan all enabled sources.

        Args:
            days_back: Days to look back

        Returns:
            ScanResult with aggregated stats
        """
        scan_id = str(uuid4())
        result = ScanResult(
            scan_id=scan_id,
            source=CVESource.NVD,
            started_at=datetime.now(timezone.utc),
        )

        cves_found = 0
        errors: List[str] = []

        if "nvd" in self.config.enabled_sources:
            try:
                async for _ in self.scan_nvd(days_back=days_back):
                    cves_found += 1
            except Exception as e:
                errors.append(f"NVD: {e}")

        if "github" in self.config.enabled_sources:
            try:
                async for _ in self.scan_github():
                    cves_found += 1
            except Exception as e:
                errors.append(f"GitHub: {e}")

        if "cisa_kev" in self.config.enabled_sources:
            try:
                async for _ in self.scan_cisa_kev():
                    cves_found += 1
            except Exception as e:
                errors.append(f"CISA KEV: {e}")

        if "osv" in self.config.enabled_sources:
            try:
                async for _ in self.scan_osv():
                    cves_found += 1
            except Exception as e:
                errors.append(f"OSV: {e}")

        result.completed_at = datetime.now(timezone.utc)
        result.success = not errors
        result.cves_found = cves_found
        result.errors = errors
        if result.completed_at and result.started_at:
            result.duration_seconds = (
                result.completed_at - result.started_at
            ).total_seconds()

        return result
