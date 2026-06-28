"""Wire + domain models for the dashboard news ticker.

These DTOs are the stable contract between the news service, the read-only
``/news`` route, and the React ticker. News items come from public RSS/Atom
feeds — global reference data, identical for every operator — so nothing here is
tenant-scoped (cf. the convention for security-ops catalog data).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

NEWS_API_VERSION = "1"


class NewsCategory(str, Enum):
    """Coarse topic bucket projected onto each item (drives the accent colour).

    Mirrors the digest's themes; ``general`` is the safe fallback when a feed is
    not pinned to a specific lane.
    """

    ai = "ai"
    society = "society"
    regulation = "regulation"
    repos = "repos"
    tech = "tech"
    cyber = "cyber"
    general = "general"


class FeedSpec(BaseModel):
    """A single configured RSS/Atom source.

    ``url`` is operator/config-supplied and therefore treated as untrusted at
    fetch time (SSRF-guarded). ``source`` is the short label shown in the ticker
    and ``category`` colours it.
    """

    url: str
    source: str
    category: NewsCategory = NewsCategory.general
    lang: str | None = None  # "en" | "it" | None (unknown)


class NewsItem(BaseModel):
    """One headline rendered in the scrolling ticker."""

    title: str
    url: str
    source: str
    category: NewsCategory = NewsCategory.general
    published_at: float | None = None  # epoch seconds, newest-first ordering
    lang: str | None = None


class NewsResponse(BaseModel):
    """The ticker payload: newest-first items plus freshness metadata."""

    api_version: str = NEWS_API_VERSION
    generated_at: float = Field(..., description="Epoch seconds of this snapshot.")
    count: int = 0
    items: list[NewsItem] = Field(default_factory=list)
    # ``stale`` = served from the last good snapshot after a refresh failure.
    # ``degraded`` = no items at all (every feed unreachable, or disabled).
    stale: bool = False
    degraded: bool = False


__all__ = [
    "NEWS_API_VERSION",
    "NewsCategory",
    "FeedSpec",
    "NewsItem",
    "NewsResponse",
]
