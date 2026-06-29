"""Runtime per-plugin tenancy-mode override resolver.

A plugin declares its tenancy model in its manifest (``shared`` | ``personal``).
Operators can override that at runtime from the auth admin console; the override
lives in the auth persistence layer (:class:`PluginTenancyOverrideMixin`). This
module bridges that store into core: it registers a resolver via
``core.context.set_plugin_tenancy_resolver`` so every plugin's
``self.tenant_key()`` picks up the override automatically.

The resolver is on the hot path (consulted on each storage-scope resolution), so
it reads from a short-TTL in-memory snapshot of the whole override table — one
query refreshes every plugin's override at once. It degrades **safely**: any DB
error keeps the last good snapshot (and returns ``None`` → the declared manifest
mode wins), so an override-store outage never breaks or silently re-scopes a
plugin's storage. Idempotent install; the cache is invalidated on admin writes.
"""

from __future__ import annotations

import threading
import time
from typing import Optional

from core.context import set_plugin_tenancy_resolver
from core.observability.logging import get_logger

logger = get_logger(__name__)

_CACHE_TTL = 30.0  # seconds the override snapshot stays warm on the hot path

_INSTALLED = False
_INSTALL_LOCK = threading.Lock()

# Snapshot of the whole override table: {plugin_name: mode}. Replaced wholesale
# on a successful refresh; kept (stale) on failure so a transient DB blip never
# drops live overrides.
_snapshot: dict[str, str] = {}
_fetched_at: float = 0.0
_snapshot_lock = threading.Lock()


def _persistence() -> object | None:
    """The auth persistence singleton, or ``None`` when unavailable."""
    try:
        from plugins.auth.persistence import get_auth_persistence

        return get_auth_persistence()
    except Exception:  # noqa: BLE001 — DB-less deployments degrade gracefully
        return None


def _refresh_locked(now: float) -> None:
    """Reload the override snapshot from the DB (best-effort, keep stale on error)."""
    global _snapshot, _fetched_at
    p = _persistence()
    if p is None:
        _fetched_at = now  # avoid hammering a missing DB; declared mode wins
        return
    try:
        fresh = p.get_plugin_tenancy_overrides()  # type: ignore[attr-defined]
        _snapshot = dict(fresh)
        _fetched_at = now
    except Exception as exc:  # noqa: BLE001 — never break scoping on a DB hiccup
        logger.debug("tenancy override refresh failed: %s", exc)
        _fetched_at = now  # back off; serve the previous snapshot


def resolve_override(plugin_name: str) -> Optional[str]:
    """Return the override mode for a plugin, or ``None`` to inherit the manifest.

    Cheap and total: serves a TTL-cached snapshot and never raises. This is the
    callable handed to ``core.context.set_plugin_tenancy_resolver``.
    """
    now = time.time()
    with _snapshot_lock:
        if now - _fetched_at >= _CACHE_TTL:
            _refresh_locked(now)
        return _snapshot.get(plugin_name)


def invalidate_override_cache() -> None:
    """Force the next resolve to reload (call after an admin changes an override)."""
    global _fetched_at
    with _snapshot_lock:
        _fetched_at = 0.0


def install_plugin_tenancy_overrides() -> bool:
    """Register the override resolver into core (idempotent).

    Safe to call once at plugin activation. Returns ``True`` once installed.
    """
    global _INSTALLED
    if _INSTALLED:
        return True
    with _INSTALL_LOCK:
        if _INSTALLED:
            return True
        set_plugin_tenancy_resolver(resolve_override)
        _INSTALLED = True
        logger.info("Auth per-plugin tenancy overrides installed")
        return True


__all__ = [
    "install_plugin_tenancy_overrides",
    "invalidate_override_cache",
    "resolve_override",
]
