"""Cache mixin for CVEService.

Provides Redis-backed and in-memory caching helpers.
"""

from typing import Optional

from core.observability.logging import get_logger

from ...models.cve import CVEData, CVESearchResult

logger = get_logger(__name__)


class CacheMixin:
    """Cache helpers for CVEService."""

    async def _get_from_cache(self, cve_id: str) -> Optional[CVEData]:
        """Get CVE from cache.

        Args:
            cve_id: CVE identifier

        Returns:
            Cached CVE data or None
        """
        # Try Redis first
        if self._redis:
            try:
                cache_key = f"cve:{cve_id}"
                cached_json = await self._redis.get(cache_key)
                if cached_json:
                    return CVEData.model_validate_json(cached_json)
            except Exception as e:
                logger.warning(f"Redis cache read error: {e}")

        # Fallback to in-memory cache
        return self._cache.get(cve_id)

    async def _store_in_cache(self, cve_id: str, data: CVEData) -> None:
        """Store CVE in cache.

        Args:
            cve_id: CVE identifier
            data: CVE data to cache
        """
        data.cached = True

        # Store in Redis
        if self._redis:
            try:
                cache_key = f"cve:{cve_id}"
                await self._redis.setex(
                    cache_key,
                    self.config.cve_cache_ttl_seconds,
                    data.model_dump_json(),
                )
            except Exception as e:
                logger.warning(f"Redis cache write error: {e}")

        # Also store in memory
        self._cache[cve_id] = data

    async def _get_search_from_cache(self, cache_key: str) -> Optional[CVESearchResult]:
        """Get search results from cache.

        Args:
            cache_key: Cache key

        Returns:
            Cached search results or None
        """
        if self._redis:
            try:
                cached_json = await self._redis.get(f"search:{cache_key}")
                if cached_json:
                    result = CVESearchResult.model_validate_json(cached_json)
                    result.cached = True
                    return result
            except Exception as e:
                logger.warning(f"Redis search cache read error: {e}")

        return None

    async def _store_search_in_cache(
        self, cache_key: str, results: CVESearchResult
    ) -> None:
        """Store search results in cache.

        Args:
            cache_key: Cache key
            results: Search results to cache
        """
        if self._redis:
            try:
                await self._redis.setex(
                    f"search:{cache_key}",
                    self.config.cve_cache_ttl_seconds,
                    results.model_dump_json(),
                )
            except Exception as e:
                logger.warning(f"Redis search cache write error: {e}")
