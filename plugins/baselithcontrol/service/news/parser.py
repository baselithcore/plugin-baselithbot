"""Safe RSS/Atom parsing into normalized :class:`NewsItem` records.

Feed XML is fetched from third-party hosts, so it is untrusted input: parsing
goes through :mod:`defusedxml` (already a core dependency) to neutralise the
classic XML attacks (external entities / billion-laughs). The parser is tolerant
— it extracts what it can from either dialect and drops entries it cannot make
sense of, never raising on a malformed document.
"""

from __future__ import annotations

import html
import re
from email.utils import parsedate_to_datetime

from defusedxml import ElementTree as DefusedET  # type: ignore[import-untyped]

from .models import FeedSpec, NewsItem

# Namespace-tolerant tag match: strip any ``{uri}`` prefix ElementTree prepends.
_TAG = re.compile(r"\{.*\}")
_HTML = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def _local(tag: str) -> str:
    """Return an element's local name without its XML namespace."""
    return _TAG.sub("", tag).lower()


def _clean(text: str | None) -> str:
    """Decode HTML entities, strip tags, collapse whitespace in a feed title.

    Feeds commonly double-encode (``world&#8217;s``) or wrap titles in CDATA with
    HTML markup, which the XML parser leaves as literal text. Unescape first so
    entity-encoded tags (``&lt;b&gt;``) become real tags the strip then removes,
    and numeric/named entities (``&#8217;`` → ’, ``&amp;`` → &) render properly.
    """
    if not text:
        return ""
    unescaped = html.unescape(text)
    return _WS.sub(" ", _HTML.sub(" ", unescaped)).strip()


def _parse_date(value: str | None) -> float | None:
    """Parse an RSS (RFC 822) or Atom (RFC 3339) date into epoch seconds."""
    if not value:
        return None
    text = value.strip()
    # RSS pubDate — RFC 822, e.g. "Sat, 27 Jun 2026 10:00:00 +0000".
    try:
        dt = parsedate_to_datetime(text)
        if dt is not None:
            return dt.timestamp()
    except (TypeError, ValueError, IndexError):
        pass
    # Atom — RFC 3339, e.g. "2026-06-27T10:00:00Z".
    try:
        from datetime import datetime

        return datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def _child_text(node: object, names: set[str]) -> str | None:
    """First non-empty text among ``node``'s direct children matching ``names``."""
    for child in list(node):  # type: ignore[call-overload]
        if _local(child.tag) in names and (child.text or "").strip():
            return child.text
    return None


def _link(node: object) -> str | None:
    """Resolve the entry link: RSS ``<link>`` text or Atom ``<link href=...>``."""
    for child in list(node):  # type: ignore[call-overload]
        if _local(child.tag) != "link":
            continue
        href = child.attrib.get("href")
        rel = child.attrib.get("rel", "alternate")
        if href and rel in ("alternate", ""):
            return href.strip()
        if (child.text or "").strip():
            return child.text.strip()
    return None


def _entry_to_item(node: object, feed: FeedSpec) -> NewsItem | None:
    """Map a single ``<item>``/``<entry>`` element to a :class:`NewsItem`."""
    title = _clean(_child_text(node, {"title"}))
    url = _link(node)
    if not title or not url or not url.lower().startswith(("http://", "https://")):
        return None
    published = _parse_date(
        _child_text(node, {"pubdate", "published", "updated", "date"})
    )
    return NewsItem(
        title=title[:280],
        url=url,
        source=feed.source,
        category=feed.category,
        published_at=published,
        lang=feed.lang,
    )


def parse_feed(payload: bytes, feed: FeedSpec, *, limit: int = 20) -> list[NewsItem]:
    """Parse RSS/Atom ``payload`` into up to ``limit`` items (best-effort).

    Returns an empty list on any parse failure rather than raising, so one bad
    feed degrades to "no items from this source" instead of breaking the ticker.
    """
    if not payload:
        return []
    try:
        root = DefusedET.fromstring(payload)
    except Exception:  # noqa: BLE001 — malformed/oversized XML → no items
        return []
    items: list[NewsItem] = []
    for node in root.iter():
        if _local(node.tag) not in ("item", "entry"):
            continue
        item = _entry_to_item(node, feed)
        if item is not None:
            items.append(item)
        if len(items) >= limit:
            break
    return items


__all__ = ["parse_feed"]
