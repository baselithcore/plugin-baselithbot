"""Process-wide singleton wiring for the news service.

Builds one :class:`NewsService` from the plugin's :class:`ControlConfig` and
reuses it across requests so the TTL cache and last-good snapshot are shared.
Rebuilds only when the effective config changes (e.g. a reload with new feeds).
"""

from __future__ import annotations

from ...config import ControlConfig
from .feeds import resolve_feeds
from .service import NewsService

_service: NewsService | None = None
_signature: tuple[object, ...] | None = None


def _config_signature(cfg: ControlConfig) -> tuple[object, ...]:
    """A cheap identity for the news-relevant slice of the config."""
    feeds = cfg.news_feeds
    feeds_key: object = tuple(sorted(str(f) for f in feeds)) if feeds else None
    return (
        cfg.news_enabled,
        cfg.news_cache_ttl_seconds,
        cfg.news_max_items,
        cfg.news_fetch_timeout_seconds,
        cfg.news_allow_internal,
        feeds_key,
    )


def get_news_service(cfg: ControlConfig) -> NewsService:
    """Return the shared :class:`NewsService`, rebuilding on config change."""
    global _service, _signature
    signature = _config_signature(cfg)
    if _service is None or signature != _signature:
        _service = NewsService(
            feeds=resolve_feeds(cfg.news_feeds),
            ttl_seconds=cfg.news_cache_ttl_seconds,
            max_items=cfg.news_max_items,
            timeout=cfg.news_fetch_timeout_seconds,
            allow_internal=cfg.news_allow_internal,
            enabled=cfg.news_enabled,
        )
        _signature = signature
    return _service


__all__ = ["get_news_service"]
