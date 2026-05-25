"""Target-as-project CRUD + posture endpoints.

Targets are the persistent unit of work in the Red Agent: every web app,
host, cloud account or network range an operator wants to monitor lives
here. Scans become "runs" against a target, inheriting the target's
profile (default scanners, intensity, scope overrides, schedule).
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from core.context import get_current_tenant_id
from core.di.container import ServiceRegistry
from plugins.red_agent.agent import RedAgent
from plugins.red_agent.dependencies import (
    get_red_agent,
    require_security_operator,
    require_viewer,
)
from plugins.red_agent.guardrails import GuardrailViolation
from plugins.red_agent.models import (
    ScanIntensity,
    ScanRequest,
    Target,
    TargetCreate,
    TargetKind,
    TargetRecord,
    TargetType,
    TargetUpdate,
)
from plugins.red_agent.persistence import EngagementPersistence, TargetPersistence


def _audit() -> Any:
    """Resolve the AuditLogger lazily so import-time wiring stays lean."""
    from plugins.red_agent.audit import AuditLogger

    return ServiceRegistry.get(AuditLogger)


router = APIRouter(prefix="/targets", tags=["red-agent"])


# ──────────────────────────────────────────────────────────────────────
# Helpers


def _store() -> TargetPersistence:
    store = ServiceRegistry.get(TargetPersistence)
    if store is None or not store.available:
        raise HTTPException(503, "TargetPersistence not available")
    return store


def _infer_target_type(kind: TargetKind, value: str) -> TargetType:
    """Map a high-level :class:`TargetKind` + raw value to the legacy ``TargetType``.

    Kept intentionally permissive — guardrails do the real validation downstream.
    """
    if kind == TargetKind.WEB:
        return (
            TargetType.URL
            if value.startswith(("http://", "https://"))
            else TargetType.HOSTNAME
        )
    if kind == TargetKind.NETWORK:
        return TargetType.CIDR if "/" in value else TargetType.IP
    if kind == TargetKind.CLOUD:
        return TargetType.HOSTNAME
    if kind == TargetKind.REPO:
        return TargetType.REPO
    if kind == TargetKind.BINARY:
        return TargetType.BINARY
    if kind == TargetKind.HOST and value.startswith("system:"):
        return TargetType.SYSTEM
    return TargetType.HOSTNAME


def _derive_target_scope(kind: TargetKind, value: str) -> list[str]:
    """Pull a scope token out of a target value so the catalog target is
    treated as in-scope by guardrails without needing the global
    ``scope_allowlist`` to be populated.

    Returns hostnames / IPs / CIDRs that ``TargetGuardrails._in_scope``
    can match against. Cloud / repo / binary targets have no network
    host, so an empty list is returned and the caller falls through to
    whatever else is configured.
    """
    if not value:
        return []
    if kind == TargetKind.WEB:
        if value.startswith(("http://", "https://")):
            from urllib.parse import urlparse

            host = urlparse(value).hostname
            return [host] if host else []
        return [value]
    if kind == TargetKind.NETWORK:
        return [value]
    if kind == TargetKind.HOST:
        # ``agent:<uuid>`` references a daemon, ``system:local`` refers
        # to the in-process self-posture audit — neither has a network
        # host that ``_in_scope`` can match against.
        if value.startswith(("agent:", "system:")):
            return []
        return [value]
    return []


# ──────────────────────────────────────────────────────────────────────
# Read endpoints


@router.get("", dependencies=[require_viewer()])
async def list_targets(
    kind: str | None = None,
    environment: str | None = None,
    include_archived: bool = False,
    limit: int = 200,
    offset: int = 0,
) -> list[TargetRecord]:
    store = _store()
    return await store.list(
        tenant_id=get_current_tenant_id(),
        kind=TargetKind(kind) if kind else None,
        environment=environment,
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )


@router.get("/{target_id}", dependencies=[require_viewer()])
async def get_target(target_id: UUID) -> TargetRecord:
    store = _store()
    record = await store.get(target_id)
    if record is None:
        raise HTTPException(404, "target not found")
    return record


@router.get("/{target_id}/posture", dependencies=[require_viewer()])
async def get_posture(target_id: UUID) -> dict[str, Any]:
    store = _store()
    if await store.get(target_id) is None:
        raise HTTPException(404, "target not found")
    return await store.posture(target_id)


@router.get("/{target_id}/scans", dependencies=[require_viewer()])
async def list_target_scans(
    target_id: UUID,
    agent: RedAgent = Depends(get_red_agent),
    limit: int = 100,
    offset: int = 0,
) -> list[dict[str, object]]:
    rows = await agent.persistence.list_scans(
        target_id=target_id, limit=limit, offset=offset
    )
    for r in rows:
        r["id"] = str(r["id"])
        if r.get("target_id"):
            r["target_id"] = str(r["target_id"])
    return rows


@router.get("/{target_id}/activity", dependencies=[require_viewer()])
async def list_target_activity(
    target_id: UUID,
    limit: int = 100,
) -> list[dict[str, Any]]:
    store = _store()
    if await store.get(target_id) is None:
        raise HTTPException(404, "target not found")
    return await store.list_activity(target_id, limit=limit)


@router.get("/{target_id}/diff", dependencies=[require_viewer()])
async def diff_runs(
    target_id: UUID,
    baseline: UUID,
    latest: UUID,
    agent: RedAgent = Depends(get_red_agent),
) -> dict[str, Any]:
    """Diff two scans against the same target. Both scans must reference ``target_id``."""
    base = await agent.get_scan(baseline)
    head = await agent.get_scan(latest)
    if base is None or head is None:
        raise HTTPException(404, "scan not found")
    if base.target_id != target_id or head.target_id != target_id:
        raise HTTPException(400, "scans do not belong to target")
    store = _store()
    return await store.diff_runs(baseline, latest)


# ──────────────────────────────────────────────────────────────────────
# Mutating endpoints


@router.post("", status_code=201, dependencies=[require_security_operator()])
async def create_target(body: TargetCreate) -> TargetRecord:
    store = _store()
    return await store.create(
        body, tenant_id=get_current_tenant_id(), created_by="api-caller"
    )


@router.patch("/{target_id}", dependencies=[require_security_operator()])
async def update_target(target_id: UUID, body: TargetUpdate) -> TargetRecord:
    store = _store()
    record = await store.update(target_id, body, actor="api-caller")
    if record is None:
        raise HTTPException(404, "target not found")
    return record


class TargetScanRequest(BaseModel):
    """Trigger a scan against an existing target.

    Optional overrides take precedence over the target's stored profile.
    Useful for one-off intrusive runs without mutating the default profile.
    """

    scanners: list[str] | None = None
    engagement_id: UUID | None = None
    intensity: ScanIntensity | None = None
    notes: str | None = None


@router.post(
    "/{target_id}/scans",
    status_code=202,
    dependencies=[require_security_operator()],
)
async def launch_target_scan(
    target_id: UUID,
    body: TargetScanRequest,
    agent: RedAgent = Depends(get_red_agent),
) -> dict[str, str]:
    store = _store()
    record = await store.get(target_id)
    if record is None:
        raise HTTPException(404, "target not found")
    if record.archived_at is not None:
        raise HTTPException(409, "target is archived")
    if body.engagement_id is not None:
        engagement_store = (
            ServiceRegistry.get(EngagementPersistence)
            if ServiceRegistry.has(EngagementPersistence)
            else None
        )
        if (
            engagement_store is None
            or await engagement_store.get(body.engagement_id) is None
        ):
            raise HTTPException(404, "engagement not found")

    profile = record.profile or {}
    scanners = body.scanners or list(profile.get("scanners") or ["nmap", "nuclei"])
    intensity = body.intensity or ScanIntensity(profile.get("intensity") or "passive")
    target_type = _infer_target_type(record.kind, record.value)
    overrides = record.scope_overrides or {}
    target_metadata: dict[str, Any] = {}
    if overrides.get("allow_internal"):
        target_metadata["allow_internal"] = True
    # The catalog target is, by definition, in scope: an operator added
    # it on purpose. We inject its own host as extra_scope so guardrails
    # don't reject the scan with OUT_OF_SCOPE when the deployment has not
    # populated the global ``scope_allowlist``. Operator-managed extra
    # scope tokens from ``scope_overrides.extra_scope`` are merged in.
    auto_scope = _derive_target_scope(record.kind, record.value)
    declared_scope = (
        overrides.get("scope_allowlist") or overrides.get("extra_scope") or []
    )
    merged: list[str] = []
    if isinstance(declared_scope, list):
        merged.extend(str(x) for x in declared_scope if x)
    merged.extend(auto_scope)
    if merged:
        target_metadata["extra_scope"] = list(dict.fromkeys(merged))

    request = ScanRequest(
        target=Target(type=target_type, value=record.value, metadata=target_metadata),
        target_id=record.id,
        engagement_id=body.engagement_id,
        scanners=scanners,
        intensity=intensity,
        requested_by="api-caller",
        notes=body.notes,
        tenant_id=get_current_tenant_id(),
    )
    try:
        scan_id = await agent.submit_scan(request)
    except GuardrailViolation as e:
        raise HTTPException(400, detail={"code": e.code, "message": e.message})
    return {"scan_id": str(scan_id), "target_id": str(target_id)}


@router.delete(
    "/{target_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
    dependencies=[require_security_operator()],
)
async def delete_target(
    target_id: UUID,
    hard: bool = False,
    purge_runs: bool = False,
) -> None:
    """Soft- or hard-delete a target.

    Default behaviour is **soft** — the target is archived (``archived_at``
    set) and disappears from the active list while history is preserved.
    Pass ``?hard=true`` to permanently drop the row. Hard-delete is
    refused when scans still reference the target unless
    ``purge_runs=true`` is also supplied, which deletes those scans
    (and, by FK cascade, their findings) first.
    """
    store = _store()
    record = await store.get(target_id)
    if record is None:
        raise HTTPException(404, "target not found")

    audit = _audit()

    if not hard:
        if record.archived_at is not None:
            return
        ok = await store.archive(target_id)
        if not ok:
            raise HTTPException(404, "target not found")
        if audit is not None:
            await audit.record(
                scan_id=None,
                actor="api-caller",
                event="target.archived",
                payload={"target_id": str(target_id), "name": record.name},
            )
        return

    if not purge_runs and await store.has_runs(target_id):
        raise HTTPException(
            status_code=409,
            detail=(
                "target has scan history — pass purge_runs=true to drop"
                " scans and findings, or DELETE without hard=true to archive"
            ),
        )
    deleted = await store.hard_delete(target_id, purge_runs=purge_runs)
    if not deleted:
        raise HTTPException(404, "target not found")
    if audit is not None:
        await audit.record(
            scan_id=None,
            actor="api-caller",
            event="target.deleted",
            payload={
                "target_id": str(target_id),
                "name": record.name,
                "purged_runs": purge_runs,
            },
        )
