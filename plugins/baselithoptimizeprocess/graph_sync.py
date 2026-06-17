"""Knowledge-graph sync: project a process onto the shared graph.

The plugin already *registers* the ``bop_process`` / ``bop_process_step`` /
``bop_kpi`` entity and relationship types (see :class:`BopPlugin`), but nothing
populated them. This module fills that gap: on every process save it upserts the
process, its steps, and its KPIs as graph nodes plus their transition / has-step
/ measures edges, so a mapped process is queryable alongside the rest of the
knowledge graph (cross-process reasoning, lineage, impact analysis).

``graph_elements`` is pure (easy to unit-test); :class:`GraphSyncMixin` applies
them best-effort — a disabled graph or any backend error degrades to a no-op and
never breaks the ingestion path.
"""

from __future__ import annotations

import asyncio

from core.observability.logging import get_logger

from .models import ProcessGraph

logger = get_logger(__name__)

# Graph node/edge shapes: (node_id, labels, properties) and (src, rel, tgt, props).
GraphNode = tuple[str, list[str], dict[str, str]]
GraphEdge = tuple[str, str, str, dict[str, str]]


def _proc_id(tenant: str, process_id: str) -> str:
    return f"bop:{tenant}:proc:{process_id}"


def _step_id(tenant: str, process_id: str, node_id: str) -> str:
    return f"bop:{tenant}:proc:{process_id}:step:{node_id}"


def _kpi_id(tenant: str, process_id: str, kpi_id: str) -> str:
    return f"bop:{tenant}:proc:{process_id}:kpi:{kpi_id}"


def graph_elements(
    tenant: str, process: ProcessGraph
) -> tuple[list[GraphNode], list[GraphEdge]]:
    """Map a process onto knowledge-graph nodes and edges (pure)."""
    pid = _proc_id(tenant, process.id)
    nodes: list[GraphNode] = [
        (
            pid,
            ["bop_process"],
            {
                "name": process.name,
                "description": process.description,
                "tenant_id": tenant,
                "bop_process_id": process.id,
            },
        )
    ]
    edges: list[GraphEdge] = []

    known = {n.id for n in process.nodes}
    for node in process.nodes:
        sid = _step_id(tenant, process.id, node.id)
        nodes.append(
            (
                sid,
                ["bop_process_step"],
                {"name": node.name, "kind": node.kind.value, "role": node.role},
            )
        )
        edges.append((pid, "BOP_HAS_STEP", sid, {}))

    for edge in process.edges:
        if edge.source in known and edge.target in known:
            edges.append(
                (
                    _step_id(tenant, process.id, edge.source),
                    "BOP_NEXT",
                    _step_id(tenant, process.id, edge.target),
                    {"condition": edge.condition},
                )
            )

    for kpi in process.kpis:
        kid = _kpi_id(tenant, process.id, kpi.id)
        nodes.append(
            (
                kid,
                ["bop_kpi"],
                {"name": kpi.name, "unit": kpi.unit, "direction": kpi.direction.value},
            )
        )
        edges.append((kid, "BOP_MEASURES", pid, {}))

    return nodes, edges


def element_ids(tenant: str, process: ProcessGraph) -> list[str]:
    """All graph node ids a process owns (for deletion)."""
    ids = [_proc_id(tenant, process.id)]
    ids += [_step_id(tenant, process.id, n.id) for n in process.nodes]
    ids += [_kpi_id(tenant, process.id, k.id) for k in process.kpis]
    return ids


class GraphSyncMixin:
    """Best-effort knowledge-graph projection mixed into the BOP service."""

    async def _sync_graph(self, tenant: str, process: ProcessGraph) -> None:
        """Upsert a process's nodes/edges into the graph; no-op if disabled."""
        try:
            from core.graph import graph_db

            if not graph_db.is_enabled():
                return
            nodes, edges = graph_elements(tenant, process)

            def _apply() -> None:
                for node_id, labels, props in nodes:
                    graph_db.upsert_node(node_id, labels=labels, properties=props)
                for src, rel, tgt, props in edges:
                    graph_db.upsert_edge(src, rel, tgt, properties=props)

            await asyncio.to_thread(_apply)
        except Exception as exc:  # noqa: BLE001 — sync must never break ingest
            logger.warning(
                "bop_graph_sync_failed", process_id=process.id, error=str(exc)
            )

    async def _unsync_graph(self, tenant: str, process: ProcessGraph) -> None:
        """Delete a process's nodes from the graph; no-op if disabled."""
        try:
            from core.graph import graph_db

            if not graph_db.is_enabled():
                return
            ids = element_ids(tenant, process)

            def _apply() -> None:
                for node_id in ids:
                    graph_db.delete_node(node_id)

            await asyncio.to_thread(_apply)
        except Exception as exc:  # noqa: BLE001 — sync must never break delete
            logger.warning(
                "bop_graph_unsync_failed", process_id=process.id, error=str(exc)
            )


__all__ = ["graph_elements", "element_ids", "GraphSyncMixin"]
