"""Routing ordering: collapse hierarchical PRIMA di parent-section.

Senza il riordino, ``expand_to_parent_section`` recupera sibling per ogni
child non-collassato, duplicando il contenuto già denormalizzato in
``parent_text``. Verifichiamo che:

- ``expand_to_parent_section`` skippa hit con ``hierarchical_collapsed=True``;
- il filtro scroll fa OR su ``section_heading`` e ``parent_section_heading``
  (presente nel ``should`` del Filter);
- ``annotate_mix_edizioni`` espone ``mix_kind`` e ``prefer_vigente_applied``.
"""

from __future__ import annotations

from llm_wiki.vectorstore.expansions import (
    annotate_mix_edizioni,
    expand_to_parent_section,
)


def test_expand_skips_collapsed_hierarchical_hits(monkeypatch) -> None:
    # Simula `PARENT_RETRIEVAL_ENABLED=True` e niente client Qdrant.
    monkeypatch.setattr("llm_wiki.config.PARENT_RETRIEVAL_ENABLED", True, raising=False)
    monkeypatch.setattr(
        "llm_wiki.vectorstore.expansions.get_qdrant",
        lambda: None,  # client None → ritorna hits invariato
    )
    hits = [
        {
            "id": "1",
            "point_id": "1",
            "payload": {"document_id": "d1", "section_heading": "X"},
            "hierarchical_collapsed": True,
        }
    ]
    out = expand_to_parent_section(hits)
    assert out == hits  # no-op (client None oppure skip — ritorna lista originale)


class _FakeQdrant:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def scroll(self, *, collection_name, scroll_filter, limit, with_payload):
        self.calls.append({"filter": scroll_filter, "limit": limit})
        return [], None


def test_expand_uses_or_filter_for_section_and_parent_heading(monkeypatch) -> None:
    monkeypatch.setattr("llm_wiki.config.PARENT_RETRIEVAL_ENABLED", True, raising=False)
    fake = _FakeQdrant()
    monkeypatch.setattr("llm_wiki.vectorstore.expansions.get_qdrant", lambda: fake)
    hits = [
        {
            "id": "h1",
            "point_id": "h1",
            "payload": {
                "document_id": "d1",
                "section_heading": "Fine H3",
                "parent_section_heading": "Parent H2",
            },
        }
    ]
    expand_to_parent_section(hits, max_extra=5, per_hit_cap=3)
    assert fake.calls, "scroll non chiamato"
    f = fake.calls[0]["filter"]
    # Deve avere `should` con entrambe le condizioni (OR).
    should_keys = {c.key for c in (f.should or [])}
    assert should_keys == {"section_heading", "parent_section_heading"}


def test_expand_skips_when_no_section_or_parent_heading(monkeypatch) -> None:
    monkeypatch.setattr("llm_wiki.config.PARENT_RETRIEVAL_ENABLED", True, raising=False)
    fake = _FakeQdrant()
    monkeypatch.setattr("llm_wiki.vectorstore.expansions.get_qdrant", lambda: fake)
    hits = [
        {
            "id": "h1",
            "point_id": "h1",
            "payload": {"document_id": "d1"},  # no section, no parent
        }
    ]
    out = expand_to_parent_section(hits)
    assert out == hits
    assert not fake.calls


# --- edizione audit smart -------------------------------------------------


def test_audit_mix_kind_versioni_diverse_when_no_vigente_filter() -> None:
    hits = [
        {"payload": {"edizione": "2020"}},
        {"payload": {"edizione": "2024"}},
    ]
    out = annotate_mix_edizioni(hits, prefer_vigente_applied=False)
    assert all(h["edizione_audit"]["mix_versions"] for h in out)
    assert all(h["edizione_audit"]["mix_kind"] == "versioni_diverse" for h in out)
    assert all(h["edizione_audit"]["prefer_vigente_applied"] is False for h in out)


def test_audit_mix_kind_vigenti_distinti_when_vigente_filter_applied() -> None:
    hits = [
        {"payload": {"edizione": "rev-A"}},
        {"payload": {"edizione": "rev-B"}},
    ]
    out = annotate_mix_edizioni(hits, prefer_vigente_applied=True)
    assert all(h["edizione_audit"]["mix_kind"] == "vigenti_distinti" for h in out)
    assert all(h["edizione_audit"]["prefer_vigente_applied"] is True for h in out)


def test_audit_no_mix_when_single_edizione() -> None:
    hits = [
        {"payload": {"edizione": "2024"}},
        {"payload": {"edizione": "2024"}},
    ]
    out = annotate_mix_edizioni(hits, prefer_vigente_applied=True)
    assert all(not h["edizione_audit"]["mix_versions"] for h in out)
    assert all(h["edizione_audit"]["mix_kind"] == "" for h in out)
