from fastapi import APIRouter

from .audit import router as audit_router
from .auth import router as auth_router
from .export import router as export_router
from .findings import router as findings_router
from .metrics import router as metrics_router
from .policies import router as policies_router
from .routes import router as core_router
from .summary import router as summary_router
from .system import router as system_router
from .workspace import router as workspace_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(core_router)
router.include_router(policies_router)
router.include_router(audit_router)
router.include_router(metrics_router)
router.include_router(export_router)
router.include_router(workspace_router)
router.include_router(findings_router)
router.include_router(summary_router)
router.include_router(system_router)

__all__ = ["router"]
