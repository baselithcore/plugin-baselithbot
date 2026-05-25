"""Graph export formats (graphify PR2).

Targets:

- **GraphML** — XML standard consumed by Gephi, yEd, Cytoscape Desktop.
  Uses NetworkX's native writer (full fidelity).
- **Neo4j Cypher DDL** — `CREATE` statements importable into Neo4j or
  any openCypher store. Idempotent (`MERGE` over `CREATE`).
- **Obsidian vault** — one markdown page per Entity + per Community,
  with frontmatter + wikilinks. Lets users browse the extracted graph
  inside Obsidian alongside the original wiki vault.

All exporters write to a target directory and return the list of paths
created. Empty graphs produce no output (logged as a no-op).
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any

from llm_wiki.graphdb.algorithms import GraphSnapshot, snapshot

logger = logging.getLogger(__name__)

# Filename-safe slug for Obsidian page names. Matches `wiki/parser.py`
# slug style: lowercase ascii + dashes.
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slug(s: str) -> str:
    out = _SLUG_RE.sub("-", (s or "").strip().lower()).strip("-")
    return out or "unnamed"


# --- GraphML ---------------------------------------------------------------


def to_graphml(graph: Any, output: Path) -> Path | None:
    """Write the entity graph in GraphML format. Returns the path or None
    if the graph is empty / NetworkX unavailable.
    """
    if graph is None or graph.number_of_nodes() == 0:
        logger.info("[graph.export] graphml: empty graph, skipping")
        return None
    try:
        import networkx as nx  # type: ignore[import-not-found]
    except ImportError:
        logger.warning("[graph.export] networkx not installed; cannot write GraphML")
        return None
    output.parent.mkdir(parents=True, exist_ok=True)
    nx.write_graphml(graph, str(output))
    logger.info("[graph.export] graphml: wrote %s", output)
    return output


# --- Neo4j Cypher ---------------------------------------------------------


def _cypher_escape(value: Any) -> str:
    """Escape a Python value into a Cypher literal.

    Strings: single-quoted with backslash + quote escapes. Booleans →
    ``true/false``. Numbers as-is. None → ``NULL``. Lists recursed.
    """
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, list | tuple):
        return "[" + ", ".join(_cypher_escape(v) for v in value) + "]"
    s = str(value).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{s}'"


def to_cypher(graph: Any, output: Path) -> Path | None:
    """Write idempotent Cypher DDL importable into Neo4j.

    Output structure:

        // header comment
        CREATE INDEX entity_id IF NOT EXISTS FOR (e:Entity) ON (e.id);

        MERGE (:Entity {id: 'concept:foo', name: 'Foo', kind: 'concept'});
        ...

        MATCH (a:Entity {id: 'A'}), (b:Entity {id: 'B'})
        MERGE (a)-[:R {kind: 'COVERS', confidence: 0.9}]->(b);

    Idempotent: re-running on the same store overwrites property values
    via MERGE-then-SET. Safe for repeated CI runs.
    """
    if graph is None or graph.number_of_nodes() == 0:
        logger.info("[graph.export] cypher: empty graph, skipping")
        return None
    output.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = [
        "// Neo4j Cypher DDL — exported from llm-wiki-grafiphy.",
        "// Apply with: cypher-shell -f graph.cypher",
        "",
        "CREATE INDEX entity_id IF NOT EXISTS FOR (e:Entity) ON (e.id);",
        "",
        "// --- Entities --------------------------------------------------",
        "",
    ]
    for nid, attrs in graph.nodes(data=True):
        props = {
            "id": nid,
            "name": attrs.get("name") or nid,
            "kind": attrs.get("kind") or "",
        }
        prop_str = ", ".join(f"{k}: {_cypher_escape(v)}" for k, v in props.items())
        lines.append(f"MERGE (:Entity {{{prop_str}}});")

    lines.append("")
    lines.append("// --- Relations -------------------------------------------------")
    lines.append("")
    for u, v, data in graph.edges(data=True):
        props = {
            "kind": data.get("kind") or "",
            "confidence": float(data.get("confidence", 0.0) or 0.0),
        }
        prop_str = ", ".join(f"{k}: {_cypher_escape(val)}" for k, val in props.items())
        lines.append(
            f"MATCH (a:Entity {{id: {_cypher_escape(u)}}}), "
            f"(b:Entity {{id: {_cypher_escape(v)}}}) "
            f"MERGE (a)-[r:R {{kind: {_cypher_escape(props['kind'])}}}]->(b) "
            f"SET r.confidence = {_cypher_escape(props['confidence'])};"
        )
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("[graph.export] cypher: wrote %s", output)
    return output


# --- Obsidian vault --------------------------------------------------------


def to_obsidian_vault(graph: Any, output_dir: Path) -> list[Path]:
    """Generate an Obsidian-readable vault from the entity graph.

    Layout::

        <output_dir>/
          entities/
            <kind>-<slug>.md          # one page per Entity
          communities/
            community-<id>.md         # one page per Leiden community

    Each entity page links to its neighbors via wikilinks (`[[…]]`).
    Each community page lists its members as wikilinks. Together they
    let users open the extracted graph as a native Obsidian vault.
    """
    if graph is None or graph.number_of_nodes() == 0:
        logger.info("[graph.export] obsidian: empty graph, skipping")
        return []

    snap = snapshot(graph)
    pagerank_map = {s.entity_id: s.score for s in snap.pagerank}
    community_map: dict[str, int] = {}
    for c in snap.communities:
        for m in c.members:
            community_map[m] = c.id

    entities_dir = output_dir / "entities"
    communities_dir = output_dir / "communities"
    entities_dir.mkdir(parents=True, exist_ok=True)
    communities_dir.mkdir(parents=True, exist_ok=True)

    written: list[Path] = []
    name_index: dict[str, str] = {}  # entity_id → filename stem (for wikilinks)

    # First pass: stable filename per entity, so wikilinks resolve.
    for nid, attrs in graph.nodes(data=True):
        kind = str(attrs.get("kind") or "entity")
        stem = f"{kind}-{_slug(nid.split(':', 1)[-1] if ':' in nid else nid)}"
        name_index[nid] = stem

    # Entity pages.
    for nid, attrs in graph.nodes(data=True):
        page = _entity_page(
            entity_id=nid,
            attrs=attrs,
            graph=graph,
            name_index=name_index,
            community_id=community_map.get(nid, -1),
            pagerank=pagerank_map.get(nid, 0.0),
        )
        out_path = entities_dir / f"{name_index[nid]}.md"
        out_path.write_text(page, encoding="utf-8")
        written.append(out_path)

    # Community pages.
    for community in snap.communities:
        page = _community_page(community, name_index=name_index, graph=graph)
        out_path = communities_dir / f"community-{community.id:03d}.md"
        out_path.write_text(page, encoding="utf-8")
        written.append(out_path)

    logger.info("[graph.export] obsidian: wrote %d pages under %s", len(written), output_dir)
    return written


def _entity_page(
    *,
    entity_id: str,
    attrs: dict[str, Any],
    graph: Any,
    name_index: dict[str, str],
    community_id: int,
    pagerank: float,
) -> str:
    name = str(attrs.get("name") or entity_id)
    kind = str(attrs.get("kind") or "")
    out_neighbors: list[tuple[str, str, float]] = []
    in_neighbors: list[tuple[str, str, float]] = []
    for _, nbr, data in graph.out_edges(entity_id, data=True):
        out_neighbors.append((nbr, str(data.get("kind") or ""), float(data.get("confidence", 0.0))))
    for nbr, _, data in graph.in_edges(entity_id, data=True):
        in_neighbors.append((nbr, str(data.get("kind") or ""), float(data.get("confidence", 0.0))))

    lines = [
        "---",
        f"id: {entity_id}",
        f"kind: {kind}",
        f"pagerank: {pagerank:.6f}",
        f"community: {community_id}",
        "tags: [graphify, entity]",
        "---",
        "",
        f"# {name}",
        "",
        f"- **Kind**: `{kind}`",
        f"- **PageRank**: {pagerank:.4f}",
        f"- **Community**: [[community-{community_id:03d}]]"
        if community_id >= 0
        else "- **Community**: orphan",
        "",
    ]
    if out_neighbors:
        lines.append("## Outgoing relations")
        for nbr, rel, conf in out_neighbors:
            link = name_index.get(nbr, _slug(nbr))
            lines.append(f"- `{rel}` → [[{link}]] _(conf {conf:.2f})_")
        lines.append("")
    if in_neighbors:
        lines.append("## Incoming relations")
        for nbr, rel, conf in in_neighbors:
            link = name_index.get(nbr, _slug(nbr))
            lines.append(f"- [[{link}]] `{rel}` → _(conf {conf:.2f})_")
        lines.append("")
    return "\n".join(lines)


def _community_page(community: Any, *, name_index: dict[str, str], graph: Any) -> str:
    """Render a Leiden community as an Obsidian index page."""
    members = community.members
    lines = [
        "---",
        f"id: community-{community.id:03d}",
        f"size: {len(members)}",
        f"cohesion: {community.cohesion:.4f}",
        "tags: [graphify, community]",
        "---",
        "",
        f"# Community {community.id}",
        "",
        f"- **Size**: {len(members)} entities",
        f"- **Cohesion**: {community.cohesion:.2f}",
        "",
        "## Members",
        "",
    ]
    for m in members:
        attrs = graph.nodes.get(m, {}) or {}
        name = str(attrs.get("name") or m)
        link = name_index.get(m, _slug(m))
        lines.append(f"- [[{link}|{name}]]")
    return "\n".join(lines)


# --- Standalone HTML (Cytoscape) ------------------------------------------


_HTML_TEMPLATE = """<!doctype html>
<html lang="it">
<head>
<meta charset="utf-8">
<title>Knowledge Graph</title>
<style>
  html, body {{ margin: 0; padding: 0; height: 100%; font-family: -apple-system, system-ui, sans-serif; }}
  #cy {{ width: 100vw; height: 100vh; background: #0b0c10; }}
  #hud {{ position: fixed; top: 12px; left: 12px; padding: 10px 14px;
         background: rgba(20,22,28,0.85); color: #e8eaed; border-radius: 8px;
         font-size: 12px; line-height: 1.5; max-width: 320px; }}
  #hud strong {{ color: #8ab4f8; }}
</style>
<script src="https://unpkg.com/cytoscape@3.30.0/dist/cytoscape.min.js"></script>
<script src="https://unpkg.com/layout-base@2.0.1/layout-base.js"></script>
<script src="https://unpkg.com/cose-base@2.2.0/cose-base.js"></script>
<script src="https://unpkg.com/cytoscape-cose-bilkent@4.1.0/cytoscape-cose-bilkent.js"></script>
</head>
<body>
<div id="cy"></div>
<div id="hud">
  <div><strong>Knowledge Graph</strong></div>
  <div>nodi: <span id="n-nodes">0</span> · archi: <span id="n-edges">0</span> · community: <span id="n-comms">0</span></div>
  <div style="margin-top:6px; opacity:0.8">click su nodo per evidenziare 1-hop</div>
</div>
<script>
const DATA = {data_json};
const palette = ["#8ab4f8","#f28b82","#fdd663","#81c995","#c58af9","#78d9ec","#f6aea9","#aecbfa"];
const nodes = (DATA.nodes||[]).map(n => ({{
  data: {{ id: n.id, label: n.name||n.id, kind: n.kind||"", community: n.community||0,
          pagerank: n.pagerank||0 }}
}}));
const edges = (DATA.edges||[]).map((e,i) => ({{
  data: {{ id: "e"+i, source: e.src, target: e.dst, kind: e.kind||"", confidence: e.confidence||0 }}
}}));
document.getElementById("n-nodes").textContent = nodes.length;
document.getElementById("n-edges").textContent = edges.length;
document.getElementById("n-comms").textContent = (DATA.communities||[]).length;
const cy = cytoscape({{
  container: document.getElementById("cy"),
  elements: {{ nodes, edges }},
  style: [
    {{ selector: "node",
       style: {{ "background-color": ele => palette[(ele.data("community")||0) % palette.length],
                "label": "data(label)", "color": "#e8eaed", "font-size": 10,
                "text-outline-color": "#0b0c10", "text-outline-width": 2,
                "width": ele => 12 + 28 * Math.log(1 + (ele.data("pagerank")||0) * 30),
                "height": ele => 12 + 28 * Math.log(1 + (ele.data("pagerank")||0) * 30) }} }},
    {{ selector: "edge",
       style: {{ "width": ele => 0.5 + 2 * (ele.data("confidence")||0),
                "line-color": "#5f6368", "curve-style": "bezier",
                "target-arrow-shape": "triangle", "target-arrow-color": "#5f6368",
                "opacity": 0.6 }} }},
    {{ selector: ".highlight", style: {{ "background-color": "#fff", "line-color": "#fff",
                                       "target-arrow-color": "#fff", "opacity": 1 }} }},
    {{ selector: ".dim", style: {{ "opacity": 0.1 }} }},
  ],
  layout: {{ name: "cose-bilkent", animate: false, nodeRepulsion: 4500,
            idealEdgeLength: 80, gravity: 0.25 }},
}});
cy.on("tap", "node", evt => {{
  const n = evt.target;
  cy.elements().addClass("dim").removeClass("highlight");
  n.neighborhood().add(n).removeClass("dim").addClass("highlight");
}});
cy.on("tap", evt => {{ if (evt.target === cy) cy.elements().removeClass("dim highlight"); }});
</script>
</body>
</html>
"""


def to_html(graph: Any, output: Path, *, snap: GraphSnapshot | None = None) -> Path | None:
    """Standalone Cytoscape HTML page with the graph embedded inline.

    Loads cytoscape + cose-bilkent from a CDN. ``snap`` (community / pagerank
    bundle) is optional — when omitted the function computes a default snapshot
    via :func:`algorithms.snapshot`. Returns the output path or ``None`` for an
    empty graph.
    """
    if graph is None or graph.number_of_nodes() == 0:
        logger.info("[graph.export] html: empty graph, skipping")
        return None
    from llm_wiki.graphdb.report import render_json

    snap = snap or snapshot(graph)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = render_json(graph, snap)
    output.write_text(
        _HTML_TEMPLATE.format(data_json=payload),
        encoding="utf-8",
    )
    logger.info("[graph.export] html: wrote %s", output)
    return output


__all__ = ["to_cypher", "to_graphml", "to_html", "to_obsidian_vault"]
