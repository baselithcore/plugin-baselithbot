"""Graph service — the knowledge graph as an interaction surface.

Builds three edge kinds from the corpus:

* **explicit**  — authored ``[[wikilinks]]`` (source of truth, in the files);
* **tag**       — note↔tag membership (shared-tag clustering);
* **derived**   — semantic similarity (from embeddings, disposable).

Exposes the full graph, n-hop neighborhoods (for the docked local graph beside
the editor), MOC (Map-of-Content) cluster suggestions, and per-note link
suggestions (semantic neighbors + unlinked mentions).
"""

from __future__ import annotations

from collections import defaultdict

from . import links as link_utils
from .config_proxy import get_settings
from .models import GraphData, GraphEdge, GraphNode, LinkSuggestion
from .semantic import SemanticIndex


class GraphService:
    """Computes graph views over notes, links, tags and semantic neighbors."""

    def __init__(self, semantic: SemanticIndex) -> None:
        self._semantic = semantic
        self._titles: dict[str, str] = {}
        self._tags: dict[str, list[str]] = {}
        self._links: dict[str, list[str]] = {}
        self._backlinks: dict[str, list[str]] = {}

    def rebuild(
        self,
        titles: dict[str, str],
        tags: dict[str, list[str]],
        links: dict[str, list[str]],
    ) -> None:
        self._titles = dict(titles)
        self._tags = dict(tags)
        # Keep only edges to existing notes (drop dangling targets).
        known = set(titles)
        self._links = {n: [t for t in ts if t in known] for n, ts in links.items()}
        self._backlinks = link_utils.build_backlinks(self._links)

    # ---- accessors -------------------------------------------------------
    def backlinks(self, note_id: str) -> list[str]:
        return self._backlinks.get(note_id, [])

    def forward_links(self, note_id: str) -> list[str]:
        return self._links.get(note_id, [])

    # ---- full graph ------------------------------------------------------
    def full_graph(
        self,
        include_tags: bool = True,
        include_derived: bool = False,
        scope: set[str] | None = None,
    ) -> GraphData:
        # ``scope`` narrows the graph to one workspace: keep only in-scope notes
        # and the edges whose *both* ends stay in scope.
        titles = (
            self._titles
            if scope is None
            else {nid: t for nid, t in self._titles.items() if nid in scope}
        )
        known = set(titles)
        degree: dict[str, int] = defaultdict(int)
        edges: list[GraphEdge] = []

        for source, targets in self._links.items():
            if source not in known:
                continue
            for target in targets:
                if target not in known:
                    continue
                edges.append(GraphEdge(source=source, target=target, kind="explicit"))
                degree[source] += 1
                degree[target] += 1

        nodes: list[GraphNode] = [
            GraphNode(id=nid, label=title, kind="note", degree=degree.get(nid, 0))
            for nid, title in titles.items()
        ]

        if include_tags:
            self._add_tag_edges(nodes, edges, degree, known)
        if include_derived and self._semantic.available:
            self._add_derived_edges(edges, degree, known)

        return GraphData(nodes=nodes, edges=edges)

    def _add_tag_edges(self, nodes, edges, degree, known: set[str]) -> None:
        seen_tags: set[str] = set()
        for nid, tags in self._tags.items():
            if nid not in known:
                continue
            for tag in tags:
                tag_id = f"tag:{tag}"
                if tag_id not in seen_tags:
                    seen_tags.add(tag_id)
                    nodes.append(GraphNode(id=tag_id, label=f"#{tag}", kind="tag"))
                edges.append(GraphEdge(source=nid, target=tag_id, kind="tag"))
                degree[tag_id] += 1

    def _add_derived_edges(self, edges, degree, known: set[str]) -> None:
        cfg = get_settings()
        for nid in known:
            for other, _ in self._semantic.neighbors(
                nid, cfg.semantic_edges_per_note, cfg.semantic_edge_threshold
            ):
                if other not in known:
                    continue
                if nid < other:  # de-dupe undirected derived edges
                    edges.append(GraphEdge(source=nid, target=other, kind="derived"))
                    degree[nid] += 1
                    degree[other] += 1

    # ---- local neighborhood (lazy, docked beside editor) -----------------
    def neighborhood(self, note_id: str, hops: int = 1) -> GraphData:
        if note_id not in self._titles:
            return GraphData()
        frontier = {note_id}
        visited = {note_id}
        for _ in range(max(1, hops)):
            nxt: set[str] = set()
            for nid in frontier:
                nxt.update(self._links.get(nid, []))
                nxt.update(self._backlinks.get(nid, []))
            nxt -= visited
            visited |= nxt
            frontier = nxt
            if not frontier:
                break

        nodes = [
            GraphNode(id=nid, label=self._titles.get(nid, nid), kind="note")
            for nid in visited
        ]
        edges = [
            GraphEdge(source=s, target=t, kind="explicit")
            for s in visited
            for t in self._links.get(s, [])
            if t in visited
        ]
        return GraphData(nodes=nodes, edges=edges)

    # ---- MOC cluster suggestions ----------------------------------------
    def moc_candidates(self, min_size: int = 4) -> list[dict]:
        """Suggest Maps-of-Content from dense shared-tag clusters."""
        by_tag: dict[str, list[str]] = defaultdict(list)
        for nid, tags in self._tags.items():
            for tag in tags:
                by_tag[tag].append(nid)
        out = [
            {"tag": tag, "size": len(members), "members": sorted(members)}
            for tag, members in by_tag.items()
            if len(members) >= min_size
        ]
        out.sort(key=lambda c: c["size"], reverse=True)
        return out

    # ---- per-note link suggestions --------------------------------------
    def suggestions(
        self, note_id: str, body: str, top_k: int = 6
    ) -> list[LinkSuggestion]:
        existing = set(self._links.get(note_id, []))
        out: list[LinkSuggestion] = []

        for other in link_utils.unlinked_mentions(
            note_id, body, self._titles, existing
        ):
            out.append(
                LinkSuggestion(
                    id=other,
                    title=self._titles.get(other, other),
                    score=1.0,
                    reason="unlinked-mention",
                )
            )

        if self._semantic.available:
            cfg = get_settings()
            mentioned = {s.id for s in out}
            for other, score in self._semantic.neighbors(
                note_id, top_k, cfg.semantic_edge_threshold
            ):
                if other not in existing and other not in mentioned:
                    out.append(
                        LinkSuggestion(
                            id=other,
                            title=self._titles.get(other, other),
                            score=round(score, 4),
                            reason="semantic",
                        )
                    )
        return out[:top_k]
