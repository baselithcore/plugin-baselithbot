"""Resilient outbound fetch for a single news feed.

Every feed URL is attacker-influenceable config, so the fetch path reuses the
core SSRF guard (:func:`core.webhooks.ssrf.validate_webhook_url`) to reject
loopback/private/link-local/metadata targets before any connection, and wraps
the HTTP call in the core retry policy (:func:`core.resilience.retry`) with a
hard timeout and a response-size ceiling. A persistently-failing source is
absorbed at the service layer, which serves the last good snapshot rather than
an empty ticker. Reuse over re-implementation, per the core-reuse convention.
"""

from __future__ import annotations

import asyncio

import httpx

from core.observability.logging import get_logger
from core.resilience import retry
from core.webhooks.ssrf import WebhookSSRFError, validate_webhook_url

from .models import FeedSpec

logger = get_logger(__name__)

_USER_AGENT = "BaselithControl-NewsTicker/1.0 (+https://baselithcore.xyz)"
_MAX_BYTES = 2_000_000  # 2 MB ceiling — feeds are small; cap defends memory.


class FeedFetchError(RuntimeError):
    """A feed could not be fetched (network, HTTP, or SSRF rejection)."""


@retry(max_attempts=2, base_delay=0.4, exponential_base=2.0)
async def _http_get(client: httpx.AsyncClient, url: str, timeout: float) -> bytes:
    """GET ``url`` with a hard timeout, returning at most ``_MAX_BYTES``."""
    accept = "application/rss+xml, application/atom+xml, application/xml, text/xml"
    resp = await client.get(
        url,
        timeout=timeout,
        follow_redirects=True,
        headers={"User-Agent": _USER_AGENT, "Accept": accept},
    )
    resp.raise_for_status()
    return resp.content[:_MAX_BYTES]


async def fetch_feed(
    client: httpx.AsyncClient,
    feed: FeedSpec,
    *,
    timeout: float = 6.0,
    allow_internal: bool = False,
) -> bytes:
    """Fetch a feed's raw bytes, SSRF-guarded and retried.

    Args:
        client: A shared async HTTP client (connection reuse across feeds).
        feed: The source to fetch.
        timeout: Per-request timeout in seconds.
        allow_internal: Skip the private/loopback SSRF checks (dev only).

    Raises:
        FeedFetchError: On SSRF rejection, network error, or non-2xx response.
    """
    try:
        # DNS resolution inside the guard is blocking — keep it off the loop.
        await asyncio.to_thread(
            validate_webhook_url, feed.url, allow_internal=allow_internal
        )
    except WebhookSSRFError as exc:
        logger.warning("News feed %s rejected by SSRF guard: %s", feed.url, exc)
        raise FeedFetchError(str(exc)) from exc

    try:
        return await _http_get(client, feed.url, timeout)
    except Exception as exc:  # noqa: BLE001 — normalise to one fetch error type
        raise FeedFetchError(f"fetch failed for {feed.source}: {exc}") from exc


__all__ = ["fetch_feed", "FeedFetchError"]
