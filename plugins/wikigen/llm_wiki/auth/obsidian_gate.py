"""Per-user half of the Obsidian two-key gate.

Single source of truth used by ``/api/branding`` (``user_can_open``)
and ``/api/wiki/page/{id}`` (``obsidian_uri``). Keeping the logic in one
place ensures the two surfaces never drift — if a future deploy mode
changes how anonymous callers are treated (e.g. opt-in auth without
Postgres), both surfaces flip together.
"""

from __future__ import annotations

from fastapi import Request

from llm_wiki import config
from llm_wiki.auth.permissions import Permission, has_permission


def user_can_open_obsidian(request: Request) -> bool:
    """True if the caller holds ``obsidian.open``.

    Fail-open in setup mode (no Postgres = no auth backend, marker is
    the only gate). Fail-closed when auth resolution itself raises —
    a transient DB outage must not leak the URI to anonymous probes.
    """
    if not config.POSTGRES_ENABLED:
        return True
    try:
        from llm_wiki.auth.dependencies import _resolve_user

        user = _resolve_user(request)
    except Exception:
        return False
    return has_permission(user, Permission.OBSIDIAN_OPEN)


__all__ = ["user_can_open_obsidian"]
