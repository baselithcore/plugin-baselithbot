"""Configuration views and runtime policy editing for the Red Agent plugin.

GET returns the *effective* policy (env defaults overlaid with persisted
operator overrides). PUT accepts a partial update from the UI, validates
it, persists the override, applies it to the live RedAgentConfig and
records an audit entry. Secrets and process-bound knobs (host/port,
sandbox provider) remain env-only.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from core.di.container import ServiceRegistry
from plugins.red_agent.audit import AuditLogger
from plugins.red_agent.config import RedAgentConfig
from plugins.red_agent.dependencies import (
    get_red_agent_config,
    require_security_operator,
    require_viewer,
)
from plugins.red_agent.persistence import PolicyStore
from plugins.red_agent.policy import (
    PolicyUpdate,
    apply_overrides,
    overrides_from_update,
    snapshot,
)

router = APIRouter(prefix="/settings", tags=["red-agent"])


def _actor(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if user is not None:
        for attr in ("username", "email", "id"):
            v = getattr(user, attr, None)
            if v:
                return str(v)
    return request.headers.get("X-Operator", "ui-operator")


@router.get("/scope", dependencies=[require_viewer()])
async def get_scope(
    config: RedAgentConfig = Depends(get_red_agent_config),
) -> dict[str, object]:
    return snapshot(config)


@router.put("/scope", dependencies=[require_security_operator()])
async def update_scope(
    update: PolicyUpdate,
    request: Request,
    config: RedAgentConfig = Depends(get_red_agent_config),
) -> dict[str, object]:
    new_overrides = overrides_from_update(update)

    store = (
        ServiceRegistry.get(PolicyStore) if ServiceRegistry.has(PolicyStore) else None
    )
    merged: dict[str, object] = {}
    if store is not None and store.available:
        merged = dict(await store.load())
    merged.update(new_overrides)

    apply_overrides(config, new_overrides)

    actor = _actor(request)
    if store is not None and store.available:
        await store.save(merged, actor=actor)

    if ServiceRegistry.has(AuditLogger):
        audit = ServiceRegistry.get(AuditLogger)
        await audit.record(
            scan_id=None,
            actor=actor,
            event="policy.updated",
            payload={"changed": sorted(new_overrides.keys())},
        )

    return snapshot(config)
