"""Findings query endpoints."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel

from plugins.red_agent.agent import RedAgent
from plugins.red_agent.dependencies import get_red_agent, require_viewer
from plugins.red_agent.exporters import to_sigma_yaml
from plugins.red_agent.models import Finding

router = APIRouter(prefix="/findings", tags=["red-agent"])


class EvidenceChainEvent(BaseModel):
    id: int
    actor: str | None
    event: str
    payload: dict[str, Any]
    created_at: str | None


class FindingEvidence(BaseModel):
    """Replayable provenance bundle for a single finding.

    Combines the finding row, its parent scan id, and the ordered
    audit-log chain that produced it. Lets reviewers replay every
    decision the agent took without trusting any single layer in
    isolation.
    """

    finding: Finding
    scan_id: str
    chain: list[EvidenceChainEvent]


@router.get("", dependencies=[require_viewer()])
async def list_findings(
    agent: RedAgent = Depends(get_red_agent),
    severity: str | None = None,
    cwe: str | None = None,
    scanner: str | None = None,
    target: str | None = None,
    target_id: UUID | None = None,
    state: str | None = None,
    assignee: str | None = None,
    overdue: bool = False,
    limit: int = 100,
    offset: int = 0,
) -> list[Finding]:
    return await agent.persistence.list_findings(
        severity=severity,
        cwe=cwe,
        scanner=scanner,
        target=target,
        target_id=target_id,
        state=state,
        assignee=assignee,
        overdue=overdue,
        limit=limit,
        offset=offset,
    )


@router.get("/by-scan/{scan_id}", dependencies=[require_viewer()])
async def list_by_scan(
    scan_id: UUID,
    agent: RedAgent = Depends(get_red_agent),
) -> list[Finding]:
    result = await agent.get_scan(scan_id)
    if result is None:
        raise HTTPException(status_code=404, detail="scan not found")
    return result.findings


@router.get("/{finding_id}/evidence", dependencies=[require_viewer()])
async def get_finding_evidence(
    finding_id: UUID,
    agent: RedAgent = Depends(get_red_agent),
    chain_limit: int = 500,
) -> FindingEvidence:
    """Return the evidence ledger for a single finding.

    The bundle is a snapshot of the immutable audit chain plus the
    finding row itself, sufficient to reconstruct what the agent did
    without re-running anything.
    """
    resolved = await agent.persistence.get_finding(finding_id)
    if resolved is None:
        raise HTTPException(404, "finding not found")
    finding, scan_id = resolved
    rows = await agent.persistence.list_scan_audit(scan_id, limit=chain_limit)
    chain = [
        EvidenceChainEvent(
            id=r["id"],
            actor=r.get("actor"),
            event=r["event"],
            payload=r.get("payload") or {},
            created_at=r["created_at"].isoformat() if r.get("created_at") else None,
        )
        for r in rows
    ]
    return FindingEvidence(finding=finding, scan_id=str(scan_id), chain=chain)


@router.get(
    "/{finding_id}/sigma",
    dependencies=[require_viewer()],
    response_class=PlainTextResponse,
)
async def get_finding_sigma(
    finding_id: UUID,
    agent: RedAgent = Depends(get_red_agent),
    keyword: list[str] | None = Query(default=None),
    tag: list[str] | None = Query(default=None),
) -> PlainTextResponse:
    """Render the finding's detection guidance as a Sigma rule (YAML).

    Operators can override the auto-extracted ``keywords`` selector
    via repeated ``?keyword=`` query params and append custom ``?tag=``
    entries before download. Returns 404 when the finding is unknown,
    409 when the finding has no detection_guidance to render.
    """
    resolved = await agent.persistence.get_finding(finding_id)
    if resolved is None:
        raise HTTPException(404, "finding not found")
    finding, _ = resolved
    yaml_body = to_sigma_yaml(
        finding,
        keyword_override=keyword if keyword else None,
        extra_tags=tag if tag else None,
    )
    if yaml_body is None:
        raise HTTPException(409, "finding has no detection_guidance to convert")
    return PlainTextResponse(
        content=yaml_body,
        media_type="application/yaml",
        headers={
            "Content-Disposition": (
                f'attachment; filename="baselithcore-{finding.id}.sigma.yml"'
            )
        },
    )
