"""Knowledge-graph reporting (graphify PR2).

Generates two artifacts from a :class:`GraphSnapshot`:

- ``GRAPH_REPORT.md`` — human-readable summary suitable for committing
  alongside the wiki vault. Highlights top entities by PageRank, lists
  communities with representative members, and surfaces "surprising
  connections" (cross-community high-confidence edges).
- ``graph.json`` — full graph dump (nodes + edges + computed scores).
  Consumable by the React UI in PR3 or downstream tooling.

Layout
------
Files land under ``GRAPH_REPORT_DIR`` (default ``WIKI_ROOT/.graphify/``).
The directory is created on demand; the CLI prints paths on completion.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from llm_wiki.config import GRAPH_REPORT_DIR
from llm_wiki.graphdb.algorithms import GraphSnapshot, snapshot

logger = logging.getLogger(__name__)

# Cap members per community in the markdown listing — keeps the report
# scannable even when one community swallows half the graph.
_REPORT_MEMBERS_PER_COMMUNITY = 8
_REPORT_TOP_ENTITIES = 20
_REPORT_TOP_SURPRISING = 15
_REPORT_TOP_COMMUNITIES = 12


@dataclass(slots=True)
class ReportPaths:
    markdown: Path
    json: Path


def generate(graph: Any, *, output_dir: str | Path | None = None) -> ReportPaths:
    """Compute snapshot + write both artifacts. Returns the paths."""
    snap = snapshot(graph)
    out = _resolve_output_dir(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    md_path = out / "GRAPH_REPORT.md"
    json_path = out / "graph.json"
    md_path.write_text(render_markdown(snap), encoding="utf-8")
    json_path.write_text(render_json(graph, snap), encoding="utf-8")
    logger.info("[graph.report] wrote %s and %s", md_path, json_path)
    return ReportPaths(markdown=md_path, json=json_path)


def _resolve_output_dir(output_dir: str | Path | None) -> Path:
    if output_dir is not None:
        return Path(output_dir)
    return Path(GRAPH_REPORT_DIR)


# --- markdown --------------------------------------------------------------


def render_markdown(snap: GraphSnapshot) -> str:
    """Build the GRAPH_REPORT.md body. No I/O — pure string assembly."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    lines: list[str] = [
        "# Knowledge Graph Report",
        "",
        f"_Generated: {now}_",
        "",
        f"- **Entities**: {snap.node_count}",
        f"- **Relations**: {snap.edge_count}",
        f"- **Communities (Leiden)**: {len(snap.communities)}",
        "",
        "## Top entities by PageRank",
        "",
    ]
    if snap.pagerank:
        lines.append("| Rank | Entity | Kind | Score |")
        lines.append("| ---: | ------ | ---- | ----: |")
        for i, e in enumerate(snap.pagerank[:_REPORT_TOP_ENTITIES], 1):
            lines.append(f"| {i} | {e.name} | `{e.kind}` | {e.score:.4f} |")
    else:
        lines.append("_Graph is empty or PageRank unavailable._")
    lines.append("")

    lines.append("## Communities")
    lines.append("")
    if snap.communities:
        for c in snap.communities[:_REPORT_TOP_COMMUNITIES]:
            size = len(c.members)
            preview = ", ".join(m for m in c.members[:_REPORT_MEMBERS_PER_COMMUNITY])
            more = (
                ""
                if size <= _REPORT_MEMBERS_PER_COMMUNITY
                else f" … (+{size - _REPORT_MEMBERS_PER_COMMUNITY} more)"
            )
            lines.append(
                f"- **Community {c.id}** — {size} members, cohesion {c.cohesion:.2f}"
            )
            lines.append(f"  - {preview}{more}")
    else:
        lines.append("_No communities computed (install `leidenalg` for Leiden)._")
    lines.append("")

    lines.append("## Surprising connections")
    lines.append("")
    lines.append(
        "_High-confidence relations that cross community boundaries — often "
        "the most insight-dense edges._"
    )
    lines.append("")
    if snap.surprising:
        lines.append("| src → dst | kind | confidence | communities |")
        lines.append("| --------- | ---- | ---------: | ----------- |")
        for s in snap.surprising[:_REPORT_TOP_SURPRISING]:
            lines.append(
                f"| `{s.src}` → `{s.dst}` | {s.kind} | {s.confidence:.2f} | "
                f"{s.src_community} ↔ {s.dst_community} |"
            )
    else:
        lines.append(
            "_None — try lowering `GRAPH_CONFIDENCE_MIN` or ingest more pages._"
        )
    lines.append("")
    return "\n".join(lines)


# --- json ------------------------------------------------------------------


def render_json(graph: Any, snap: GraphSnapshot) -> str:
    """Full graph dump + computed scores. Stable schema for UI consumers."""
    pagerank_map = {s.entity_id: s.score for s in snap.pagerank}
    degree_map = {s.entity_id: s.score for s in snap.degree}
    community_map: dict[str, int] = {}
    for c in snap.communities:
        for m in c.members:
            community_map[m] = c.id

    nodes: list[dict[str, Any]] = []
    if graph is not None:
        try:
            for nid, attrs in graph.nodes(data=True):
                nodes.append(
                    {
                        "id": nid,
                        "name": attrs.get("name") or nid,
                        "kind": attrs.get("kind") or "",
                        "pagerank": pagerank_map.get(nid, 0.0),
                        "degree": degree_map.get(nid, 0.0),
                        "community": community_map.get(nid, -1),
                    }
                )
        except Exception as exc:
            logger.warning("[graph.report] node dump failed: %s", exc)

    edges: list[dict[str, Any]] = []
    if graph is not None:
        try:
            for u, v, attrs in graph.edges(data=True):
                edges.append(
                    {
                        "src": u,
                        "dst": v,
                        "kind": attrs.get("kind") or "",
                        "confidence": float(attrs.get("confidence", 0.0) or 0.0),
                    }
                )
        except Exception as exc:
            logger.warning("[graph.report] edge dump failed: %s", exc)

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "stats": {
            "node_count": snap.node_count,
            "edge_count": snap.edge_count,
            "community_count": len(snap.communities),
        },
        "nodes": nodes,
        "edges": edges,
        "communities": [
            {
                "id": c.id,
                "size": len(c.members),
                "cohesion": c.cohesion,
                "members": c.members,
            }
            for c in snap.communities
        ],
        "surprising": [
            {
                "src": s.src,
                "dst": s.dst,
                "kind": s.kind,
                "confidence": s.confidence,
                "src_community": s.src_community,
                "dst_community": s.dst_community,
            }
            for s in snap.surprising
        ],
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


__all__ = ["ReportPaths", "generate", "render_json", "render_markdown"]
