"""Parent-section retrieval tests.

Verifica :func:`expand_to_parent_section` gating + behavior senza
hittare Qdrant reale.
"""

from __future__ import annotations

from typing import Any

import pytest


class _FakePoint:
    def __init__(
        self, pid: str, doc_id: str, heading: str, chunk_index: int, text: str
    ) -> None:
        self.id = pid
        self.payload = {
            "document_id": doc_id,
            "section_heading": heading,
            "chunk_index": chunk_index,
            "text": text,
        }


class _FakeQdrant:
    """Restituisce point fissi indipendentemente dal filter; il test poi
    ispeziona che il caller filtri correttamente per (doc_id, heading)."""

    def __init__(self, points: list[_FakePoint]) -> None:
        self.points = points
        self.calls: list[dict[str, Any]] = []

    def scroll(self, **kwargs: Any) -> tuple[list[_FakePoint], None]:
        self.calls.append(kwargs)
        return list(self.points), None


def test_disabled_returns_hits_unchanged(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("llm_wiki.config.PARENT_RETRIEVAL_ENABLED", False)
    from llm_wiki.vectorstore.expansions import expand_to_parent_section

    hits = [
        {
            "id": "p1",
            "point_id": "p1",
            "payload": {"document_id": "concepts/foo", "section_heading": "Casi d'uso"},
            "score": 0.9,
        }
    ]
    assert expand_to_parent_section(hits) == hits


def test_no_section_heading_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    """Hit senza section_heading → nessuno scroll, nessun extra."""
    monkeypatch.setattr("llm_wiki.config.PARENT_RETRIEVAL_ENABLED", True)
    monkeypatch.setattr("llm_wiki.config.PARENT_RETRIEVAL_MAX_EXTRA", 6)
    monkeypatch.setattr("llm_wiki.config.PARENT_RETRIEVAL_PER_HIT_CAP", 3)

    fake = _FakeQdrant(points=[])
    monkeypatch.setattr("llm_wiki.vectorstore.expansions.get_qdrant", lambda: fake)

    from llm_wiki.vectorstore.expansions import expand_to_parent_section

    hits = [
        {
            "id": "p1",
            "point_id": "p1",
            "payload": {"document_id": "concepts/foo", "section_heading": ""},
            "score": 0.9,
        }
    ]
    out = expand_to_parent_section(hits)
    assert out == hits
    assert fake.calls == []


def test_appends_siblings_sorted_by_chunk_index(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("llm_wiki.config.PARENT_RETRIEVAL_ENABLED", True)
    monkeypatch.setattr("llm_wiki.config.PARENT_RETRIEVAL_MAX_EXTRA", 6)
    monkeypatch.setattr("llm_wiki.config.PARENT_RETRIEVAL_PER_HIT_CAP", 3)

    # 3 sibling chunks in ordine arbitrario; il caller li sorta per chunk_index.
    siblings = [
        _FakePoint("p3", "concepts/foo", "Casi d'uso", 4, "caso b"),
        _FakePoint("p1", "concepts/foo", "Casi d'uso", 2, "header"),
        _FakePoint("p2", "concepts/foo", "Casi d'uso", 3, "caso a"),
    ]
    fake = _FakeQdrant(points=siblings)
    monkeypatch.setattr("llm_wiki.vectorstore.expansions.get_qdrant", lambda: fake)

    from llm_wiki.vectorstore.expansions import expand_to_parent_section

    # Hit originale = il chunk con chunk_index=2; restano 2 sibling nuovi.
    hits = [
        {
            "id": "p1",
            "point_id": "p1",
            "payload": {
                "document_id": "concepts/foo",
                "section_heading": "Casi d'uso",
                "chunk_index": 2,
            },
            "score": 0.9,
        }
    ]
    out = expand_to_parent_section(hits)
    # Original + 2 sibling (p1 escluso perché già presente).
    assert len(out) == 3
    extras = out[1:]
    assert all(e["via_parent_section"] is True for e in extras)
    # Ordinati per chunk_index (3 poi 4).
    assert [e["payload"]["chunk_index"] for e in extras] == [3, 4]
    assert [e["payload"]["text"] for e in extras] == ["caso a", "caso b"]


def test_per_hit_cap_respected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("llm_wiki.config.PARENT_RETRIEVAL_ENABLED", True)
    monkeypatch.setattr("llm_wiki.config.PARENT_RETRIEVAL_MAX_EXTRA", 10)
    monkeypatch.setattr("llm_wiki.config.PARENT_RETRIEVAL_PER_HIT_CAP", 1)

    siblings = [
        _FakePoint(f"p{i}", "concepts/foo", "Casi d'uso", i + 10, f"caso {i}")
        for i in range(5)
    ]
    monkeypatch.setattr(
        "llm_wiki.vectorstore.expansions.get_qdrant",
        lambda: _FakeQdrant(points=siblings),
    )

    from llm_wiki.vectorstore.expansions import expand_to_parent_section

    hits = [
        {
            "id": "seed",
            "point_id": "seed",
            "payload": {
                "document_id": "concepts/foo",
                "section_heading": "Casi d'uso",
                "chunk_index": 2,
            },
            "score": 0.9,
        }
    ]
    out = expand_to_parent_section(hits)
    # 1 seed + 1 sibling (cap=1)
    assert len(out) == 2


def test_global_max_extra_respected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("llm_wiki.config.PARENT_RETRIEVAL_ENABLED", True)
    monkeypatch.setattr("llm_wiki.config.PARENT_RETRIEVAL_MAX_EXTRA", 2)
    monkeypatch.setattr("llm_wiki.config.PARENT_RETRIEVAL_PER_HIT_CAP", 5)

    # Due section diverse, 5 sibling ciascuna — tetto globale 2 deve fermare.
    siblings = [
        _FakePoint(f"a{i}", "concepts/foo", "Sezione A", i + 10, f"a{i}")
        for i in range(5)
    ]
    monkeypatch.setattr(
        "llm_wiki.vectorstore.expansions.get_qdrant",
        lambda: _FakeQdrant(points=siblings),
    )

    from llm_wiki.vectorstore.expansions import expand_to_parent_section

    hits = [
        {
            "id": "seed1",
            "point_id": "seed1",
            "payload": {
                "document_id": "concepts/foo",
                "section_heading": "Sezione A",
                "chunk_index": 0,
            },
            "score": 0.9,
        },
        {
            "id": "seed2",
            "point_id": "seed2",
            "payload": {
                "document_id": "concepts/bar",
                "section_heading": "Sezione B",
                "chunk_index": 0,
            },
            "score": 0.8,
        },
    ]
    out = expand_to_parent_section(hits)
    # 2 seed + max 2 extras totali.
    assert len(out) == 4
    extras = [h for h in out if h.get("via_parent_section")]
    assert len(extras) == 2


def test_duplicate_section_explored_once(monkeypatch: pytest.MonkeyPatch) -> None:
    """Due hit nella stessa (doc_id, section) → scroll una volta sola."""
    monkeypatch.setattr("llm_wiki.config.PARENT_RETRIEVAL_ENABLED", True)
    monkeypatch.setattr("llm_wiki.config.PARENT_RETRIEVAL_MAX_EXTRA", 6)
    monkeypatch.setattr("llm_wiki.config.PARENT_RETRIEVAL_PER_HIT_CAP", 3)

    fake = _FakeQdrant(points=[])
    monkeypatch.setattr("llm_wiki.vectorstore.expansions.get_qdrant", lambda: fake)

    from llm_wiki.vectorstore.expansions import expand_to_parent_section

    hits = [
        {
            "id": "h1",
            "point_id": "h1",
            "payload": {
                "document_id": "concepts/foo",
                "section_heading": "Casi d'uso",
                "chunk_index": 2,
            },
            "score": 0.9,
        },
        {
            "id": "h2",
            "point_id": "h2",
            "payload": {
                "document_id": "concepts/foo",
                "section_heading": "Casi d'uso",
                "chunk_index": 3,
            },
            "score": 0.8,
        },
    ]
    expand_to_parent_section(hits)
    assert len(fake.calls) == 1


def test_qdrant_unavailable_returns_hits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("llm_wiki.config.PARENT_RETRIEVAL_ENABLED", True)
    monkeypatch.setattr("llm_wiki.vectorstore.expansions.get_qdrant", lambda: None)

    from llm_wiki.vectorstore.expansions import expand_to_parent_section

    hits = [
        {
            "id": "h1",
            "payload": {"document_id": "x", "section_heading": "H"},
            "score": 0.9,
        }
    ]
    assert expand_to_parent_section(hits) == hits


def test_scroll_exception_skips_hit(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("llm_wiki.config.PARENT_RETRIEVAL_ENABLED", True)
    monkeypatch.setattr("llm_wiki.config.PARENT_RETRIEVAL_MAX_EXTRA", 6)
    monkeypatch.setattr("llm_wiki.config.PARENT_RETRIEVAL_PER_HIT_CAP", 3)

    class _Boom:
        def scroll(self, **_kw: Any) -> tuple[list[Any], None]:
            raise RuntimeError("qdrant down")

    monkeypatch.setattr("llm_wiki.vectorstore.expansions.get_qdrant", lambda: _Boom())

    from llm_wiki.vectorstore.expansions import expand_to_parent_section

    hits = [
        {
            "id": "h1",
            "payload": {"document_id": "x", "section_heading": "H"},
            "score": 0.9,
        }
    ]
    out = expand_to_parent_section(hits)
    assert out == hits
