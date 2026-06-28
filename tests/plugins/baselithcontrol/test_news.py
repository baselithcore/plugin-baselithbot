"""Tests for the BaselithControl news ticker (parse, fetch guard, aggregation).

No real network: the HTTP fetch seam is injected. SSRF rejection is exercised
against an IP literal so it stays deterministic and offline.
"""

from __future__ import annotations

import httpx
import pytest

from plugins.baselithcontrol.service.news.feeds import DEFAULT_FEEDS, resolve_feeds
from plugins.baselithcontrol.service.news.fetcher import FeedFetchError, fetch_feed
from plugins.baselithcontrol.service.news.models import (
    FeedSpec,
    NewsCategory,
    NewsItem,
    NewsResponse,
)
from plugins.baselithcontrol.service.news.parser import parse_feed
from plugins.baselithcontrol.service.news.service import NewsService, _dedup_sort_cap

RSS = b"""<?xml version='1.0'?><rss version='2.0'><channel><title>X</title>
<item><title>Hello &amp; World</title><link>https://example.com/a</link>
<pubDate>Sat, 27 Jun 2026 10:00:00 +0000</pubDate>
<description>&lt;p&gt;body&lt;/p&gt;</description></item>
<item><title>Older</title><link>https://example.com/b</link>
<pubDate>Fri, 26 Jun 2026 09:00:00 +0000</pubDate></item></channel></rss>"""

ATOM = b"""<?xml version='1.0'?><feed xmlns='http://www.w3.org/2005/Atom'>
<entry><title>Atom One</title>
<link href='https://example.org/x' rel='alternate'/>
<updated>2026-06-28T08:00:00Z</updated></entry></feed>"""

AI_FEED = FeedSpec(
    url="https://example.com/feed", source="Test", category=NewsCategory.ai
)
TECH_FEED = FeedSpec(
    url="https://example.org/feed", source="AtomSrc", category=NewsCategory.tech
)


def test_parse_rss_decodes_entities_and_strips_html() -> None:
    items = parse_feed(RSS, AI_FEED)
    assert [i.title for i in items] == ["Hello & World", "Older"]
    assert items[0].url == "https://example.com/a"
    assert items[0].category is NewsCategory.ai
    assert items[0].published_at and items[0].published_at > items[1].published_at  # type: ignore[operator]


def test_parse_decodes_html_entities_in_title() -> None:
    # Double-encoded entities + entity-encoded tags must render as clean text,
    # not literal "&#8217;" / "&lt;b&gt;" (the ticker mis-format bug).
    feed_xml = (
        b"<rss><channel><item>"
        b"<title>China claims the world&amp;#8217;s fastest &amp;lt;b&amp;gt;super&amp;lt;/b&amp;gt;</title>"
        b"<link>https://example.com/c</link></item></channel></rss>"
    )
    items = parse_feed(feed_xml, AI_FEED)
    assert items[0].title == "China claims the world’s fastest super"


def test_parse_atom_uses_href_link() -> None:
    items = parse_feed(ATOM, TECH_FEED)
    assert items and items[0].url == "https://example.org/x"
    assert items[0].source == "AtomSrc"


def test_parse_malformed_returns_empty() -> None:
    assert parse_feed(b"<not xml", AI_FEED) == []
    assert parse_feed(b"", AI_FEED) == []


def test_parse_drops_items_without_usable_link() -> None:
    bad = b"<rss><channel><item><title>NoLink</title></item></channel></rss>"
    assert parse_feed(bad, AI_FEED) == []


def test_dedup_sort_cap_orders_and_dedupes() -> None:
    items = [
        NewsItem(title="old", url="https://x/1", source="s", published_at=100.0),
        NewsItem(title="new", url="https://x/2", source="s", published_at=200.0),
        NewsItem(title="dup", url="https://x/2/", source="s", published_at=150.0),
        NewsItem(title="undated", url="https://x/3", source="s", published_at=None),
    ]
    out = _dedup_sort_cap(items, max_items=10)
    # newest first, trailing-slash dup of /2 removed, undated sinks to the end
    assert [i.title for i in out] == ["new", "old", "undated"]


def test_resolve_feeds_precedence_deploy_then_manifest_then_default() -> None:
    from plugins.baselithcontrol.service.news.feeds import manifest_feeds

    declared = manifest_feeds()
    assert declared, "manifest should declare news_feeds"
    # no deploy override → manifest list wins (not the hardcoded defaults)
    assert resolve_feeds(None) == declared
    assert resolve_feeds([]) == declared
    # a deploy override takes precedence over the manifest
    custom = resolve_feeds(
        [{"url": "https://a/feed", "source": "A", "category": "cyber"}]
    )
    assert len(custom) == 1 and custom[0].category is NewsCategory.cyber
    # a malformed-only override is dropped → falls through to the manifest
    assert resolve_feeds([{"nope": 1}]) == declared


def test_default_feeds_is_code_fallback() -> None:
    # DEFAULT_FEEDS stays the last-resort fallback when nothing else resolves.
    assert DEFAULT_FEEDS and all(f.url.startswith("https://") for f in DEFAULT_FEEDS)


async def test_fetch_feed_rejects_internal_address() -> None:
    blocked = FeedSpec(url="http://127.0.0.1:9/feed", source="local")
    async with httpx.AsyncClient() as client:
        with pytest.raises(FeedFetchError):
            await fetch_feed(client, blocked, timeout=1.0)


async def test_service_merges_sorts_and_caches() -> None:
    async def fake(_client: httpx.AsyncClient, feed: FeedSpec, **_: object) -> bytes:
        return RSS if "example.com" in feed.url else ATOM

    svc = NewsService(
        feeds=(AI_FEED, TECH_FEED),
        ttl_seconds=60,
        max_items=10,
        timeout=5,
        allow_internal=False,
        enabled=True,
        fetcher=fake,
    )
    resp = await svc.get_news()
    assert resp.count == 3 and not resp.degraded and not resp.stale
    assert resp.items[0].title == "Atom One"  # 2026-06-28 is newest
    # second call hits the cache and is identical
    assert (await svc.get_news()).items[0].url == resp.items[0].url


async def test_service_disabled_is_degraded() -> None:
    svc = NewsService(
        feeds=(AI_FEED,),
        ttl_seconds=60,
        max_items=10,
        timeout=5,
        allow_internal=False,
        enabled=False,
    )
    resp = await svc.get_news()
    assert resp.degraded and resp.count == 0


async def test_service_cold_failure_is_degraded() -> None:
    async def boom(_client: httpx.AsyncClient, _feed: FeedSpec, **_: object) -> bytes:
        raise FeedFetchError("down")

    svc = NewsService(
        feeds=(AI_FEED,),
        ttl_seconds=60,
        max_items=10,
        timeout=5,
        allow_internal=False,
        enabled=True,
        fetcher=boom,
    )
    cold = await svc.get_news()
    assert cold.degraded and cold.count == 0


async def test_service_serves_last_good_as_stale_on_refresh_failure() -> None:
    async def boom(_client: httpx.AsyncClient, _feed: FeedSpec, **_: object) -> bytes:
        raise FeedFetchError("down")

    svc = NewsService(
        feeds=(AI_FEED,),
        ttl_seconds=60,
        max_items=10,
        timeout=5,
        allow_internal=False,
        enabled=True,
        fetcher=boom,
    )
    # Seed a prior good snapshot, then force a refresh: the failure must not
    # blank the ticker — it serves the last good items flagged ``stale``.
    svc._last_good = NewsResponse(
        generated_at=1.0,
        count=1,
        items=[
            NewsItem(title="cached", url="https://x/1", source="s", published_at=1.0)
        ],
    )
    stale = await svc._refresh()
    assert stale.stale and not stale.degraded
    assert stale.items[0].title == "cached"
