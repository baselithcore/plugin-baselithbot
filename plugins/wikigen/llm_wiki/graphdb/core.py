"""Knowledge Graph opzionale su FalkorDB/RedisGraph.

Il grafo modella:
- Nodi `(:Page {id, title, type, category, tags, source_file})` per ogni pagina wiki
- Archi `(:Page)-[:LINKS_TO]->(:Page)` derivati dai wikilinks
- Archi `(:Page)-[:CITES_SOURCE]->(:Page {type:'source'})` quando una pagina
  richiama esplicitamente una fonte (tipicamente via wikilink a `wiki/sources/`)

Quando `GRAPH_DB_ENABLED=false` o `falkordb/redis` non sono installati,
tutte le API sono no-op.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from llm_wiki.config import (
    GRAPH_DB_ENABLED,
    GRAPH_DB_NAME,
    GRAPH_DB_TIMEOUT,
    GRAPH_DB_URL,
)

logger = logging.getLogger(__name__)


class GraphDb:
    def __init__(
        self,
        *,
        enabled: bool = GRAPH_DB_ENABLED,
        url: str = GRAPH_DB_URL,
        name: str = GRAPH_DB_NAME,
        timeout: float = GRAPH_DB_TIMEOUT,
    ) -> None:
        self.enabled = enabled
        self.name = name
        self._url = url
        self._timeout = timeout
        self._client: Any | None = None

    def is_enabled(self) -> bool:
        if not self.enabled:
            return False
        try:
            return self._get_client() is not None
        except Exception:
            return False

    def _get_client(self) -> Any:
        if self._client is not None:
            return self._client
        try:
            from redis import Redis  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeError(
                "`redis` non installato. `pip install redis falkordb`."
            ) from exc
        self._client = Redis.from_url(
            self._url, socket_timeout=self._timeout, decode_responses=True
        )
        return self._client

    def ping(self) -> bool:
        if not self.enabled:
            return False
        try:
            return bool(self._get_client().ping())
        except Exception as exc:
            logger.warning("[graphdb] ping fallito: %s", exc)
            return False

    # --- core query helpers -------------------------------------------------

    def query(self, cypher: str, params: Mapping[str, Any] | None = None) -> list[Any]:
        if not self.enabled:
            return []
        try:
            client = self._get_client()
            expanded = _inline_params(cypher, params or {})
            result = client.execute_command(
                "GRAPH.QUERY", self.name, expanded, "--compact"
            )
            return list(result) if isinstance(result, list | tuple) else []
        except Exception as exc:
            logger.debug("[graphdb] query fallita: %s", exc)
            return []

    # --- wiki-specific ops --------------------------------------------------

    def create_indexes(self) -> None:
        if not self.enabled:
            return
        for stmt in (
            "CREATE INDEX FOR (p:Page) ON (p.id)",
            "CREATE INDEX FOR (p:Page) ON (p.type)",
        ):
            try:
                self._get_client().execute_command("GRAPH.QUERY", self.name, stmt)
            except Exception:
                pass

    def upsert_page(
        self,
        page_id: str,
        *,
        title: str | None = None,
        page_type: str | None = None,
        category: str | None = None,
        tags: list[str] | None = None,
        source_file: str | None = None,
    ) -> None:
        if not self.enabled:
            return
        props = {
            "id": page_id,
            "title": title or page_id,
            "type": page_type or "unknown",
            "category": category or "",
            "tags": ",".join(tags or []),
            "source_file": source_file or "",
        }
        cypher = (
            "MERGE (p:Page {id: $id}) "
            "SET p.title = $title, p.type = $type, p.category = $category, "
            "    p.tags = $tags, p.source_file = $source_file"
        )
        self.query(cypher, props)

    def link_pages(self, source_id: str, target_id: str, rel: str = "LINKS_TO") -> None:
        if not self.enabled:
            return
        cypher = f"MATCH (a:Page {{id: $source}}), (b:Page {{id: $target}}) MERGE (a)-[:{rel}]->(b)"
        self.query(cypher, {"source": source_id, "target": target_id})

    def delete_page(self, page_id: str) -> None:
        if not self.enabled:
            return
        self.query("MATCH (p:Page {id: $id}) DETACH DELETE p", {"id": page_id})

    def stats(self) -> dict[str, int]:
        if not self.enabled:
            return {"nodes": 0, "edges": 0}
        try:
            n = self.query("MATCH (n) RETURN count(n)")
            e = self.query("MATCH ()-[r]->() RETURN count(r)")
            return {"nodes": _extract_count(n), "edges": _extract_count(e)}
        except Exception:
            return {"nodes": 0, "edges": 0}


def _inline_params(cypher: str, params: Mapping[str, Any]) -> str:
    """Sostituzione parametri $key → letterale Cypher-safe.

    FalkorDB accetta parametri come prefisso `CYPHER key=... query` ma la forma
    inline è più leggera e sufficiente per workload wiki (pochi nodi, scrittura
    controllata lato codice).
    """
    out = cypher
    for key, value in params.items():
        out = out.replace(f"${key}", _encode(value))
    return out


def _encode(value: Any) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int | float):
        return str(value)
    if isinstance(value, list):
        return "[" + ",".join(_encode(v) for v in value) + "]"
    s = str(value).replace("\\", "\\\\").replace("'", "\\'")
    return f"'{s}'"


def _extract_count(res: list[Any]) -> int:
    try:
        if len(res) > 1 and res[1]:
            val: Any = res[1][0][0]
            if isinstance(val, list) and len(val) >= 2:
                return int(val[1])  # type: ignore[arg-type]
            return int(val)  # type: ignore[arg-type]
    except Exception:
        pass
    return 0


_graph_db: GraphDb | None = None


def get_graph_db() -> GraphDb:
    global _graph_db
    if _graph_db is None:
        _graph_db = GraphDb()
    return _graph_db


__all__ = ["GraphDb", "get_graph_db"]
