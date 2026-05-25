"""Knowledge-graph store layer (graphify-inspired).

Wraps :class:`llm_wiki.graphdb.core.GraphDb` (raw Cypher on FalkorDB) with
typed ops over the wiki ontology:

Schema
------
- ``(:Page {id, title, type, category, tags, source_file})`` — existing
- ``(:Entity {id, name, kind, aliases})`` — new
- ``(:Page)-[:LINKS_TO]->(:Page)`` — existing (from wikilinks)
- ``(:Page)-[:MENTIONS {confidence, tier}]->(:Entity)`` — new
- ``(:Entity)-[:DEFINED_IN]->(:Page)`` — new (canonical page for entity)
- ``(:Entity)-[:R {kind, confidence, tier, evidence, page_id}]->(:Entity)``
  — new. ``kind`` carries the pack-declared relation_type id; ``tier`` ∈
  {EXTRACTED, INFERRED, AMBIGUOUS} (graphify confidence tiers).

Design notes
------------
- All ops are no-op when graph DB is disabled or unreachable. Never raise
  upstream — graph layer is best-effort enrichment, not a hard dependency.
- ``entity_id`` is a deterministic slug derived from (name, kind). Multiple
  surface forms (aliases) collapse to a single canonical node — crucial for
  graph cohesion. See :func:`canonical_entity_id`.
- The store does NOT compute algorithms itself. :meth:`to_networkx` returns
  an in-memory snapshot consumed by PR2 algorithm layer (Leiden, PageRank).

Modular layout (>500 LOC budget):
- :mod:`._models`  — dataclasses + tier constants + canonical id slugger
- :mod:`._helpers` — FalkorDB ``--compact`` row/scalar coercion
- This module      — :class:`KnowledgeGraphStore` orchestrator + singleton
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

from llm_wiki.config import GRAPH_CONFIDENCE_MIN
from llm_wiki.graphdb.core import GraphDb, get_graph_db
from llm_wiki.graphdb.store._helpers import _entity_from_row, _rows, _scalar
from llm_wiki.graphdb.store._models import (
    TIER_AMBIGUOUS,
    TIER_EXTRACTED,
    TIER_INFERRED,
    EntityRecord,
    RelationRecord,
    canonical_entity_id,
    confidence_to_tier,
)

logger = logging.getLogger(__name__)


class KnowledgeGraphStore:
    """Typed wrapper over :class:`GraphDb` for the wiki knowledge graph."""

    def __init__(self, graph: GraphDb | None = None) -> None:
        self._g = graph or get_graph_db()

    @property
    def enabled(self) -> bool:
        return self._g.is_enabled()

    # --- schema setup -------------------------------------------------------

    def ensure_indexes(self) -> None:
        """Idempotent index creation. Safe to call on every startup."""
        if not self.enabled:
            return
        self._g.create_indexes()
        for stmt in (
            "CREATE INDEX FOR (e:Entity) ON (e.id)",
            "CREATE INDEX FOR (e:Entity) ON (e.kind)",
        ):
            try:
                self._g.query(stmt)
            except Exception:
                pass

    # --- writes -------------------------------------------------------------

    def upsert_entity(
        self,
        name: str,
        kind: str,
        *,
        aliases: Iterable[str] | None = None,
    ) -> str:
        """MERGE entity by canonical id. Returns the entity id."""
        eid = canonical_entity_id(name, kind)
        if not self.enabled:
            return eid
        aliases_str = ",".join(sorted({a for a in (aliases or []) if a}))
        cypher = "MERGE (e:Entity {id: $id}) SET e.name = $name, e.kind = $kind, e.aliases = $aliases"
        self._g.query(
            cypher,
            {"id": eid, "name": name, "kind": kind, "aliases": aliases_str},
        )
        return eid

    def link_mention(
        self,
        page_id: str,
        entity_id: str,
        *,
        confidence: float,
        canonical: bool = False,
    ) -> None:
        """Record that ``page_id`` mentions ``entity_id``.

        When ``canonical=True``, also creates the inverse ``DEFINED_IN`` edge
        — meaning this page is the canonical definition source for the
        entity.
        """
        if not self.enabled:
            return
        tier = confidence_to_tier(confidence)
        self._g.query(
            (
                "MATCH (p:Page {id: $page}), (e:Entity {id: $entity}) "
                "MERGE (p)-[m:MENTIONS]->(e) "
                "SET m.confidence = $conf, m.tier = $tier"
            ),
            {"page": page_id, "entity": entity_id, "conf": confidence, "tier": tier},
        )
        if canonical:
            self._g.query(
                (
                    "MATCH (p:Page {id: $page}), (e:Entity {id: $entity}) "
                    "MERGE (e)-[:DEFINED_IN]->(p)"
                ),
                {"page": page_id, "entity": entity_id},
            )

    def upsert_relation(
        self,
        src_id: str,
        dst_id: str,
        kind: str,
        *,
        confidence: float,
        evidence: str = "",
        page_id: str | None = None,
    ) -> None:
        """MERGE typed relation between two entities."""
        if not self.enabled:
            return
        tier = confidence_to_tier(confidence)
        ev = (evidence or "")[:280]
        self._g.query(
            (
                "MATCH (a:Entity {id: $src}), (b:Entity {id: $dst}) "
                "MERGE (a)-[r:R {kind: $kind}]->(b) "
                "SET r.confidence = $conf, r.tier = $tier, r.evidence = $ev, "
                "    r.page_id = $page"
            ),
            {
                "src": src_id,
                "dst": dst_id,
                "kind": kind,
                "conf": confidence,
                "tier": tier,
                "ev": ev,
                "page": page_id or "",
            },
        )

    def delete_page_extractions(self, page_id: str) -> None:
        """Remove MENTIONS + DEFINED_IN + relations attributed to this page."""
        if not self.enabled:
            return
        self._g.query(
            "MATCH (p:Page {id: $page})-[m:MENTIONS]->(:Entity) DELETE m",
            {"page": page_id},
        )
        self._g.query(
            "MATCH (:Entity)-[d:DEFINED_IN]->(p:Page {id: $page}) DELETE d",
            {"page": page_id},
        )
        self._g.query(
            "MATCH (:Entity)-[r:R]->(:Entity) WHERE r.page_id = $page DELETE r",
            {"page": page_id},
        )

    # --- reads --------------------------------------------------------------

    def stats(self) -> dict[str, int]:
        """Top-level graph metrics. Cheap counts only."""
        base = self._g.stats()
        if not self.enabled:
            return {**base, "entities": 0, "mentions": 0, "relations": 0}
        entities = self._count("MATCH (e:Entity) RETURN count(e)")
        mentions = self._count("MATCH ()-[m:MENTIONS]->() RETURN count(m)")
        relations = self._count("MATCH ()-[r:R]->() RETURN count(r)")
        return {
            **base,
            "entities": entities,
            "mentions": mentions,
            "relations": relations,
        }

    def _count(self, cypher: str) -> int:
        try:
            from llm_wiki.graphdb.core import _extract_count

            return _extract_count(self._g.query(cypher))
        except Exception:
            return 0

    def search_entities(
        self,
        query: str,
        *,
        kind: str | None = None,
        limit: int = 25,
    ) -> list[EntityRecord]:
        """Substring match on entity name. Case-insensitive."""
        if not self.enabled or not query.strip():
            return []
        clauses = ["e.name CONTAINS $needle"]
        params: dict[str, Any] = {"needle": query.strip().lower(), "lim": int(limit)}
        if kind:
            clauses.append("e.kind = $kind")
            params["kind"] = kind
        cypher = (
            "MATCH (e:Entity) WHERE "
            + " AND ".join(clauses)
            + " RETURN e.id, e.name, e.kind, e.aliases LIMIT $lim"
        )
        rows = self._rows(self._g.query(cypher, params))
        return [_entity_from_row(r) for r in rows]

    def get_entity(self, entity_id: str) -> EntityRecord | None:
        if not self.enabled:
            return None
        cypher = (
            "MATCH (e:Entity {id: $id}) RETURN e.id, e.name, e.kind, e.aliases LIMIT 1"
        )
        rows = self._rows(self._g.query(cypher, {"id": entity_id}))
        if not rows:
            return None
        return _entity_from_row(rows[0])

    def neighbors(
        self,
        entity_id: str,
        *,
        hops: int = 1,
        confidence_min: float | None = None,
        relation_kind: str | None = None,
        limit: int = 50,
    ) -> list[EntityRecord]:
        """Variable-length neighbor traversal over typed R edges."""
        if not self.enabled:
            return []
        hops = max(1, min(3, int(hops)))
        conf = GRAPH_CONFIDENCE_MIN if confidence_min is None else float(confidence_min)
        kind_filter = f" AND r.kind = '{relation_kind}'" if relation_kind else ""
        cypher = (
            f"MATCH (a:Entity {{id: $id}})-[r:R*1..{hops}]-(b:Entity) "
            f"WHERE ALL(rel IN r WHERE rel.confidence >= $conf{kind_filter}) "
            f"  AND b.id <> $id "
            f"RETURN DISTINCT b.id, b.name, b.kind, b.aliases LIMIT $lim"
        )
        rows = self._rows(
            self._g.query(cypher, {"id": entity_id, "conf": conf, "lim": int(limit)})
        )
        return [_entity_from_row(r) for r in rows]

    def entities_for_page(
        self,
        page_id: str,
        *,
        confidence_min: float | None = None,
        limit: int = 100,
    ) -> list[tuple[EntityRecord, float, str]]:
        """Entità menzionate dalla pagina con ``confidence`` e ``tier``."""
        if not self.enabled or not page_id:
            return []
        conf = GRAPH_CONFIDENCE_MIN if confidence_min is None else float(confidence_min)
        cypher = (
            "MATCH (p:Page {id: $pid})-[m:MENTIONS]->(e:Entity) "
            "WHERE m.confidence >= $conf "
            "RETURN e.id, e.name, e.kind, e.aliases, m.confidence, m.tier "
            "ORDER BY m.confidence DESC LIMIT $lim"
        )
        rows = self._rows(
            self._g.query(cypher, {"pid": page_id, "conf": conf, "lim": int(limit)})
        )
        out: list[tuple[EntityRecord, float, str]] = []
        for r in rows:
            if not r or len(r) < 4:
                continue
            ent = _entity_from_row(r[:4])
            conf_val = float(_scalar(r[4]) or 0.0) if len(r) > 4 else 0.0
            tier_val = str(_scalar(r[5]) or "") if len(r) > 5 else ""
            out.append((ent, conf_val, tier_val))
        return out

    def pages_for_entities(
        self,
        entity_ids: Iterable[str],
        *,
        confidence_min: float | None = None,
        limit: int = 25,
    ) -> list[str]:
        """Pages mentioning any of the given entities, ordered by max
        mention confidence descending."""
        ids = [e for e in entity_ids if e]
        if not self.enabled or not ids:
            return []
        conf = GRAPH_CONFIDENCE_MIN if confidence_min is None else float(confidence_min)
        cypher = (
            "MATCH (p:Page)-[m:MENTIONS]->(e:Entity) "
            "WHERE e.id IN $ids AND m.confidence >= $conf "
            "RETURN DISTINCT p.id, max(m.confidence) AS s "
            "ORDER BY s DESC LIMIT $lim"
        )
        rows = self._rows(
            self._g.query(cypher, {"ids": ids, "conf": conf, "lim": int(limit)})
        )
        out: list[str] = []
        for r in rows:
            if r:
                pid = _scalar(r[0])
                if isinstance(pid, str) and pid:
                    out.append(pid)
        return out

    def shortest_path(
        self,
        src_id: str,
        dst_id: str,
        *,
        max_hops: int = 5,
    ) -> list[str]:
        """Shortest entity path src→dst. Returns ordered list of entity ids
        or [] if unreachable / graph disabled."""
        if not self.enabled:
            return []
        max_hops = max(1, min(8, int(max_hops)))
        cypher = (
            f"MATCH p = shortestPath((a:Entity {{id: $src}})-[:R*1..{max_hops}]-"
            f"(b:Entity {{id: $dst}})) RETURN [n IN nodes(p) | n.id] LIMIT 1"
        )
        rows = self._rows(self._g.query(cypher, {"src": src_id, "dst": dst_id}))
        if not rows:
            return []
        val = _scalar(rows[0][0]) if rows[0] else None
        if isinstance(val, list):
            return [str(x) for x in val]
        return []

    # --- networkx snapshot (for PR2 algorithms) ----------------------------

    def to_networkx(self) -> Any:
        """Load Entity-R-Entity subgraph into a :class:`networkx.DiGraph`."""
        if not self.enabled:
            return None
        try:
            import networkx as nx  # type: ignore[import-not-found]
        except ImportError:
            logger.debug("[graph.store] networkx not installed; to_networkx() → None")
            return None

        g = nx.DiGraph()
        ent_rows = self._rows(
            self._g.query("MATCH (e:Entity) RETURN e.id, e.name, e.kind")
        )
        for row in ent_rows:
            if not row:
                continue
            eid = _scalar(row[0])
            if not isinstance(eid, str):
                continue
            g.add_node(
                eid,
                name=_scalar(row[1]) if len(row) > 1 else eid,
                kind=_scalar(row[2]) if len(row) > 2 else "",
            )

        edge_rows = self._rows(
            self._g.query(
                "MATCH (a:Entity)-[r:R]->(b:Entity) RETURN a.id, b.id, r.kind, r.confidence"
            )
        )
        for row in edge_rows:
            if not row or len(row) < 4:
                continue
            src = _scalar(row[0])
            dst = _scalar(row[1])
            kind = _scalar(row[2])
            conf = _scalar(row[3])
            if isinstance(src, str) and isinstance(dst, str):
                g.add_edge(
                    src, dst, kind=str(kind or ""), confidence=float(conf or 0.0)
                )
        return g

    # --- low-level helpers (kept on the class for back-compat) --------------

    @staticmethod
    def _rows(result: list[Any]) -> list[list[Any]]:
        """Compat alias: delegates to :func:`_helpers._rows`."""
        return _rows(result)


_store: KnowledgeGraphStore | None = None


def get_kg_store() -> KnowledgeGraphStore:
    """Process-singleton store. Cheap; reuses the FalkorDB client pool."""
    global _store
    if _store is None:
        _store = KnowledgeGraphStore()
    return _store


__all__ = [
    "EntityRecord",
    "KnowledgeGraphStore",
    "RelationRecord",
    "TIER_AMBIGUOUS",
    "TIER_EXTRACTED",
    "TIER_INFERRED",
    "canonical_entity_id",
    "confidence_to_tier",
    "get_kg_store",
]
