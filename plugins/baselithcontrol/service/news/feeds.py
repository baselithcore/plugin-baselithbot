"""Public RSS/Atom feed set for the dashboard news ticker.

Sources are resolved by precedence (:func:`resolve_feeds`):

1. **Deploy override** — ``news_feeds`` in the plugin block of
   ``configs/plugins.yaml`` (or the ``BASELITHCONTROL_NEWS_FEEDS`` env JSON).
2. **Manifest** — the declarative ``news_feeds:`` list in the plugin's own
   ``manifest.yaml``. This is the recommended place to curate the sources: it
   ships with the plugin, is editable without touching code, and does **not**
   affect ``integrity_sha256`` (the signature only covers ``*.py``).
3. **Code default** — :data:`DEFAULT_FEEDS` below, the last-resort fallback.

Every URL is SSRF-validated at fetch time regardless of where it came from, so a
misconfigured feed can never reach an internal address. Malformed entries are
dropped (validated through :class:`FeedSpec`), never fatal.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from core.observability.logging import get_logger

from .models import FeedSpec, NewsCategory

logger = get_logger(__name__)

# plugins/baselithcontrol/service/news/feeds.py → plugins/baselithcontrol/
_MANIFEST_PATH = Path(__file__).resolve().parents[2] / "manifest.yaml"

# Public, https-only, stable feeds. Kept intentionally small so a single slow
# source never dominates the fetch window; the ticker dedups + caps anyway.
DEFAULT_FEEDS: tuple[FeedSpec, ...] = (
    # ── AI / models ──────────────────────────────────────────────────────
    FeedSpec(
        url="https://techcrunch.com/category/artificial-intelligence/feed/",
        source="TechCrunch AI",
        category=NewsCategory.ai,
        lang="en",
    ),
    FeedSpec(
        url="https://venturebeat.com/category/ai/feed/",
        source="VentureBeat",
        category=NewsCategory.ai,
        lang="en",
    ),
    # ── General technology ───────────────────────────────────────────────
    FeedSpec(
        url="https://www.theverge.com/rss/index.xml",
        source="The Verge",
        category=NewsCategory.tech,
        lang="en",
    ),
    FeedSpec(
        url="https://feeds.arstechnica.com/arstechnica/technology-lab",
        source="Ars Technica",
        category=NewsCategory.tech,
        lang="en",
    ),
    # ── Cybersecurity ────────────────────────────────────────────────────
    FeedSpec(
        url="https://feeds.feedburner.com/TheHackersNews",
        source="The Hacker News",
        category=NewsCategory.cyber,
        lang="en",
    ),
    FeedSpec(
        url="https://www.bleepingcomputer.com/feed/",
        source="BleepingComputer",
        category=NewsCategory.cyber,
        lang="en",
    ),
    FeedSpec(
        url="https://krebsonsecurity.com/feed/",
        source="Krebs on Security",
        category=NewsCategory.cyber,
        lang="en",
    ),
)


def _coerce_feeds(entries: list[Any] | None) -> tuple[FeedSpec, ...]:
    """Validate a raw list of feed dicts into :class:`FeedSpec`, dropping bad rows."""
    resolved: list[FeedSpec] = []
    for entry in entries or []:
        if not isinstance(entry, dict):
            continue
        try:
            resolved.append(FeedSpec.model_validate(entry))
        except Exception:  # noqa: BLE001 — skip a malformed feed, keep the rest
            continue
    return tuple(resolved)


def manifest_feeds() -> tuple[FeedSpec, ...]:
    """Read the declarative ``news_feeds:`` list from the plugin's manifest.

    Returns an empty tuple when the manifest is missing/unreadable or declares no
    feeds, so a parse error degrades to the next precedence tier rather than
    breaking the ticker.
    """
    try:
        data = yaml.safe_load(_MANIFEST_PATH.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError) as exc:
        logger.warning("Could not read news_feeds from manifest: %s", exc)
        return ()
    feeds = data.get("news_feeds") if isinstance(data, dict) else None
    return _coerce_feeds(feeds if isinstance(feeds, list) else None)


def resolve_feeds(override: list[dict[str, Any]] | None) -> tuple[FeedSpec, ...]:
    """Resolve the active feed list by precedence: deploy → manifest → default.

    ``override`` is the raw ``news_feeds`` deploy config (plugins.yaml / env). A
    non-empty, valid override wins; otherwise the manifest's declarative list is
    used; if that is also empty, the code-level :data:`DEFAULT_FEEDS` applies.
    Every tier is validated through :class:`FeedSpec` — malformed entries are
    dropped, never fatal.
    """
    deploy = _coerce_feeds(override)
    if deploy:
        return deploy
    declared = manifest_feeds()
    if declared:
        return declared
    return DEFAULT_FEEDS


__all__ = ["DEFAULT_FEEDS", "manifest_feeds", "resolve_feeds"]
