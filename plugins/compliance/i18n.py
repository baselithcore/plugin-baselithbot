"""Backend i18n for the compliance plugin (English default, Italian).

Resolves a locale from the request ``Accept-Language`` header and looks up
messages from per-locale JSON catalogs (``locales/{en,it}.json``). Used for any
user-facing text the API returns; the SPA does its own i18n client-side. Falls
back to ``en`` for an unknown locale or a missing key.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict

_LOCALES_DIR = Path(__file__).resolve().parent / "locales"
_SUPPORTED = ("en", "it")
_DEFAULT = "en"


@lru_cache(maxsize=None)
def _catalog(locale: str) -> Dict[str, str]:
    """Load and cache a locale catalog; empty dict if the file is missing."""
    path = _LOCALES_DIR / f"{locale}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — a missing catalog degrades to fallback
        return {}


def negotiate_locale(accept_language: str | None) -> str:
    """Pick the best supported locale from an ``Accept-Language`` header."""
    if not accept_language:
        return _DEFAULT
    for part in accept_language.split(","):
        tag = part.split(";")[0].strip().lower()
        primary = tag.split("-")[0]
        if primary in _SUPPORTED:
            return primary
    return _DEFAULT


def translate(key: str, locale: str = _DEFAULT, **params: Any) -> str:
    """Resolve ``key`` in ``locale`` (then ``en``), with ``{param}`` interpolation."""
    message = _catalog(locale).get(key) or _catalog(_DEFAULT).get(key) or key
    if params:
        try:
            return message.format(**params)
        except (KeyError, IndexError, ValueError):
            return message
    return message


__all__ = ["negotiate_locale", "translate"]
