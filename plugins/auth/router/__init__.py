"""
Auth Plugin FastAPI Router.

Provides authentication endpoints: login, logout, refresh, MFA. The handlers
are split across sibling modules (auth flow vs. account/MFA management) to
honour the 500 LOC cap; this package re-exports the combined ``router``.
"""

from fastapi import APIRouter

from plugins.auth.router._account_routes import router as _account_router
from plugins.auth.router._apikey_routes import router as _apikey_router
from plugins.auth.router._auth_routes import router as _auth_router
from plugins.auth.router._cost_routes import router as _cost_self_router
from plugins.auth.router._impersonation_routes import router as _impersonation_router
from plugins.auth.router._mfa_enroll_routes import router as _mfa_enroll_router
from plugins.auth.router._recovery_routes import router as _recovery_router
from plugins.auth.router._self_routes import router as _self_router
from plugins.auth.router._setup_routes import router as _setup_router
from plugins.auth.router._sso_admin_routes import router as _sso_admin_router
from plugins.auth.router._sso_routes import router as _sso_router
from plugins.auth.router._tenant_routes import router as _tenant_router
from plugins.auth.router._webauthn_routes import router as _webauthn_router

router = APIRouter(prefix="/auth", tags=["Authentication"])
router.include_router(_setup_router)
router.include_router(_auth_router)
router.include_router(_mfa_enroll_router)
router.include_router(_impersonation_router)
router.include_router(_account_router)
router.include_router(_recovery_router)
router.include_router(_webauthn_router)
router.include_router(_self_router)
router.include_router(_cost_self_router)
router.include_router(_tenant_router)
router.include_router(_apikey_router)
router.include_router(_sso_admin_router)
router.include_router(_sso_router)

__all__ = ["router"]
