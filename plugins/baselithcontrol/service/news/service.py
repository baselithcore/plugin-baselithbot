"""News aggregation service: fetch → parse → merge → cache for the ticker.

Orchestrates the configured feeds into one newest-first, de-duplicated list and
caches it so the ticker poll is cheap. Reuses core machinery rather than rolling
its own: :class:`core.cache.TTLCache` (TTL snapshot), ``SingleFlight`` (one
in-flight refresh shared by concurrent callers — no thundering herd), and the
resilient :mod:`fetcher`. A failed refresh serves the last good snapshot
(``stale``) instead of an empty ticker; only a cold failure degrades to empty.
"""

from __future__ import annotations

import asyncio
import time
from typing import Protocol

import httpx

from core.cache import TTLCache
from core.cache.single_flight import SingleFlight
from core.observability.logging import get_logger

from .fetcher import FeedFetchError, fetch_feed
from .models import FeedSpec, NewsItem, NewsResponse
from .parser import parse_feed

logger = get_logger(__name__)

_CACHE_KEY = "news"
_PER_FEED = 20  # cap items pulled from any single source before merge


class FeedFetcher(Protocol):
    """Injectable fetch seam (overridden in tests to avoid real network)."""

    async def __call__(
        self,
        client: httpx.AsyncClient,
        feed: FeedSpec,
        *,
        timeout: float,
        allow_internal: bool,
    ) -> bytes: ...


class NewsService:
    """Build and cache the merged news snapshot for the dashboard ticker."""

    def __init__(
        self,
        *,
        feeds: tuple[FeedSpec, ...],
        ttl_seconds: float,
        max_items: int,
        timeout: float,
        allow_internal: bool,
        enabled: bool,
        fetcher: FeedFetcher | None = None,
    ) -> None:
        self._feeds = feeds
        self._max_items = max_items
        self._timeout = timeout
        self._allow_internal = allow_internal
        self._enabled = enabled
        self._fetcher: FeedFetcher = fetcher or fetch_feed
        self._cache: TTLCache[str, NewsResponse] = TTLCache(
            maxsize=2, ttl=ttl_seconds, metrics_name="baselithcontrol_news"
        )
        self._flight: SingleFlight[NewsResponse] = SingleFlight()
        self._last_good: NewsResponse | None = None

    async def get_news(self) -> NewsResponse:
        """Return the cached snapshot, refreshing once on miss (single-flight)."""
        if not self._enabled or not self._feeds:
            return NewsResponse(generated_at=time.time(), degraded=True)
        cached = await self._cache.get(_CACHE_KEY)
        if cached is not None:
            return cached
        return await self._flight.do(_CACHE_KEY, self._refresh)

    async def _refresh(self) -> NewsResponse:
        """Fetch every feed, merge, cache. Falls back to the last good snapshot."""
        cached = await self._cache.get(_CACHE_KEY)  # racing callers re-check
        if cached is not None:
            return cached
        items = await self._collect()
        now = time.time()
        if not items and self._last_good is not None:
            return self._last_good.model_copy(
                update={"stale": True, "generated_at": now}
            )
        resp = NewsResponse(
            generated_at=now, count=len(items), items=items, degraded=not items
        )
        if items:
            self._last_good = resp
            await self._cache.set(_CACHE_KEY, resp)
        return resp

    async def _collect(self) -> list[NewsItem]:
        """Concurrently fetch + parse all feeds, then merge/dedup/sort/cap."""
        async with httpx.AsyncClient() as client:
            results = await asyncio.gather(
                *(self._one(client, feed) for feed in self._feeds),
                return_exceptions=True,
            )
        merged: list[NewsItem] = []
        for result in results:
            if isinstance(result, BaseException):
                continue
            merged.extend(result)
        return _dedup_sort_cap(merged, self._max_items)

    async def _one(
        self, client: httpx.AsyncClient, feed: FeedSpec
    ) -> list[NewsItem]:
        """Fetch + parse a single feed, degrading to ``[]`` on any failure."""
        try:
            payload = await self._fetcher(
                client,
                feed,
                timeout=self._timeout,
                allow_internal=self._allow_internal,
            )
        except FeedFetchError:
            return []
        except Exception as exc:  # noqa: BLE001 — never let one feed break others
            logger.warning("News feed %s errored: %s", feed.source, exc)
            return []
        return parse_feed(payload, feed, limit=_PER_FEED)


def _dedup_sort_cap(items: list[NewsItem], max_items: int) -> list[NewsItem]:
    """Sort newest-first, drop duplicate URLs (keep newest), cap the count."""
    ordered = sorted(
        items,
        key=lambda i: (i.published_at is not None, i.published_at or 0.0),
        reverse=True,
    )
    seen: set[str] = set()
    out: list[NewsItem] = []
    for item in ordered:
        key = item.url.rstrip("/").lower()
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
        if len(out) >= max_items:
            break
    return out


__all__ = ["NewsService", "FeedFetcher"]
