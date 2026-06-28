"""Self-service LLM usage for the signed-in user.

``GET /me/llm-usage`` returns the caller's own month-to-date spend against their
effective monthly cap — feeding the account "Usage" panel (progress bar + warn
banner). Authenticated but not admin-gated: a user always sees their own usage.
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends

from core.auth import AuthUser
from plugins.auth.cost import MyUsageView, compute_status, micros_to_usd
from plugins.auth.dependencies import get_auth_persistence_dep, get_current_active_user
from plugins.auth.persistence import AuthPersistence

router = APIRouter(prefix="/me")


@router.get("/llm-usage", response_model=MyUsageView)
async def my_llm_usage(
    user: AuthUser = Depends(get_current_active_user),
    persistence: AuthPersistence = Depends(get_auth_persistence_dep),
) -> MyUsageView:
    """The current user's monthly LLM spend, cap, and status."""
    policy = persistence.get_cost_policy()
    warn = int(policy.get("warn_threshold_pct", 80))
    enforce = bool(policy.get("enforce", True))
    cap = persistence.effective_cap_micros(user.user_id)
    spend = persistence.monthly_spend_micros(user.user_id)
    status, pct = compute_status(spend, cap, warn)
    return MyUsageView(
        period=date.today().replace(day=1).isoformat(),
        spend_usd=micros_to_usd(spend) or 0.0,
        cap_usd=micros_to_usd(cap),
        percent_used=pct,
        status=status,
        warn_threshold_pct=warn,
        enforce=enforce,
    )


__all__ = ["router"]
