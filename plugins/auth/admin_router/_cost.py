"""Admin endpoints for LLM cost governance.

Set the org-wide policy (default monthly cap + warn threshold + enforcement),
per-user and per-group cap overrides, view per-user month-to-date spend, and
reset a user's usage. All admin-gated and audited. Cap writes invalidate the
tracker's in-memory budget cache so enforcement reflects the change promptly.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, Request

from core.auth import AuthUser
from core.observability.logging import get_logger
from plugins.auth.admin_router._helpers import get_client_ip
from plugins.auth.audit import AuditAction
from plugins.auth.cost import (
    AdminUsageView,
    CapUpdate,
    CostPolicyUpdate,
    CostPolicyView,
    UserUsageRow,
    compute_status,
    invalidate_cache,
    micros_to_usd,
    usd_to_micros,
)
from plugins.auth.dependencies import (
    get_audit_logger_dep,
    get_auth_persistence_dep,
    require_admin,
)
from plugins.auth.persistence import AuthPersistence

logger = get_logger(__name__)

router = APIRouter(prefix="/cost", tags=["Admin"])


@router.get("/policy", response_model=CostPolicyView)
async def get_policy(
    _: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
) -> CostPolicyView:
    """Read the org-wide default cost policy."""
    p = persistence.get_cost_policy()
    return CostPolicyView(
        monthly_cap_usd=micros_to_usd(p.get("monthly_cap_micros")),
        warn_threshold_pct=int(p.get("warn_threshold_pct", 80)),
        enforce=bool(p.get("enforce", True)),
    )


@router.put("/policy", response_model=CostPolicyView)
async def set_policy(
    body: CostPolicyUpdate,
    request: Request,
    admin: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    audit=Depends(get_audit_logger_dep),
) -> CostPolicyView:
    """Set the org-wide default cap, warn threshold, and enforcement toggle."""
    persistence.set_cost_policy(
        monthly_cap_micros=usd_to_micros(body.monthly_cap_usd),
        warn_threshold_pct=body.warn_threshold_pct,
        enforce=body.enforce,
    )
    invalidate_cache()  # global change affects everyone
    audit.log(
        action=AuditAction.COST_POLICY_CHANGED,
        actor_id=admin.user_id,
        target_id="cost.policy",
        details={
            "monthly_cap_usd": body.monthly_cap_usd,
            "warn_threshold_pct": body.warn_threshold_pct,
            "enforce": body.enforce,
        },
        ip_address=get_client_ip(request),
    )
    return CostPolicyView(
        monthly_cap_usd=body.monthly_cap_usd,
        warn_threshold_pct=body.warn_threshold_pct,
        enforce=body.enforce,
    )


@router.patch("/users/{user_id}/cap")
async def set_user_cap(
    user_id: str,
    body: CapUpdate,
    request: Request,
    admin: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    audit=Depends(get_audit_logger_dep),
) -> dict[str, object]:
    """Set (or clear, with ``null``) a user's monthly cap override."""
    persistence.set_user_cap(user_id, usd_to_micros(body.monthly_cap_usd))
    invalidate_cache(user_id)
    audit.log(
        action=AuditAction.COST_USER_CAP_CHANGED,
        actor_id=admin.user_id,
        target_id=user_id,
        details={"monthly_cap_usd": body.monthly_cap_usd},
        ip_address=get_client_ip(request),
    )
    return {"ok": True, "user_id": user_id, "monthly_cap_usd": body.monthly_cap_usd}


@router.patch("/groups/{group_id}/cap")
async def set_group_cap(
    group_id: str,
    body: CapUpdate,
    request: Request,
    admin: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    audit=Depends(get_audit_logger_dep),
) -> dict[str, object]:
    """Set (or clear) a group's monthly cap (applies to its members)."""
    persistence.set_group_cap(group_id, usd_to_micros(body.monthly_cap_usd))
    invalidate_cache()  # group membership is many → clear all
    audit.log(
        action=AuditAction.COST_GROUP_CAP_CHANGED,
        actor_id=admin.user_id,
        target_id=group_id,
        details={"monthly_cap_usd": body.monthly_cap_usd},
        ip_address=get_client_ip(request),
    )
    return {"ok": True, "group_id": group_id, "monthly_cap_usd": body.monthly_cap_usd}


@router.post("/users/{user_id}/reset")
async def reset_user_usage(
    user_id: str,
    request: Request,
    admin: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
    audit=Depends(get_audit_logger_dep),
) -> dict[str, object]:
    """Zero a user's current-month usage (admin override)."""
    persistence.reset_user_usage(user_id)
    invalidate_cache(user_id)
    audit.log(
        action=AuditAction.COST_USAGE_RESET,
        actor_id=admin.user_id,
        target_id=user_id,
        ip_address=get_client_ip(request),
    )
    return {"ok": True, "user_id": user_id}


@router.get("/usage", response_model=AdminUsageView)
async def list_usage(
    _: AuthUser = Depends(require_admin()),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
) -> AdminUsageView:
    """Per-user month-to-date spend + effective cap (admin overview)."""
    policy = persistence.get_cost_policy()
    warn = int(policy.get("warn_threshold_pct", 80))
    rows: list[UserUsageRow] = []
    for r in persistence.all_usage():
        spend = int(r.get("spend_micros") or 0)
        cap = r.get("cap_micros")
        status, pct = compute_status(spend, cap, warn)
        rows.append(
            UserUsageRow(
                user_id=str(r["user_id"]),
                email=r.get("email"),
                username=r.get("username"),
                spend_usd=micros_to_usd(spend) or 0.0,
                request_count=int(r.get("request_count") or 0),
                cap_usd=micros_to_usd(cap),
                user_cap_usd=micros_to_usd(r.get("user_cap_micros")),
                percent_used=pct,
                status=status,
            )
        )
    return AdminUsageView(
        period=date.today().replace(day=1).isoformat(),
        warn_threshold_pct=warn,
        rows=rows,
    )


__all__ = ["router"]
