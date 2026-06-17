"""Auth plugin RBAC routers.

- ``rbac_admin_router`` (mounted at ``/admin/rbac``): role/permission
  management and the central per-plugin-tab access matrix.
- ``rbac_me_router`` (mounted at ``/auth/access``): self-service endpoints
  any plugin UI can use to discover the caller's permissions and tabs.
"""

from fastapi import APIRouter

from plugins.auth.rbac_router._groups import router as _groups_router
from plugins.auth.rbac_router._me import router as _me_router
from plugins.auth.rbac_router._roles import router as _roles_router
from plugins.auth.rbac_router._tabs import router as _tabs_router

rbac_admin_router = APIRouter(prefix="/admin/rbac", tags=["RBAC"])
rbac_admin_router.include_router(_roles_router)
rbac_admin_router.include_router(_groups_router)
rbac_admin_router.include_router(_tabs_router)

rbac_me_router = APIRouter(prefix="/auth/access", tags=["RBAC"])
rbac_me_router.include_router(_me_router)

__all__ = ["rbac_admin_router", "rbac_me_router"]
