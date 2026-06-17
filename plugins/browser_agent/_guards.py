"""SSRF guards and selector normalisation helpers for BrowserAgent.

Extracted from agent.py to keep that module under the 500-LOC cap.
Public API:
    assert_navigation_allowed(url)  — raises ValueError for blocked targets
    _normalize_selector(selector)   — translates jQuery :contains → Playwright
"""

from __future__ import annotations

import ipaddress
import os
import re
from urllib.parse import urlparse

_JQUERY_CONTAINS = re.compile(r":contains\(\s*['\"]([^'\"]+)['\"]\s*\)")

_ALLOWED_SCHEMES = frozenset({"http", "https"})
_BLOCKED_HOSTNAMES = frozenset({"localhost", "broadcasthost"})


def _hostname_is_blocked(hostname: str) -> bool:
    """Return True for hostnames that resolve to internal/loopback ranges."""
    if not hostname:
        return True
    lowered = hostname.lower().strip(".")
    if lowered in _BLOCKED_HOSTNAMES or lowered.endswith(".localhost"):
        return True
    try:
        addr = ipaddress.ip_address(lowered)
    except ValueError:
        return False
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def _ssrf_guard_disabled() -> bool:
    """Return True when ``BASELITH_BROWSER_ALLOW_INTERNAL`` is truthy."""
    raw = os.environ.get("BASELITH_BROWSER_ALLOW_INTERNAL", "").strip().lower()
    return raw in ("1", "true", "yes", "on")


def assert_navigation_allowed(url: str) -> None:
    """Raise ``ValueError`` when ``url`` targets an internal/loopback resource.

    Override with ``BASELITH_BROWSER_ALLOW_INTERNAL=true`` for trusted local use.
    """
    if _ssrf_guard_disabled():
        return
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in _ALLOWED_SCHEMES:
        raise ValueError(f"Refusing to navigate: scheme '{scheme}' not allowed")
    hostname = parsed.hostname or ""
    if _hostname_is_blocked(hostname):
        raise ValueError(
            f"Refusing to navigate: '{hostname}' resolves to a blocked range"
        )


def _normalize_selector(selector: str) -> str:
    """Translate jQuery-style ``:contains("X")`` to Playwright ``:has-text("X")``.

    Vision models frequently emit jQuery-flavored selectors that Playwright's
    query engine rejects. Rewriting here keeps the click/fill call sites free
    of model-specific quirks.
    """
    return _JQUERY_CONTAINS.sub(lambda m: f':has-text("{m.group(1)}")', selector)
