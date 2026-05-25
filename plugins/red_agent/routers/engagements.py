"""Engagement / campaign endpoints for the Red Agent."""

from __future__ import annotations

import io
import zipfile
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from core.context import get_current_tenant_id
from core.di.container import ServiceRegistry
from plugins.red_agent.agent import RedAgent
from plugins.red_agent.audit import AuditLogger
from plugins.red_agent.dependencies import (
    get_red_agent,
    require_security_operator,
    require_viewer,
)
from plugins.red_agent.exporters import to_sigma_yaml
from plugins.red_agent.models import (
    EngagementCreate,
    EngagementRecord,
    EngagementStatus,
    EngagementUpdate,
)
from plugins.red_agent.persistence import EngagementPersistence

router = APIRouter(prefix="/engagements", tags=["red-agent", "engagements"])


def _store() -> EngagementPersistence:
    if not ServiceRegistry.has(EngagementPersistence):
        raise HTTPException(503, "Engagement store not initialized")
    store = ServiceRegistry.get(EngagementPersistence)
    if store is None or not store.available:
        raise HTTPException(503, "Engagement store unavailable")
    return store


def _actor(request: Request) -> str:
    user = getattr(request.state, "user", None)
    if user is not None:
        for attr in ("username", "email", "id"):
            value = getattr(user, attr, None)
            if value:
                return str(value)
    return request.headers.get("X-Operator", "api-caller")


def _tenant() -> str | None:
    try:
        return get_current_tenant_id()
    except Exception:  # noqa: BLE001
        return None


async def _audit(actor: str, event: str, payload: dict[str, object]) -> None:
    if not ServiceRegistry.has(AuditLogger):
        return
    audit = ServiceRegistry.get(AuditLogger)
    await audit.record(scan_id=None, actor=actor, event=event, payload=payload)


@router.get("", dependencies=[require_viewer()])
async def list_engagements(
    status_filter: EngagementStatus | None = None,
    include_archived: bool = False,
    limit: int = 50,
    offset: int = 0,
    store: EngagementPersistence = Depends(_store),
) -> list[EngagementRecord]:
    return await store.list(
        tenant_id=_tenant(),
        status=status_filter,
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[require_security_operator()],
)
async def create_engagement(
    body: EngagementCreate,
    request: Request,
    store: EngagementPersistence = Depends(_store),
) -> EngagementRecord:
    actor = _actor(request)
    record = await store.from_create(body, tenant_id=_tenant(), created_by=actor)
    await _audit(
        actor,
        "engagement.created",
        {"engagement_id": str(record.id), "name": record.name},
    )
    return record


@router.get("/{engagement_id}", dependencies=[require_viewer()])
async def get_engagement(
    engagement_id: UUID,
    store: EngagementPersistence = Depends(_store),
) -> EngagementRecord:
    record = await store.get(engagement_id)
    if record is None:
        raise HTTPException(404, "engagement not found")
    return record


@router.patch("/{engagement_id}", dependencies=[require_security_operator()])
async def update_engagement(
    engagement_id: UUID,
    body: EngagementUpdate,
    request: Request,
    store: EngagementPersistence = Depends(_store),
) -> EngagementRecord:
    record = await store.update(engagement_id, body)
    if record is None:
        raise HTTPException(404, "engagement not found")
    await _audit(
        _actor(request),
        "engagement.updated",
        {"engagement_id": str(record.id), "status": record.status.value},
    )
    return record


@router.delete(
    "/{engagement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    response_model=None,
    dependencies=[require_security_operator()],
)
async def archive_engagement(
    engagement_id: UUID,
    request: Request,
    store: EngagementPersistence = Depends(_store),
) -> None:
    archived = await store.archive(engagement_id)
    if not archived:
        raise HTTPException(404, "engagement not found")
    await _audit(
        _actor(request),
        "engagement.archived",
        {"engagement_id": str(engagement_id)},
    )


@router.get("/{engagement_id}/sigma.zip", dependencies=[require_viewer()])
async def export_engagement_sigma_bundle(
    engagement_id: UUID,
    store: EngagementPersistence = Depends(_store),
    agent: RedAgent = Depends(get_red_agent),
    limit: int = 200,
) -> Response:
    """Bundle Sigma rules for every finding produced by an engagement.

    Walks the scans linked to ``engagement_id`` (newest ``limit``),
    pulls each scan's findings, and emits one Sigma YAML per finding
    that carries ``detection_guidance``. Returns 404 when the
    engagement is unknown, 409 when no eligible findings exist.
    """
    engagement = await store.get(engagement_id)
    if engagement is None:
        raise HTTPException(404, "engagement not found")

    rows = await agent.persistence.list_scans(engagement_id=engagement_id, limit=limit)
    buf = io.BytesIO()
    manifest_lines = [
        f"engagement_id: {engagement_id}",
        f"engagement_name: {engagement.name}",
        "",
    ]
    written = 0
    seen_findings: set[str] = set()
    with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for row in rows:
            scan_id_raw = row.get("id")
            if scan_id_raw is None:
                continue
            scan_uuid = (
                scan_id_raw if isinstance(scan_id_raw, UUID) else UUID(str(scan_id_raw))
            )
            scan = await agent.persistence.get_scan(scan_uuid)
            if scan is None:
                continue
            scan_dir = f"scan-{scan_uuid}"
            for finding in scan.findings:
                fid = str(finding.id)
                if fid in seen_findings:
                    continue
                yaml_body = to_sigma_yaml(finding)
                if yaml_body is None:
                    continue
                zf.writestr(f"{scan_dir}/{fid}.sigma.yml", yaml_body)
                manifest_lines.append(
                    f"- scan {scan_uuid}  finding {fid}  "
                    f"[{finding.severity.value}]  {finding.title}"
                )
                seen_findings.add(fid)
                written += 1
        if written == 0:
            raise HTTPException(
                status_code=409,
                detail="no findings in this engagement have detection_guidance",
            )
        zf.writestr("MANIFEST.txt", "\n".join(manifest_lines) + "\n")

    return Response(
        content=buf.getvalue(),
        media_type="application/zip",
        headers={
            "Content-Disposition": (
                f'attachment; filename="baselithcore-engagement-'
                f'{engagement_id}.sigma.zip"'
            )
        },
    )
