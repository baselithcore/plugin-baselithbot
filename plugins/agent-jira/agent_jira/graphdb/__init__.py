"""
GraphDB package - FalkorDB/RedisGraph integration.

This package provides a modular, maintainable structure for graph database operations.

Modules:
- core: Main GraphDb client class
- operations: Basic node and edge CRUD operations
- linking: Domain-specific linking helpers (stories, Jira, documents)
- code_graph: Code graph specialized operations
- query_builder: Query construction and parameter encoding utilities

For backward compatibility, the main public API is re-exported here.
"""

from agent_jira.graphdb.core import GraphDb, graph_db

__all__ = ["GraphDb", "graph_db"]
