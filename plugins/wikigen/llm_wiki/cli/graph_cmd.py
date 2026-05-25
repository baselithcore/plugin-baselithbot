"""``wiki-wl graph ...`` — operate on the knowledge graph (graphify-inspired).

Subcommands:

- ``rebuild`` — wipe entity layer + re-extract entities/relations from
  every page under ``WIKI_DIR``. Heavy: 1 LLM call per page. Use after
  major pack ontology changes.
- ``report`` — write ``GRAPH_REPORT.md`` and ``graph.json`` under
  ``GRAPH_REPORT_DIR``. Read-only on the graph.
- ``export`` — dump the entity graph to one of: ``graphml``, ``cypher``,
  ``obsidian``. Writes under ``GRAPH_REPORT_DIR/exports/`` by default.
- ``query`` — semantic substring search over entities, plus 1-hop neighbor
  preview for the top match. Scoped subgraph — much smaller than reading
  ``GRAPH_REPORT.md`` whole.
- ``path`` — shortest entity path between two names or ids.
- ``explain`` — focused subgraph around one entity: canonical pages +
  1-hop neighbors.

All subcommands require a graph store (FalkorDB up + ``GRAPH_DB_ENABLED=true``).
On a disabled graph they print an actionable diagnostic and exit 1.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.panel import Panel
from rich.table import Table

from llm_wiki.cli._output import EXIT_USER_ERROR, emit_error, emit_json, get_ctx

if TYPE_CHECKING:
    from llm_wiki.graphdb.store import EntityRecord, KnowledgeGraphStore

logger = logging.getLogger(__name__)

graph_app = typer.Typer(help="Knowledge graph operations (graphify-inspired)")


def _require_store(ctx: typer.Context) -> KnowledgeGraphStore:
    """Return a usable :class:`KnowledgeGraphStore` or exit 1."""
    from llm_wiki.graphdb.store import get_kg_store

    store = get_kg_store()
    if not store.enabled:
        emit_error(
            ctx,
            message=(
                "Graph store is disabled or unreachable. Enable with "
                "`GRAPH_DB_ENABLED=true` and start FalkorDB "
                "(`docker compose --profile graph up -d`)."
            ),
        )
        raise typer.Exit(code=EXIT_USER_ERROR)
    return store


@graph_app.command("rebuild")
def graph_rebuild(
    ctx: typer.Context,
    limit: int = typer.Option(
        0, "--limit", min=0, help="Cap re-extraction to first N pages (0 = no cap)."
    ),
    page_type: str = typer.Option(
        "", "--page-type", help="Restrict to one page type (e.g. concept, source)."
    ),
) -> None:
    """Re-extract entities + relations from every wiki page.

    Wipes pre-existing MENTIONS / DEFINED_IN / page-attributed R edges
    per page before re-writing — idempotent. Pages already in the graph
    have their entities collapsed via MERGE on canonical id.
    """
    from llm_wiki.config import GRAPH_EXTRACT_ENABLED, WIKI_DIR, WIKI_ROOT
    from llm_wiki.domain.prompts import get_registry
    from llm_wiki.domain.registry import get_pack
    from llm_wiki.graphdb.extraction import extract_from_page
    from llm_wiki.wiki.parser import parse_file, walk_wiki

    if not GRAPH_EXTRACT_ENABLED:
        emit_error(ctx, message="GRAPH_EXTRACT_ENABLED=false — set it to enable extraction.")
        raise typer.Exit(code=EXIT_USER_ERROR)

    store = _require_store(ctx)
    store.ensure_indexes()
    pack = get_pack()
    registry = get_registry()

    output = get_ctx(ctx)
    paths = walk_wiki(WIKI_DIR)
    if not paths:
        emit_error(ctx, message=f"No pages under {WIKI_DIR}.")
        raise typer.Exit(code=EXIT_USER_ERROR)
    if limit:
        paths = paths[:limit]

    processed = 0
    skipped = 0
    failures = 0
    output.console.print(f"[graph] re-extracting {len(paths)} page(s)…")
    for path in paths:
        page = parse_file(path, WIKI_ROOT)
        if page is None or not page.body:
            skipped += 1
            continue
        if page_type and page.page_type != page_type:
            skipped += 1
            continue
        try:
            payload = extract_from_page(
                page_id=page.document_id,
                page_title=page.title,
                page_body=page.body,
                page_type=page.page_type,
                pack=pack,
                registry=registry,
                store=store,
            )
            output.console.print(
                f"  · {page.document_id}: {len(payload.entities)} entities, "
                f"{len(payload.relations)} relations"
            )
            processed += 1
        except Exception as exc:
            failures += 1
            logger.warning("[graph.rebuild] %s failed: %s", page.document_id, exc)

    summary = {
        "processed": processed,
        "skipped": skipped,
        "failures": failures,
        "total_pages": len(paths),
    }
    if output.json_output:
        emit_json(summary)
    else:
        output.console.print(
            Panel.fit(
                f"processed={processed}  skipped={skipped}  failures={failures}",
                title="graph rebuild",
            )
        )


@graph_app.command("report")
def graph_report(
    ctx: typer.Context,
    output_dir: str = typer.Option(
        "", "--output-dir", help="Override GRAPH_REPORT_DIR (default WIKI_ROOT/.graphify)."
    ),
) -> None:
    """Compute snapshot + write GRAPH_REPORT.md and graph.json."""
    from llm_wiki.graphdb.report import generate

    store = _require_store(ctx)
    graph = store.to_networkx()
    paths = generate(graph, output_dir=output_dir or None)
    output = get_ctx(ctx)
    if output.json_output:
        emit_json({"markdown": str(paths.markdown), "json": str(paths.json)})
        return
    table = Table(title="graph report", show_header=False)
    table.add_row("markdown", str(paths.markdown))
    table.add_row("json", str(paths.json))
    output.console.print(table)


@graph_app.command("export")
def graph_export(
    ctx: typer.Context,
    fmt: str = typer.Option(
        "graphml",
        "--format",
        "-f",
        help="Output format: graphml | cypher | obsidian | html.",
    ),
    output_dir: str = typer.Option("", "--output-dir", help="Override GRAPH_REPORT_DIR/exports/."),
) -> None:
    """Export the entity graph for downstream tools.

    - ``graphml`` → ``graph.graphml`` (Gephi / yEd / Cytoscape).
    - ``cypher`` → ``graph.cypher`` (Neo4j import).
    - ``obsidian`` → directory of wikilinked markdown pages.
    - ``html`` → standalone Cytoscape page with the graph embedded inline.
    """
    from llm_wiki.config import GRAPH_REPORT_DIR
    from llm_wiki.graphdb.export import to_cypher, to_graphml, to_html, to_obsidian_vault

    store = _require_store(ctx)
    graph = store.to_networkx()
    base = Path(output_dir) if output_dir else Path(GRAPH_REPORT_DIR) / "exports"
    base.mkdir(parents=True, exist_ok=True)

    fmt_norm = fmt.strip().lower()
    written: list[str] = []
    if fmt_norm == "graphml":
        path = to_graphml(graph, base / "graph.graphml")
        if path:
            written.append(str(path))
    elif fmt_norm == "cypher":
        path = to_cypher(graph, base / "graph.cypher")
        if path:
            written.append(str(path))
    elif fmt_norm == "obsidian":
        written.extend(str(p) for p in to_obsidian_vault(graph, base / "obsidian"))
    elif fmt_norm == "html":
        path = to_html(graph, base / "graph.html")
        if path:
            written.append(str(path))
    else:
        emit_error(
            ctx,
            message=f"unknown format {fmt_norm!r}. Use graphml | cypher | obsidian | html.",
        )
        raise typer.Exit(code=EXIT_USER_ERROR)

    output = get_ctx(ctx)
    if output.json_output:
        emit_json({"format": fmt_norm, "count": len(written), "files": written})
        return
    output.console.print(f"[graph.export] {fmt_norm}: wrote {len(written)} file(s)")
    for w in written[:10]:
        output.console.print(f"  · {w}")
    if len(written) > 10:
        output.console.print(f"  · … (+{len(written) - 10} more)")


def _resolve_entity(store: KnowledgeGraphStore, needle: str) -> EntityRecord | None:
    """Resolve free-text name OR canonical id (``kind:slug``) to an EntityRecord.

    Direct id lookup wins; otherwise substring search returns the top match.
    Returns ``None`` if no entity matches.
    """
    if not needle.strip():
        return None
    direct = store.get_entity(needle.strip())
    if direct is not None:
        return direct
    rows = store.search_entities(needle.strip(), limit=1)
    return rows[0] if rows else None


@graph_app.command("query")
def graph_query(
    ctx: typer.Context,
    text: str = typer.Argument(..., help="Question or keyword (substring match on entity names)."),
    kind: str = typer.Option("", "--kind", help="Filter on entity kind (e.g. concept, source)."),
    limit: int = typer.Option(10, "--limit", min=1, max=50, help="Top-N entity matches."),
    neighbors: int = typer.Option(5, "--neighbors", min=0, max=25, help="1-hop neighbors per hit."),
) -> None:
    """Substring search over entity names + neighbor preview for top hit.

    Returns a scoped subgraph that is much smaller than ``GRAPH_REPORT.md``
    and steers downstream work toward the relevant entities.
    """
    store = _require_store(ctx)
    rows = store.search_entities(text, kind=kind or None, limit=limit)
    output = get_ctx(ctx)

    if not rows:
        if output.json_output:
            emit_json({"query": text, "count": 0, "results": [], "neighbors": []})
            return
        output.console.print(f"[graph.query] no entities match {text!r}")
        return

    top = rows[0]
    nbrs = store.neighbors(top.id, hops=1, limit=neighbors) if neighbors > 0 else []
    payload = {
        "query": text,
        "kind": kind or None,
        "count": len(rows),
        "results": [{"id": r.id, "name": r.name, "kind": r.kind} for r in rows],
        "top": {"id": top.id, "name": top.name, "kind": top.kind},
        "neighbors": [{"id": n.id, "name": n.name, "kind": n.kind} for n in nbrs],
    }
    if output.json_output:
        emit_json(payload)
        return

    table = Table(title=f"matches for {text!r}", show_lines=False)
    table.add_column("id")
    table.add_column("name")
    table.add_column("kind")
    for r in rows:
        table.add_row(r.id, r.name, r.kind)
    output.console.print(table)
    if nbrs:
        nbr_table = Table(title=f"1-hop neighbors of {top.name!r}", show_lines=False)
        nbr_table.add_column("id")
        nbr_table.add_column("name")
        nbr_table.add_column("kind")
        for n in nbrs:
            nbr_table.add_row(n.id, n.name, n.kind)
        output.console.print(nbr_table)


@graph_app.command("path")
def graph_path(
    ctx: typer.Context,
    src: str = typer.Argument(..., help="Source entity name or id."),
    dst: str = typer.Argument(..., help="Destination entity name or id."),
    max_hops: int = typer.Option(5, "--max-hops", min=1, max=8, help="Max path length."),
) -> None:
    """Shortest entity path between two entities.

    Accepts free-text names (resolved via top-1 search) or canonical ids
    (``kind:slug``). Exits 1 if either endpoint cannot be resolved.
    """
    store = _require_store(ctx)
    src_ent = _resolve_entity(store, src)
    dst_ent = _resolve_entity(store, dst)
    output = get_ctx(ctx)

    if src_ent is None or dst_ent is None:
        unresolved = [name for name, ent in ((src, src_ent), (dst, dst_ent)) if ent is None]
        emit_error(ctx, message=f"entity not found: {', '.join(repr(n) for n in unresolved)}")
        raise typer.Exit(code=EXIT_USER_ERROR)

    path = store.shortest_path(src_ent.id, dst_ent.id, max_hops=max_hops)
    payload = {
        "src": {"id": src_ent.id, "name": src_ent.name},
        "dst": {"id": dst_ent.id, "name": dst_ent.name},
        "max_hops": max_hops,
        "found": bool(path),
        "length": max(0, len(path) - 1),
        "path": path,
    }
    if output.json_output:
        emit_json(payload)
        return

    if not path:
        output.console.print(
            f"[graph.path] no path within {max_hops} hops from {src_ent.name!r} to {dst_ent.name!r}"
        )
        return
    output.console.print(
        Panel.fit(
            " → ".join(path),
            title=f"path {src_ent.name!r} → {dst_ent.name!r} ({len(path) - 1} hops)",
        )
    )


@graph_app.command("explain")
def graph_explain(
    ctx: typer.Context,
    concept: str = typer.Argument(..., help="Entity name or canonical id."),
    neighbors: int = typer.Option(10, "--neighbors", min=0, max=50, help="1-hop neighbors cap."),
) -> None:
    """Focused subgraph for one entity: definition pages + 1-hop neighbors.

    Useful starting point when an entity surfaces in a query and you want
    the immediate context without reading the full graph.
    """
    from llm_wiki.config import GRAPH_CONFIDENCE_MIN

    store = _require_store(ctx)
    ent = _resolve_entity(store, concept)
    output = get_ctx(ctx)

    if ent is None:
        emit_error(ctx, message=f"entity not found: {concept!r}")
        raise typer.Exit(code=EXIT_USER_ERROR)

    nbrs = store.neighbors(ent.id, hops=1, limit=neighbors) if neighbors > 0 else []
    pages = store.pages_for_entities([ent.id], confidence_min=GRAPH_CONFIDENCE_MIN, limit=10)

    payload = {
        "entity": {"id": ent.id, "name": ent.name, "kind": ent.kind, "aliases": ent.aliases},
        "pages": pages,
        "neighbors": [{"id": n.id, "name": n.name, "kind": n.kind} for n in nbrs],
    }
    if output.json_output:
        emit_json(payload)
        return

    header = Table(title=f"entity {ent.name!r}", show_header=False)
    header.add_row("id", ent.id)
    header.add_row("kind", ent.kind)
    if ent.aliases:
        header.add_row("aliases", ", ".join(ent.aliases))
    output.console.print(header)

    if pages:
        page_table = Table(title="pages")
        page_table.add_column("page_id")
        for pid in pages:
            page_table.add_row(pid)
        output.console.print(page_table)
    if nbrs:
        nbr_table = Table(title="1-hop neighbors")
        nbr_table.add_column("id")
        nbr_table.add_column("name")
        nbr_table.add_column("kind")
        for n in nbrs:
            nbr_table.add_row(n.id, n.name, n.kind)
        output.console.print(nbr_table)


__all__ = ["graph_app"]
