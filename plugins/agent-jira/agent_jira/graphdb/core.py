"""
Core GraphDB client class for FalkorDB/RedisGraph.

Provides the main GraphDb client with initialization, connection management,
and delegation to specialized operation modules.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Mapping, Optional, Sequence

from agent_jira.cache import RedisTTLCache, TTLCache, create_redis_client
from agent_jira.cost_control import cost_controller
from agent_jira.tenant_context import get_tenant_cache_prefix

# Import specialized modules
from agent_jira.graphdb import code_graph, linking, operations, query_builder, retrieval
from agent_jira.config import (
    CACHE_BACKEND,
    CACHE_REDIS_PREFIX,
    CACHE_REDIS_URL,
    GRAPH_CACHE_TTL,
    GRAPH_DB_CREATE_CONSTRAINTS,
    GRAPH_DB_ENABLED,
    GRAPH_DB_NAME,
    GRAPH_DB_TIMEOUT,
    GRAPH_DB_URL,
)

try:  # pragma: no cover - optional dependency
    from redis import Redis
except Exception:  # pragma: no cover - redis not available
    Redis = None  # type: ignore[arg-type]

logger = logging.getLogger(__name__)


class GraphDb:
    """Lightweight client for FalkorDB/RedisGraph with minimal and safe-by-default API."""

    def __init__(
        self,
        *,
        enabled: bool = GRAPH_DB_ENABLED,
        url: str = GRAPH_DB_URL,
        graph_name: str = GRAPH_DB_NAME,
        timeout: float = GRAPH_DB_TIMEOUT,
    ) -> None:
        self.enabled = enabled
        self.graph_name = graph_name
        self._url = url
        self._timeout = timeout
        self._client: "Redis | None" = None

        # Initialize Cache
        self._cache = None
        if self.enabled:
            try:
                if CACHE_BACKEND == "redis":
                    redis_client = create_redis_client(CACHE_REDIS_URL)
                    self._cache = RedisTTLCache(
                        redis_client,
                        prefix=get_tenant_cache_prefix(f"{CACHE_REDIS_PREFIX}:graph"),
                        default_ttl=GRAPH_CACHE_TTL,
                    )
                else:
                    self._cache = TTLCache(maxsize=1024, ttl=GRAPH_CACHE_TTL)
            except Exception as e:
                logger.warning(f"[graphdb] Failed to initialize cache: {e}")

    def is_enabled(self) -> bool:
        """Check if graph database is enabled."""
        return bool(self.enabled)

    def ping(self) -> bool:
        """
        Verify backend reachability without altering state.

        Returns:
            True if backend is reachable, False otherwise
        """
        if not self.enabled:
            return False
        try:
            self._get_client().ping()
            return True
        except Exception as exc:  # pragma: no cover - diagnostic log
            logger.warning("[graphdb] ping failed: %s", exc)
            return False

    def create_constraints(self) -> None:
        """
        Create uniqueness constraints for main labels.
        Idempotent operation (errors are handled/ignored if constraint already exists).
        """
        if not self.enabled:
            return

        unique_specs = [
            ("Document", "id"),
            ("Story", "id"),
            ("Epic", "id"),
            ("TestCase", "id"),
            ("Requirement", "id"),
            ("JiraIssue", "id"),
            ("Topic", "id"),
            ("Technology", "id"),
            ("Stakeholder", "id"),
            ("Milestone", "id"),
            ("Risk", "id"),
        ]
        index_specs = [
            ("Document", "id"),
            ("Story", "id"),
            ("Epic", "id"),
            ("TestCase", "id"),
            ("Requirement", "id"),
            ("JiraIssue", "id"),
            ("Topic", "id"),
            ("Technology", "id"),
            ("Stakeholder", "id"),
            ("Milestone", "id"),
            ("Risk", "id"),
            ("Topic", "source_document_id"),
            ("Technology", "source_document_id"),
            ("Stakeholder", "source_document_id"),
            ("Milestone", "source_document_id"),
            ("Risk", "source_document_id"),
            ("Topic", "entity_key"),
            ("Technology", "entity_key"),
            ("Stakeholder", "entity_key"),
            ("Milestone", "entity_key"),
            ("Risk", "entity_key"),
        ]

        client = self._get_client()
        for label, field in index_specs:
            # 1. Create index (idempotent)
            try:
                client.execute_command(
                    "GRAPH.QUERY",
                    self.graph_name,
                    f"CREATE INDEX FOR (n:{label}) ON (n.{field})",
                )
            except Exception as e:
                # If index already exists, might give error. Ignore if "already indexed".
                msg = str(e)
                if "already indexed" not in msg and "already exists" not in msg:
                    logger.warning(
                        f"[graphdb] Error creating index {label}({field}): {msg}"
                    )

        if not GRAPH_DB_CREATE_CONSTRAINTS:
            logger.info(
                "[graphdb] Unique constraints disabled via GRAPH_DB_CREATE_CONSTRAINTS=false; keeping indexes only."
            )
            return

        for label, field in unique_specs:
            try:
                client.execute_command(
                    "GRAPH.CONSTRAINT",
                    "CREATE",
                    self.graph_name,
                    "UNIQUE",
                    "NODE",
                    label,
                    "PROPERTIES",
                    1,
                    field,
                )
                logger.info(f"[graphdb] Constraint created/verified: {label}({field})")
            except Exception as e:
                # E.g. "Constraint already exists"
                msg = str(e)
                if "already exists" not in msg:
                    logger.warning(
                        f"[graphdb] Error creating constraint {label}: {msg}"
                    )

    def query(self, cypher: str, params: Mapping[str, Any] | None = None) -> list[Any]:
        """
        Execute a Cypher query and return the raw Redis payload.

        Uses parameters with CYPHER prefix to avoid unsafe string concatenation.
        Returns empty list if graph is disabled.

        Args:
            cypher: Cypher query string
            params: Optional query parameters

        Returns:
            Query result list
        """
        if not self.enabled:
            logger.debug("[graphdb] query ignored because disabled")
            return []

        # Track & Validate cost
        cost_controller.track_query(cypher)

        # Cache Check (Read-Only Heuristic)
        # Only cache if query doesn't modify data
        upper_cypher = cypher.upper()
        is_read_only = not any(
            kw in upper_cypher
            for kw in [
                "CREATE",
                "MERGE",
                "SET",
                "DELETE",
                "DETACH",
                "REMOVE",
                "DROP",
                "CALL",
            ]
        )

        cache_key = None
        if is_read_only and self._cache:
            # Create a deterministic key from cypher and params
            key_parts = [cypher]
            if params:
                for k in sorted(params.keys()):
                    key_parts.append(f"{k}={params[k]}")
            cache_key = "|".join(key_parts)

            cached = self._cache.get(cache_key)
            if cached is not None:
                # logger.debug("[graphdb] cache hit") # verbose
                return cached

        query_text = query_builder.build_query(cypher, params or {})
        client = self._get_client()
        result = client.execute_command(  # type: ignore[union-attr]
            "GRAPH.QUERY",
            self.graph_name,
            query_text,
            "--compact",
        )

        # Cache Set
        if is_read_only and self._cache and cache_key:
            self._cache.set(cache_key, result)

        return result

    # --- Node & Edge Operations (delegated to operations module) ---

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve node properties by ID."""
        if not self.enabled:
            return None
        return operations.get_node(self.query, node_id)

    def upsert_node(
        self,
        node_id: str,
        *,
        labels: Sequence[str] | None = None,
        properties: Mapping[str, Any] | None = None,
    ) -> None:
        """Create or update a node with stable ID and mergeable properties."""
        if not self.enabled:
            return
        operations.upsert_node(
            self.query, node_id, labels=labels, properties=properties
        )

    def upsert_edge(
        self,
        source_id: str,
        relationship: str,
        target_id: str,
        *,
        properties: Mapping[str, Any] | None = None,
    ) -> None:
        """Create or update a directed relationship between two nodes."""
        if not self.enabled:
            return
        operations.upsert_edge(
            self.query, source_id, relationship, target_id, properties=properties
        )

    def delete_node(self, node_id: str) -> None:
        """Delete a node and all its incident relationships."""
        if not self.enabled:
            return
        operations.delete_node(self.query, node_id)

    def delete_orphan_nodes(self) -> int:
        """
        Delete orphan nodes (without relationships) from the graph.
        Explicitly excludes Document nodes for safety.

        Returns:
            Number of nodes deleted
        """
        if not self.enabled:
            return 0
        return operations.delete_orphan_nodes(self.query)

    # --- Linking Operations (delegated to linking module) ---

    def link_story_to_doc(
        self,
        story_id: str,
        doc_id: str,
        *,
        title: Optional[str] = None,
        priority: Optional[str] = None,
        status: Optional[str] = None,
    ) -> None:
        """Link a user story to a knowledge base document."""
        if not self.enabled:
            return
        linking.link_story_to_doc(
            self.upsert_node,
            self.upsert_edge,
            story_id,
            doc_id,
            title=title,
            priority=priority,
            status=status,
        )

    def link_story_to_jira(
        self,
        story_id: str,
        *,
        issue_key: Optional[str] = None,
        issue_status: Optional[str] = None,
        issue_url: Optional[str] = None,
    ) -> None:
        """Link a story to a Jira issue, creating the issue node if necessary."""
        if not self.enabled:
            return
        linking.link_story_to_jira(
            self.upsert_node,
            self.upsert_edge,
            story_id,
            issue_key=issue_key,
            issue_status=issue_status,
            issue_url=issue_url,
        )

    def get_linked_jiras(self, doc_id: str) -> list[dict[str, Any]]:
        """
        Retrieve Jira issues linked to a specific document.

        Returns:
            List of dicts with keys: key, status, url, summary
        """
        if not self.enabled:
            return []
        return linking.get_linked_jiras(self.query, doc_id)

    def get_document_subgraph(self, doc_id: str) -> dict[str, Any]:
        """
        Retrieve the subgraph (neighborhood) for a given document.

        Args:
            doc_id: The document ID (or KB path).

        Returns:
            Dict with 'nodes' and 'links' for visualization.
        """
        if not self.enabled:
            return {"nodes": [], "links": []}
        return retrieval.get_subgraph_for_node(self.query, doc_id)

    def search_node(self, prop: str, value: str) -> Optional[str]:
        """Cerca un nodo per proprietà."""
        if not self.enabled:
            return None
        return retrieval.search_node_by_property(self.query, prop, value)

    def record_document_feedback(
        self, document_id: str, feedback: str, comment: Optional[str] = None
    ) -> None:
        """
        Update feedback counters on a Document node.

        Args:
            document_id: Document identifier
            feedback: Feedback sentiment ("positive" or "negative")
            comment: Optional feedback comment
        """
        if not self.enabled:
            return
        linking.record_document_feedback(self.query, document_id, feedback, comment)

    # --- Code Graph Operations (delegated to code_graph module) ---

    def upsert_code_node(
        self,
        node_id: str,
        label: str,
        name: str,
        file_path: str,
        *,
        properties: Mapping[str, Any] | None = None,
    ) -> None:
        """Create or update a node representing a code entity (File, Class, Function)."""
        if not self.enabled:
            return
        code_graph.upsert_code_node(
            self.upsert_node, node_id, label, name, file_path, properties=properties
        )

    def upsert_code_relation(
        self,
        source_id: str,
        relation_type: str,
        target_id: str,
    ) -> None:
        """Create a relationship between two code components (e.g., DEFINES, CONTAINS)."""
        if not self.enabled:
            return
        code_graph.upsert_code_relation(
            self.upsert_edge, source_id, relation_type, target_id
        )

    # --- Internals ---

    def close(self) -> None:
        """Close the Redis connection if it exists."""
        if self._client:
            try:
                self._client.close()
            except Exception as e:
                logger.warning(f"[graphdb] Error closing connection: {e}")
            finally:
                self._client = None

    def _get_client(self) -> "Redis":
        """Get or create Redis client connection."""
        if not self.enabled:
            raise RuntimeError("GraphDB not enabled (GRAPH_DB_ENABLED=false)")
        if Redis is None:
            raise RuntimeError(
                "GraphDB requires the redis package; install it to enable."
            )
        if self._client is None:
            self._client = Redis.from_url(
                self._url,
                socket_timeout=self._timeout,
                decode_responses=True,
                max_connections=50,
            )
        return self._client


# Singleton instance, ready to use but lazy: doesn't open connection until needed.
graph_db = GraphDb()

__all__ = ["GraphDb", "graph_db"]
