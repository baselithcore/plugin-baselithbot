"""Test della provenance puntuale (section_path + anchor) sui chunk.

Garantisce che, dato un markdown wiki con heading annidati, l'output del
chunker sia accompagnato da:

- ``section_paths_for_chunks(text, chunks)`` con breadcrumb corretti per
  ogni chunk (heading più profondo che lo contiene);
- ``slug_anchor(heading)`` normalizzazione case-insensitive coerente con
  i parser markdown comuni.

Senza questa coppia, il payload Qdrant perderebbe la possibilità di
emettere `Cita come: [[doc#anchor]]` nel CONTESTO del RAG: la
citazione tornerebbe generica e l'utente non potrebbe verificare il
claim in un click.
"""

from __future__ import annotations

from llm_wiki.vectorstore.chunking import (
    build_section_index,
    chunk_markdown,
    section_paths_for_chunks,
    slug_anchor,
)


def test_slug_anchor_normalises_spaces_and_case() -> None:
    assert slug_anchor("Roadmap Strategica") == "roadmap-strategica"
    assert slug_anchor("  Industry Leaders  ") == "industry-leaders"
    assert slug_anchor("Punto 3.1") == "punto-31"
    assert slug_anchor("") == ""


def test_build_section_index_tracks_breadcrumb() -> None:
    text = (
        "## Capitolo Uno\n"
        "Contenuto introduttivo del capitolo uno.\n"
        "### Sotto-sezione A\n"
        "Dettaglio A.\n"
        "## Capitolo Due\n"
        "Contenuto del capitolo due.\n"
    )
    index = build_section_index(text)
    # Linea iniziale (offset 0) entra subito sotto "Capitolo Uno"
    assert index[0][1] == ["Capitolo Uno"]
    # Riga di "Sotto-sezione A" estende il breadcrumb
    sub_entry = next(p for off, p in index if p == ["Capitolo Uno", "Sotto-sezione A"])
    assert sub_entry == ["Capitolo Uno", "Sotto-sezione A"]
    # Capitolo Due resetta il livello 3
    cap_due = next(p for off, p in index if p == ["Capitolo Due"])
    assert cap_due == ["Capitolo Due"]


def test_section_paths_align_with_chunks() -> None:
    # Documento abbastanza grande da forzare lo splitter a produrre
    # >1 chunk. Le sezioni sono volutamente verbose così che ogni
    # heading di livello 2 generi il proprio chunk separato.
    intro_body = "Paragrafo introduttivo del documento. " * 30
    road_body = "Descrizione della roadmap strategica. " * 30
    pilota_body = "Selezione del champion e KPI di successo. " * 30
    gov_body = "Modello di governance condivisa fra IT e business. " * 30
    text = (
        "# Titolo pagina\n\n"
        "## Introduzione\n\n"
        f"{intro_body}\n\n"
        "## Roadmap strategica\n\n"
        f"{road_body}\n\n"
        "### Fase pilota\n\n"
        f"{pilota_body}\n\n"
        "## Governance\n\n"
        f"{gov_body}\n"
    )
    chunks = chunk_markdown(text)
    assert len(chunks) >= 2, "il chunker deve spezzare il documento in più chunk"

    paths = section_paths_for_chunks(text, chunks)
    assert len(paths) == len(chunks)

    flat_paths = [tuple(p) for p in paths]
    # Almeno un chunk deve essere ancorato a "Roadmap strategica".
    assert any("Roadmap strategica" in p for p in flat_paths)
    # Almeno un chunk deve risultare annidato sotto "Fase pilota".
    assert any(p and p[-1] == "Fase pilota" for p in flat_paths)


def test_section_paths_empty_when_no_headings() -> None:
    text = "Solo prosa, niente heading markdown, due paragrafi.\n\nAltro paragrafo."
    chunks = chunk_markdown(text)
    paths = section_paths_for_chunks(text, chunks)
    assert all(p == [] for p in paths)
