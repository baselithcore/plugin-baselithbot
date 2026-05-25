"""Graph query endpoints (attack-surface visualization)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends

from core.di.container import ServiceRegistry
from plugins.red_agent.dependencies import require_viewer
from plugins.red_agent.graph import VulnerabilityGraph

router = APIRouter(prefix="/graph", tags=["red-agent"])


def _get_graph() -> VulnerabilityGraph:
    g = ServiceRegistry.get(VulnerabilityGraph)
    if g is None:
        raise RuntimeError("VulnerabilityGraph not registered")
    return g


@router.get("/attack-surface", dependencies=[require_viewer()])
async def attack_surface(
    target: str,
    graph: VulnerabilityGraph = Depends(_get_graph),
) -> dict[str, Any]:
    """Cytoscape-shaped {nodes, edges} for the attack-surface view."""
    return graph.attack_surface(target)


@router.get("/finding/{finding_id}", dependencies=[require_viewer()])
async def finding_subgraph(
    finding_id: str,
    depth: int = 2,
    graph: VulnerabilityGraph = Depends(_get_graph),
) -> dict[str, Any]:
    """Subgraph centered on a vulnerability for the finding-detail modal."""
    return graph.finding_subgraph(finding_id, depth=max(1, min(depth, 4)))
