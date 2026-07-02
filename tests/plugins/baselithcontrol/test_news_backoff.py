"""News service failure cooldown: an outage must not refetch on every poll."""

from __future__ import annotations

import time
from typing import Any

from plugins.baselithcontrol.service.news.models import FeedSpec, NewsCategory
from plugins.baselithcontrol.service.news.service import NewsService

_FEED = FeedSpec(
    url="https://example.com/rss", source="X", category=NewsCategory.ai, lang="en"
)

_RSS = b"""<?xml version="1.0"?>
<rss version="2.0"><channel><title>X</title>
<item><title>Hello</title><link>https://example.com/a</link>
<pubDate>Mon, 01 Jun 2026 10:00:00 GMT</pubDate></item>
</channel></rss>"""


class _Fetcher:
    def __init__(self) -> None:
        self.calls = 0
        self.fail = True

    async def __call__(self, client: Any, feed: Any, **_: Any) -> bytes:
        self.calls += 1
        if self.fail:
            raise RuntimeError("boom")
        return _RSS


def _service(fetcher: _Fetcher) -> NewsService:
    return NewsService(
        feeds=(_FEED,),
        ttl_seconds=600.0,
        max_items=10,
        timeout=1.0,
        allow_internal=True,
        enabled=True,
        fetcher=fetcher,
    )


async def test_failed_refresh_enters_cooldown_instead_of_refetching() -> None:
    fetcher = _Fetcher()
    svc = _service(fetcher)

    first = await svc.get_news()
    assert first.degraded is True and fetcher.calls == 1

    # Within the cooldown window every poll is served without a refetch.
    second = await svc.get_news()
    third = await svc.get_news()
    assert fetcher.calls == 1
    assert second.degraded is True and third.degraded is True


async def test_recovery_after_cooldown_serves_fresh_items() -> None:
    fetcher = _Fetcher()
    svc = _service(fetcher)
    assert (await svc.get_news()).degraded is True

    fetcher.fail = False
    svc._backoff_until = time.monotonic() - 1  # expire the cooldown
    fresh = await svc.get_news()
    assert fresh.degraded is False and fresh.count == 1
    assert fetcher.calls == 2

    # A later failure serves the stale-but-good snapshot during cooldown.
    fetcher.fail = True
    await svc._cache.clear()
    stale = await svc.get_news()
    assert stale.stale is True and stale.count == 1
    again = await svc.get_news()
    assert again.stale is True and fetcher.calls == 3
