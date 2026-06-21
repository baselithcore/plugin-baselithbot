"""Current-user surface for the SPA: the caller's mapped wiki permissions.

Identity is owned by the central ``auth`` plugin. This endpoint translates the
authenticated token into the wiki permission set (see
:mod:`llm_wiki.auth._core_bridge`) so the React app can gate affordances
client-side. The backend still enforces every permission independently on each
protected route — this is a convenience for the UI, not a security boundary.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from llm_wiki.auth.dependencies import require_user

router = APIRouter(prefix="/api/me", tags=["me"])


@router.get("/perms")
def my_permissions(user: dict[str, Any] = Depends(require_user)) -> dict[str, Any]:
    """Effective wiki permission set + role for the authenticated caller."""
    return {
        "user_id": user["id"],
        "email": user["email"],
        "display_name": user["display_name"],
        "role": user["role"],
        "is_admin": user["role"] == "admin",
        "perms": user["perms"],
        "roles": user["roles"],
    }


__all__ = ["router"]
