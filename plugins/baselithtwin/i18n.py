"""Backend internationalization for user-facing API text.

Resolves a locale from the request ``Accept-Language`` header (or an explicit
override) and looks up messages from per-locale JSON catalogs under
``locales/``. English (``en``) is the default and fallback; Italian (``it``)
ships complete alongside it. Missing keys degrade to the key id rather than
raising, so a forgotten translation never 500s a response.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_LOCALES_DIR = Path(__file__).resolve().parent / "locales"
DEFAULT_LOCALE = "en"
SUPPORTED_LOCALES = ("en", "it")


@lru_cache(maxsize=8)
def _load_catalog(locale: str) -> dict[str, str]:
    """Load and cache a locale catalog, falling back to an empty dict."""
    path = _LOCALES_DIR / f"{locale}.json"
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return {str(k): str(v) for k, v in data.items()} if isinstance(data, dict) else {}


def negotiate_locale(accept_language: str | None) -> str:
    """Pick the best supported locale from an ``Accept-Language`` header.

    Parses the comma-separated, ``;q=``-weighted header and returns the first
    supported primary tag (e.g. ``it-IT`` matches ``it``). Defaults to ``en``.
    """
    if not accept_language:
        return DEFAULT_LOCALE
    ranked: list[tuple[float, str]] = []
    for part in accept_language.split(","):
        token = part.strip()
        if not token:
            continue
        lang, _, params = token.partition(";")
        quality = 1.0
        if params.startswith("q="):
            try:
                quality = float(params[2:])
            except ValueError:
                quality = 0.0
        primary = lang.strip().lower().split("-")[0]
        if primary in SUPPORTED_LOCALES:
            ranked.append((quality, primary))
    if not ranked:
        return DEFAULT_LOCALE
    ranked.sort(key=lambda item: item[0], reverse=True)
    return ranked[0][1]


def translate(key: str, locale: str, **params: object) -> str:
    """Resolve ``key`` for ``locale`` with ``{name}`` interpolation.

    Falls back to the default-locale catalog, then to the raw key. Interpolation
    is best-effort: a missing placeholder leaves the template untouched.
    """
    catalog = _load_catalog(locale if locale in SUPPORTED_LOCALES else DEFAULT_LOCALE)
    template = catalog.get(key) or _load_catalog(DEFAULT_LOCALE).get(key) or key
    if not params:
        return template
    try:
        return template.format(**params)
    except (KeyError, IndexError, ValueError):
        return template


__all__ = ["translate", "negotiate_locale", "DEFAULT_LOCALE", "SUPPORTED_LOCALES"]
