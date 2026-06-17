"""
Admin / governance routes for BaselithMed.

Extracted from router.py to keep every file under the 500-LOC cap.
All logic is identical — this is a pure mechanical split.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from .security import require_clinical_validator


def create_admin_router(plugin_instance: Any) -> APIRouter:
    """Build the admin sub-router (retention, calibration, audit)."""

    router = APIRouter(prefix="", tags=["BaselithMed"])

    clinical_validator_dep = Depends(require_clinical_validator())

    @router.post(
        "/retention/purge",
        dependencies=[clinical_validator_dep],
    )
    async def purge_retention() -> dict[str, Any]:
        purge = getattr(plugin_instance, "purge_expired_sessions", None)
        if not callable(purge):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Retention policy unavailable.",
            )
        report = purge()
        return {
            "report": report.to_dict(),
            "retention_days": getattr(
                plugin_instance.retention_policy, "retention_days", None
            )
            if hasattr(plugin_instance, "retention_policy")
            else None,
        }

    @router.get(
        "/calibration/stats",
        dependencies=[clinical_validator_dep],
    )
    async def get_calibration_stats() -> dict[str, Any]:
        store = getattr(plugin_instance, "calibration_store", None)
        if store is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Calibration store unavailable.",
            )
        return store.report().to_dict()

    @router.get(
        "/audit/{session_id}",
        dependencies=[clinical_validator_dep],
    )
    async def get_audit(session_id: str) -> dict[str, Any]:
        ledger = getattr(plugin_instance, "audit_ledger", None)
        if ledger is None:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Audit ledger unavailable.",
            )
        entries = [e.to_dict() for e in ledger.entries(session_id=session_id)]
        return {
            "session_id": session_id,
            "entries": entries,
            "chain_valid": ledger.verify(),
        }

    return router
