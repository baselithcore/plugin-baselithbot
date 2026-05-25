"""User-memories storage facade — Postgres metadata + Qdrant vectors.

Entry point: :class:`MemoriesStore` (singleton via :func:`get_memories_store`).
"""

from llm_wiki.memories.store import MemoriesStore, get_memories_store

__all__ = ["MemoriesStore", "get_memories_store"]
