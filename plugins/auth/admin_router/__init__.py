"""
Auth Plugin Admin Router.

Admin-only endpoints for user management, sessions, and audit. Handlers are
split across sibling modules (user management vs. monitoring) to honour the
500 LOC cap; this package re-exports the combined ``admin_router``.
"""

from fastapi import APIRouter

from plugins.auth.admin_router._impersonation import router as _impersonation_router
from plugins.auth.admin_router._lifecycle import router as _lifecycle_router
from plugins.auth.admin_router._monitoring import router as _monitoring_router
from plugins.auth.admin_router._security import router as _security_router
from plugins.auth.admin_router._user_actions import router as _user_actions_router
from plugins.auth.admin_router._users import router as _users_router

admin_router = APIRouter(prefix="/admin", tags=["Admin"])
admin_router.include_router(_users_router)
admin_router.include_router(_user_actions_router)
admin_router.include_router(_impersonation_router)
admin_router.include_router(_lifecycle_router)
admin_router.include_router(_monitoring_router)
admin_router.include_router(_security_router)

__all__ = ["admin_router"]
