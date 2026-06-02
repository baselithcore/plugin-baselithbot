"""Espansioni e fusione di hits di retrieval.

Estratto da :mod:`llm_wiki.vectorstore.core`. Funzioni pure che operano
su liste di dict ``hit`` — niente I/O salvo:
- ``expand_with_rinvii`` legge Qdrant via ``scroll`` per recuperare chunk
  citati;
- ``expand_to_parent_section`` idem per i sibling chunk della sezione;
- ``expand_with_graph`` / ``expand_with_entity_graph`` leggono il
  graphdb Falkor per arricchire i payload.

Tutte le funzioni sono fallback-safe: in caso di errore restituiscono
``hits`` invariato.

Modular layout (>500 LOC budget):
- :mod:`.rrf`            — Reciprocal Rank Fusion + edizione mix annotation
- :mod:`.rinvii`         — follow-the-link cited-article expansion
- :mod:`.parent_section` — small-to-big sibling chunk fetch
- :mod:`.graph`          — wikilink + entity-graph fan-out

``get_qdrant`` è re-esportato qui in modo che i test possano
``monkeypatch.setattr("llm_wiki.vectorstore.expansions.get_qdrant", …)``
e tutti i submoduli (che fanno lookup lazy via questo namespace) lo
intercettino.
"""

from __future__ import annotations

from llm_wiki.vectorstore.expansions.graph import (
    expand_with_entity_graph,
    expand_with_graph,
)
from llm_wiki.vectorstore.expansions.parent_section import expand_to_parent_section
from llm_wiki.vectorstore.expansions.rinvii import expand_with_rinvii
from llm_wiki.vectorstore.expansions.rrf import (
    _extract_edizione,  # noqa: F401 — back-compat re-export
    annotate_mix_edizioni,
    merge_hits_rrf,
)
from llm_wiki.vectorstore.qdrant_ops import get_qdrant

__all__ = [
    "annotate_mix_edizioni",
    "expand_to_parent_section",
    "expand_with_entity_graph",
    "expand_with_graph",
    "expand_with_rinvii",
    "get_qdrant",
    "merge_hits_rrf",
]
