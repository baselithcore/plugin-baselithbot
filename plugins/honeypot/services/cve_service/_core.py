"""CVE Lookup Service core.

Provides dynamic CVE intelligence from the National Vulnerability Database (NVD)
using nvdlib. Includes caching, rate limiting, and fallback mechanisms.
"""

import asyncio
import re
import time
from datetime import datetime, timezone
from typing import Dict, List, Optional

from core.observability.logging import get_logger

from ...config import HoneypotConfig, get_honeypot_config
from ...models.cve import CVEData, CVELookupStats, CVESearchResult
from ._cache import CacheMixin
from ._nvd import NVDMixin

logger = get_logger(__name__)


class CVEService(CacheMixin, NVDMixin):
    """CVE lookup service with caching and rate limiting.

    Integrates with NVD API via nvdlib for dynamic vulnerability intelligence.
    Features:
    - Redis-backed caching (7-day TTL)
    - NVD API rate limiting compliance
    - Async/await for non-blocking I/O
    - Fallback to static patterns if NVD unavailable
    - Telemetry and performance tracking
    """

    def __init__(
        self,
        config: Optional[HoneypotConfig] = None,
        redis_client=None,
    ):
        """Initialize CVE service.

        Args:
            config: Honeypot configuration
            redis_client: Optional Redis client for caching
        """
        self.config = config or get_honeypot_config()
        self._redis = redis_client
        self._cache: Dict[str, CVEData] = {}  # In-memory fallback cache

        # Stats tracking
        self._stats = CVELookupStats()
        self._latencies: List[float] = []

        # Rate limiting state (NVD: 0.6s with key, 6s without)
        self._last_api_call = 0.0
        self._rate_limit_delay = 0.6 if self.config.nvd_api_key else 6.0

        logger.info(
            f"CVE Service initialized (API key: {'✓' if self.config.nvd_api_key else '✗'}, "
            f"rate limit: {self._rate_limit_delay}s)"
        )

    async def lookup_cve(self, cve_id: str) -> Optional[CVEData]:
        """Lookup a specific CVE by ID.

        Args:
            cve_id: CVE identifier (e.g., CVE-2021-44228)

        Returns:
            CVE data or None if not found
        """
        if not self._validate_cve_id(cve_id):
            logger.warning(f"Invalid CVE ID format: {cve_id}")
            return None

        self._stats.total_lookups += 1
        start_time = time.time()

        # Check cache first
        cached = await self._get_from_cache(cve_id)
        if cached:
            self._stats.cache_hits += 1
            latency = (time.time() - start_time) * 1000
            self._record_latency(latency)
            logger.debug(f"Cache hit for {cve_id} ({latency:.1f}ms)")
            return cached

        self._stats.cache_misses += 1

        # Fetch from NVD (with rate limiting)
        try:
            await self._rate_limit()
            cve_data = await self._fetch_from_nvd(cve_id)

            if cve_data:
                # Store in cache
                await self._store_in_cache(cve_id, cve_data)

            latency = (time.time() - start_time) * 1000
            self._record_latency(latency)
            logger.info(f"NVD lookup for {cve_id} ({latency:.1f}ms)")
            return cve_data

        except Exception as e:
            self._stats.errors += 1
            logger.error(f"CVE lookup failed for {cve_id}: {e}")
            return None

    async def search_by_cwe(self, cwe_id: str, limit: int = 10) -> CVESearchResult:
        """Search CVEs by CWE identifier.

        Args:
            cwe_id: CWE identifier (e.g., CWE-89)
            limit: Maximum results to return

        Returns:
            Search results with matched CVEs
        """
        start_time = time.time()
        cache_key = f"cwe:{cwe_id}:limit:{limit}"

        # Check cache
        cached = await self._get_search_from_cache(cache_key)
        if cached:
            self._stats.cache_hits += 1
            return cached

        self._stats.cache_misses += 1

        # Search NVD
        try:
            await self._rate_limit()
            results = await self._search_nvd_by_cwe(cwe_id, limit)

            latency = (time.time() - start_time) * 1000
            search_result = CVESearchResult(
                query=cwe_id,
                query_type="cwe",
                results=results,
                total_found=len(results),
                cached=False,
                timestamp=datetime.now(timezone.utc),
                latency_ms=latency,
            )

            # Cache results
            await self._store_search_in_cache(cache_key, search_result)

            logger.info(
                f"CWE search for {cwe_id}: {len(results)} results ({latency:.1f}ms)"
            )
            return search_result

        except Exception as e:
            self._stats.errors += 1
            logger.error(f"CWE search failed for {cwe_id}: {e}")
            return CVESearchResult(
                query=cwe_id,
                query_type="cwe",
                results=[],
                total_found=0,
                cached=False,
                timestamp=datetime.now(timezone.utc),
            )

    async def search_by_keywords(
        self, keywords: List[str], limit: int = 10
    ) -> CVESearchResult:
        """Search CVEs by keywords.

        Args:
            keywords: Keywords to search for
            limit: Maximum results to return

        Returns:
            Search results with matched CVEs
        """
        start_time = time.time()
        keyword_str = " ".join(sorted(keywords))
        cache_key = f"keywords:{keyword_str}:limit:{limit}"

        # Check cache
        cached = await self._get_search_from_cache(cache_key)
        if cached:
            self._stats.cache_hits += 1
            return cached

        self._stats.cache_misses += 1

        # Search NVD
        try:
            await self._rate_limit()
            results = await self._search_nvd_by_keywords(keywords, limit)

            latency = (time.time() - start_time) * 1000
            search_result = CVESearchResult(
                query=keyword_str,
                query_type="keyword",
                results=results,
                total_found=len(results),
                cached=False,
                timestamp=datetime.now(timezone.utc),
                latency_ms=latency,
            )

            # Cache results
            await self._store_search_in_cache(cache_key, search_result)

            logger.info(
                f"Keyword search for '{keyword_str}': {len(results)} results ({latency:.1f}ms)"
            )
            return search_result

        except Exception as e:
            self._stats.errors += 1
            logger.error(f"Keyword search failed for '{keyword_str}': {e}")
            return CVESearchResult(
                query=keyword_str,
                query_type="keyword",
                results=[],
                total_found=0,
                cached=False,
                timestamp=datetime.now(timezone.utc),
            )

    async def get_recent_cves(self, limit: int = 30) -> List[CVEData]:
        """Get recently published CVEs.

        Args:
            limit: Maximum number of CVEs to return

        Returns:
            List of recent CVE data
        """
        cache_key = f"recent:{limit}"

        # Check cache
        cached = await self._get_search_from_cache(cache_key)
        if cached:
            self._stats.cache_hits += 1
            return cached.results

        self._stats.cache_misses += 1

        # Fetch from NVD
        try:
            await self._rate_limit()
            results = await self._fetch_recent_from_nvd(limit)

            # Cache results
            search_result = CVESearchResult(
                query=f"recent_{limit}",
                query_type="recent",
                results=results,
                total_found=len(results),
                cached=False,
                timestamp=datetime.now(timezone.utc),
            )
            await self._store_search_in_cache(cache_key, search_result)

            logger.info(f"Fetched {len(results)} recent CVEs")
            return results

        except Exception as e:
            self._stats.errors += 1
            logger.error(f"Failed to fetch recent CVEs: {e}")
            return []

    async def bulk_lookup(self, cve_ids: List[str]) -> Dict[str, Optional[CVEData]]:
        """Bulk lookup multiple CVEs.

        Args:
            cve_ids: List of CVE IDs to lookup

        Returns:
            Dict mapping CVE ID to CVE data
        """
        tasks = [self.lookup_cve(cve_id) for cve_id in cve_ids]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        return {
            cve_id: result if not isinstance(result, Exception) else None
            for cve_id, result in zip(cve_ids, results)
        }

    def get_stats(self) -> CVELookupStats:
        """Get service statistics.

        Returns:
            CVE lookup statistics
        """
        if self._latencies:
            self._stats.avg_latency_ms = sum(self._latencies) / len(self._latencies)
        return self._stats

    # =========================================================================
    # Private helpers
    # =========================================================================

    def _validate_cve_id(self, cve_id: str) -> bool:
        """Validate CVE ID format.

        Args:
            cve_id: CVE identifier to validate

        Returns:
            True if valid format
        """
        pattern = r"^CVE-\d{4}-\d{4,}$"
        return bool(re.match(pattern, cve_id, re.IGNORECASE))

    async def _rate_limit(self) -> None:
        """Enforce NVD API rate limiting."""
        now = time.time()
        elapsed = now - self._last_api_call

        if elapsed < self._rate_limit_delay:
            wait_time = self._rate_limit_delay - elapsed
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)

        self._last_api_call = time.time()

    def _record_latency(self, latency_ms: float) -> None:
        """Record latency for stats.

        Args:
            latency_ms: Latency in milliseconds
        """
        self._latencies.append(latency_ms)
        # Keep last 100 measurements
        if len(self._latencies) > 100:
            self._latencies = self._latencies[-100:]


# Global instance
_cve_service: Optional[CVEService] = None


async def get_cve_service(redis_client=None) -> CVEService:
    """Get or create global CVE service instance.

    Args:
        redis_client: Optional Redis client

    Returns:
        CVE service instance
    """
    global _cve_service
    if _cve_service is None:
        _cve_service = CVEService(redis_client=redis_client)
    return _cve_service
