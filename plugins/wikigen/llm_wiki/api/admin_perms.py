"""Granular per-endpoint permission gating for the admin router.

The router-level dependency ``_require_admin_or_first_boot`` (in
:mod:`llm_wiki.api.admin`) handles the baseline admin gate (auth +
first-boot bypass + loopback). Endpoints layer
:func:`require_admin_perm` on top to enforce granular permissions
(``admin.scaffold`` / ``admin.tenant.manage`` / ``admin.runtime`` etc.).

Back-compat layers (in evaluation order):

1. ``POSTGRES_ENABLED`` false → bypass (setup mode).
2. ``count_users() == 0`` (first-boot) → bypass.
3. Legacy ``users.role == 'admin'`` column → bypass.
4. RBAC role ``superuser`` → bypass (has all perms by design).
5. Granular ``perm`` in user permission set → allow.
6. Otherwise → 403.

Living outside :mod:`admin` so the sub-routers (:mod:`admin_runtime`,
:mod:`admin_uploads`) can import the factory without creating a
circular dependency.
"""

from __future__ import annotations

import logging
from collections.abc import Callable

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)


def require_admin_perm(perm: str) -> Callable[[Request], None]:
    """Return a FastAPI dependency enforcing ``perm`` with admin fallbacks."""

    def _dep(request: Request) -> None:
        from llm_wiki import config as _cfg

        if not _cfg.POSTGRES_ENABLED:
            return
        try:
            from llm_wiki.db.users import count_users

            if count_users() == 0:
                return
        except Exception as exc:  # pragma: no cover — DB blip
            logger.debug("[admin.perm] count_users skipped: %s", exc)
            return
        from llm_wiki.auth.dependencies import _resolve_user

        user = _resolve_user(request)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Autenticazione richiesta.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if user.get("role") == "admin":
            return
        if "superuser" in (user.get("roles") or []):
            return
        if perm in (user.get("perms") or []):
            return
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permesso richiesto: {perm}.",
        )

    return _dep


__all__ = ["require_admin_perm"]
