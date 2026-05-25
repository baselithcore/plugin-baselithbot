# app/vectorstore/__init__.py
"""
Vectorstore package for document indexing and search.

This package provides a modular architecture for managing document indexing,
chunking, embedding, and retrieval using Qdrant vector database with optional
graph database synchronization.

Public API:
    - index_docs: Index documents from configured sources
    - search: Search for documents using vector similarity
    - create_collection: Create Qdrant collection
    - list_indexed_documents: List all indexed documents
    - indexed_items: Dictionary of indexed document metadata
    - INDEX_SCROLL_PAGE_SIZE: Page size for Qdrant scroll operations
    - _refresh_indexed_items: Refresh indexed items from Qdrant (internal)
"""

from __future__ import annotations

from typing import Any

from agent_jira.vectorstore.state import (
    _refresh_indexed_items,
    indexed_items,
    list_indexed_documents,
)


def index_docs(*args: Any, **kwargs: Any):
    from agent_jira.vectorstore.indexing import index_docs as _index_docs

    return _index_docs(*args, **kwargs)


def search(*args: Any, **kwargs: Any):
    from agent_jira.vectorstore.indexing import search as _search

    return _search(*args, **kwargs)


def create_collection(*args: Any, **kwargs: Any):
    from agent_jira.vectorstore.qdrant_ops import (
        create_collection as _create_collection,
    )

    return _create_collection(*args, **kwargs)


def __getattr__(name: str):
    if name == "INDEX_SCROLL_PAGE_SIZE":
        from agent_jira.vectorstore.qdrant_ops import INDEX_SCROLL_PAGE_SIZE

        return INDEX_SCROLL_PAGE_SIZE
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "index_docs",
    "search",
    "create_collection",
    "list_indexed_documents",
    "indexed_items",
    "INDEX_SCROLL_PAGE_SIZE",
    "_refresh_indexed_items",
]
