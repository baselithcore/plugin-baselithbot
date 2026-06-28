"""News-ticker service for the BaselithControl dashboard.

A small, self-contained pipeline — :mod:`feeds` (sources) → :mod:`fetcher`
(SSRF-guarded, retried HTTP) → :mod:`parser` (defused RSS/Atom) → :mod:`service`
(merge + TTL cache) — feeding the read-only ``/news`` route. News is public
reference data shared by every operator, so it is not tenant-scoped.
"""

from __future__ import annotations

from .feeds import DEFAULT_FEEDS, resolve_feeds
from .models import FeedSpec, NewsCategory, NewsItem, NewsResponse
from .service import NewsService

__all__ = [
    "DEFAULT_FEEDS",
    "resolve_feeds",
    "FeedSpec",
    "NewsCategory",
    "NewsItem",
    "NewsResponse",
    "NewsService",
]
