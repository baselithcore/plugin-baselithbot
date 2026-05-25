"""Read-only playbook catalogue endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from plugins.red_agent.dependencies import require_viewer
from plugins.red_agent.models import ScanIntensity, TargetKind
from plugins.red_agent.playbooks import Playbook, PlaybookCatalogue, default_catalogue

router = APIRouter(prefix="/playbooks", tags=["red-agent", "playbooks"])

_CATALOGUE: PlaybookCatalogue | None = None


def _get_catalogue() -> PlaybookCatalogue:
    global _CATALOGUE
    if _CATALOGUE is None:
        _CATALOGUE = default_catalogue()
    return _CATALOGUE


@router.get("", dependencies=[require_viewer()])
async def list_playbooks(
    target_kind: TargetKind | None = None,
    max_intensity: ScanIntensity | None = None,
    catalogue: PlaybookCatalogue = Depends(_get_catalogue),
) -> list[Playbook]:
    return catalogue.filter_for(target_kind=target_kind, max_intensity=max_intensity)


@router.get("/{playbook_id}", dependencies=[require_viewer()])
async def get_playbook(
    playbook_id: str,
    catalogue: PlaybookCatalogue = Depends(_get_catalogue),
) -> Playbook:
    try:
        return catalogue.get(playbook_id)
    except KeyError:
        raise HTTPException(404, "playbook not found")
