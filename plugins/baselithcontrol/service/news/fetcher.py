"""Resilient outbound fetch for a single news feed.

Every feed URL is attacker-influenceable config, so the fetch path reuses the
core SSRF guard at **delivery strength**: each request (and each redirect hop)
is validated *and pinned* via :func:`core.webhooks.ssrf.resolve_pinned_target`
— the connection goes to the exact IP the guard vetted, with the original
hostname as ``Host`` header and TLS SNI, so neither a malicious 3xx from a
compromised feed nor a DNS rebind between validation and connection can reach
an internal address. Redirects are followed manually (bounded) with per-hop
re-validation; the body is streamed with a hard byte ceiling so a hostile feed
cannot balloon memory. The HTTP call is wrapped in the core retry policy
(:func:`core.resilience.retry`) with a hard timeout. A persistently-failing
source is absorbed at the service layer, which serves the last good snapshot
rather than an empty ticker. Reuse over re-implementation, per the core-reuse
convention.
"""

from __future__ import annotations

import asyncio
from urllib.parse import urljoin

import httpx

from core.observability.logging import get_logger
from core.resilience import retry
from core.webhooks.ssrf import WebhookSSRFError, resolve_pinned_target

from .models import FeedSpec

logger = get_logger(__name__)

_USER_AGENT = "BaselithControl-NewsTicker/1.0 (+https://baselithcore.xyz)"
_MAX_BYTES = 2_000_000  # 2 MB ceiling, enforced while streaming (never buffered)
_MAX_REDIRECTS = 3
_REDIRECT_CODES = frozenset({301, 302, 303, 307, 308})
_ACCEPT = "application/rss+xml, application/atom+xml, application/xml, text/xml"


class FeedFetchError(RuntimeError):
    """A feed could not be fetched (network, HTTP, or SSRF rejection)."""


async def _read_capped(resp: httpx.Response) -> bytes:
    """Stream the body up to ``_MAX_BYTES`` — a hostile feed cannot balloon RAM."""
    chunks: list[bytes] = []
    total = 0
    async for chunk in resp.aiter_bytes():
        remaining = _MAX_BYTES - total
        if len(chunk) > remaining:
            chunks.append(chunk[:remaining])
            logger.warning(
                "News feed %s truncated at %d bytes", resp.request.url, _MAX_BYTES
            )
            break
        chunks.append(chunk)
        total += len(chunk)
    return b"".join(chunks)


@retry(max_attempts=2, base_delay=0.4, exponential_base=2.0)
async def _pinned_get(
    client: httpx.AsyncClient, url: str, timeout: float, allow_internal: bool
) -> bytes:
    """GET ``url`` with per-hop SSRF pinning, manual redirects, streamed cap.

    Raises:
        WebhookSSRFError: If any hop resolves to an internal address.
        FeedFetchError: On redirect loops or a redirect without ``Location``.
        httpx.HTTPStatusError: On a non-2xx final response.
    """
    current = url
    for _ in range(_MAX_REDIRECTS + 1):
        # DNS resolution inside the guard is blocking — keep it off the loop.
        pinned_url, pin_host = await asyncio.to_thread(
            resolve_pinned_target, current, allow_internal=allow_internal
        )
        request = client.build_request(
            "GET",
            pinned_url,
            headers={"User-Agent": _USER_AGENT, "Accept": _ACCEPT, "Host": pin_host},
            timeout=timeout,
            extensions={"sni_hostname": pin_host},
        )
        resp = await client.send(request, stream=True, follow_redirects=False)
        try:
            if resp.status_code in _REDIRECT_CODES:
                location = resp.headers.get("location")
                if not location:
                    raise FeedFetchError(f"redirect without Location from {current}")
                current = urljoin(current, location)
                continue
            resp.raise_for_status()
            return await _read_capped(resp)
        finally:
            await resp.aclose()
    raise FeedFetchError(f"too many redirects for {url}")


async def fetch_feed(
    client: httpx.AsyncClient,
    feed: FeedSpec,
    *,
    timeout: float = 6.0,
    allow_internal: bool = False,
) -> bytes:
    """Fetch a feed's raw bytes — SSRF-pinned per hop, retried, size-capped.

    Args:
        client: A shared async HTTP client (connection reuse across feeds).
        feed: The source to fetch.
        timeout: Per-request timeout in seconds.
        allow_internal: Skip the private/loopback SSRF checks (dev only).

    Raises:
        FeedFetchError: On SSRF rejection, network error, or non-2xx response.
    """
    try:
        return await _pinned_get(client, feed.url, timeout, allow_internal)
    except WebhookSSRFError as exc:
        logger.warning("News feed %s rejected by SSRF guard: %s", feed.url, exc)
        raise FeedFetchError(str(exc)) from exc
    except FeedFetchError:
        raise
    except Exception as exc:  # noqa: BLE001 — normalise to one fetch error type
        raise FeedFetchError(f"fetch failed for {feed.source}: {exc}") from exc


__all__ = ["fetch_feed", "FeedFetchError"]
