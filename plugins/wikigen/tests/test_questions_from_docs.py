"""Doc-grounded starter-question generator — orchestrator + sampler tests.

The LLM call itself is monkeypatched: these tests pin the orchestration
contract (marker idempotency, fallback-safety on LLM failure, pack.yaml
patching, sampler folder ordering) rather than re-validating prompt
output (covered by ``test_prompt_synthesizer.py`` for the analogous
synth-time path).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from llm_wiki.admin import questions_from_docs as qfd
from llm_wiki.admin.prompt_synthesizer.models import (
    SuggestedQuestion,
    SynthesisError,
)
from llm_wiki.admin.questions_from_docs import _sampler


def _write_page(folder: Path, name: str, title: str, body: str) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    page = folder / name
    fm = f"---\ntitle: {title}\n---\n\n"
    page.write_text(fm + body, encoding="utf-8")
    return page


def _make_pack(tmp_path: Path) -> tuple[Path, Path]:
    """Scaffold a minimal pack_dir + wiki_dir layout for tests."""
    pack_dir = tmp_path / "pack"
    wiki_dir = tmp_path / "vault" / "wiki"
    (pack_dir / "prompts").mkdir(parents=True)
    pack_yaml = pack_dir / "pack.yaml"
    pack_yaml.write_text(
        yaml.safe_dump(
            {
                "name": "demo",
                "label": "Wiki Demo",
                "description": "Demo per i test.",
                "language": "it",
                "page_types": [
                    {
                        "id": "source",
                        "label": "Fonte",
                        "plural": "fonti",
                        "folder": "sources",
                    },
                    {
                        "id": "concept",
                        "label": "Concetto",
                        "plural": "concetti",
                        "folder": "concepts",
                    },
                ],
                "ui": {"app_name": "Wiki Demo", "disclaimer": "Demo disclaimer."},
            },
            sort_keys=False,
            allow_unicode=True,
        ),
        encoding="utf-8",
    )
    _write_page(
        wiki_dir / "sources",
        "guida-base.md",
        "Guida base alla piattaforma",
        "## Introduzione\n\nQuesto è il contenuto della guida base.\n\n"
        "Riferimento a [[concepts/architettura]].\n",
    )
    _write_page(
        wiki_dir / "concepts",
        "architettura.md",
        "Architettura del sistema",
        "## Componenti\n\nIl sistema è suddiviso in tre livelli.\n",
    )
    return pack_dir, wiki_dir


def _valid_questions() -> list[dict[str, str]]:
    return [
        {
            "category": "definizione",
            "label": "Architettura",
            "hint": "Componenti del sistema",
            "icon": "Lightbulb",
            "prompt": "Quali sono i tre livelli dell'architettura descritta nella guida?",
        },
        {
            "category": "panoramica",
            "label": "Guida base",
            "hint": "Inizia da qui",
            "icon": "BookOpen",
            "prompt": "Cosa contiene la guida base alla piattaforma e da dove conviene iniziare?",
        },
        {
            "category": "confronto",
            "label": "Fonti vs concetti",
            "hint": "Differenze chiave",
            "icon": "FileSearch",
            "prompt": "Che differenza c'è tra le fonti e le pagine di concetto nella wiki?",
        },
    ]


# ---------------------------------------------------------------------------
# Sampler
# ---------------------------------------------------------------------------


def test_sampler_prefers_source_folder(tmp_path: Path) -> None:
    _, wiki_dir = _make_pack(tmp_path)
    samples = _sampler.sample_pages(
        wiki_dir,
        page_types=[
            {"id": "concept", "folder": "concepts", "label": "Concetto"},
            {"id": "source", "folder": "sources", "label": "Fonte"},
        ],
        max_pages=2,
        max_chars=500,
    )
    assert [s.folder for s in samples] == ["sources", "concepts"]


def test_sampler_skips_incomplete_pages(tmp_path: Path) -> None:
    _, wiki_dir = _make_pack(tmp_path)
    _write_page(
        wiki_dir / "sources",
        "bozza.new.md",
        "Bozza",
        "Da rivedere.",
    )
    _write_page(
        wiki_dir / "sources",
        "errata.needs-review.md",
        "Errata",
        "Generata male.",
    )
    samples = _sampler.sample_pages(
        wiki_dir,
        page_types=[{"id": "source", "folder": "sources", "label": "Fonte"}],
        max_pages=10,
        max_chars=500,
    )
    rels = [s.relative_path for s in samples]
    assert "sources/guida-base.md" in rels
    assert all(not p.endswith(".new.md") for p in rels)
    assert all(not p.endswith(".needs-review.md") for p in rels)


def test_sampler_strips_wikilinks_in_excerpt(tmp_path: Path) -> None:
    _, wiki_dir = _make_pack(tmp_path)
    samples = _sampler.sample_pages(
        wiki_dir,
        page_types=[{"id": "source", "folder": "sources", "label": "Fonte"}],
        max_pages=1,
        max_chars=500,
    )
    assert samples
    assert "[[" not in samples[0].excerpt
    assert "architettura" in samples[0].excerpt.lower()


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


def test_regenerate_writes_questions_and_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack_dir, wiki_dir = _make_pack(tmp_path)

    def fake_call(**_kw: object) -> tuple[list[SuggestedQuestion], str]:
        return [SuggestedQuestion(**q) for q in _valid_questions()], "fake-model"

    monkeypatch.setattr(qfd, "call_llm", fake_call)
    outcome = qfd.regenerate_questions_from_docs(pack_dir, wiki_dir)
    assert outcome.applied is True
    assert outcome.questions_written == 3
    assert outcome.model == "fake-model"
    assert outcome.sampled_pages >= 1

    written = yaml.safe_load((pack_dir / "pack.yaml").read_text(encoding="utf-8"))
    chips = written["ui"]["suggested_questions"]
    assert len(chips) == 3
    assert chips[0]["label"] == "Architettura"

    marker = pack_dir / "prompts" / qfd.MARKER_FILENAME
    assert marker.is_file()
    meta = json.loads(marker.read_text(encoding="utf-8"))
    assert meta["status"] == "done"
    assert meta["questions_count"] == 3


def test_marker_blocks_second_run_without_force(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack_dir, wiki_dir = _make_pack(tmp_path)
    calls = {"n": 0}

    def fake_call(**_kw: object) -> tuple[list[SuggestedQuestion], str]:
        calls["n"] += 1
        return [SuggestedQuestion(**q) for q in _valid_questions()], "fake-model"

    monkeypatch.setattr(qfd, "call_llm", fake_call)
    qfd.regenerate_questions_from_docs(pack_dir, wiki_dir)
    second = qfd.regenerate_questions_from_docs(pack_dir, wiki_dir)
    assert second.applied is False
    assert "fingerprint matches" in (second.skipped_reason or "")
    assert calls["n"] == 1  # second run never reached the LLM


def test_force_bypasses_marker_and_regenerates(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack_dir, wiki_dir = _make_pack(tmp_path)

    monkeypatch.setattr(
        qfd,
        "call_llm",
        lambda **_kw: (
            [SuggestedQuestion(**q) for q in _valid_questions()],
            "fake-model",
        ),
    )
    first = qfd.regenerate_questions_from_docs(pack_dir, wiki_dir)
    assert first.applied
    second = qfd.regenerate_questions_from_docs(pack_dir, wiki_dir, force=True)
    assert second.applied is True


def test_llm_failure_leaves_existing_questions_intact(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack_dir, wiki_dir = _make_pack(tmp_path)
    # Seed pre-existing synth-time chips.
    raw = yaml.safe_load((pack_dir / "pack.yaml").read_text(encoding="utf-8"))
    raw["ui"]["suggested_questions"] = [
        {
            "category": "demo",
            "label": "Esempio",
            "hint": "Da synth scaffold",
            "icon": "Sparkles",
            "prompt": "Domanda di esempio dalla synth scaffold-time.",
        }
    ]
    (pack_dir / "pack.yaml").write_text(
        yaml.safe_dump(raw, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )

    def boom(**_kw: object) -> tuple[list[SuggestedQuestion], str]:
        raise SynthesisError("network down")

    monkeypatch.setattr(qfd, "call_llm", boom)
    outcome = qfd.regenerate_questions_from_docs(pack_dir, wiki_dir)
    assert outcome.applied is False
    assert outcome.warning == "network down"

    chips = yaml.safe_load((pack_dir / "pack.yaml").read_text(encoding="utf-8"))["ui"][
        "suggested_questions"
    ]
    assert chips[0]["label"] == "Esempio"
    # Marker must be dropped so a retry is possible.
    assert not (pack_dir / "prompts" / qfd.MARKER_FILENAME).exists()


def test_empty_vault_skips_without_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    pack_dir, _ = _make_pack(tmp_path)
    empty_wiki = tmp_path / "empty_vault" / "wiki"
    empty_wiki.mkdir(parents=True)

    monkeypatch.setattr(
        qfd,
        "call_llm",
        lambda **_kw: pytest.fail("LLM must not be called on empty vault"),
    )
    outcome = qfd.regenerate_questions_from_docs(pack_dir, empty_wiki)
    assert outcome.applied is False
    assert "no source pages" in (outcome.skipped_reason or "")
    assert not (pack_dir / "prompts" / qfd.MARKER_FILENAME).exists()


def test_missing_pack_yaml_skipped_gracefully(tmp_path: Path) -> None:
    pack_dir = tmp_path / "no_pack"
    pack_dir.mkdir()
    wiki_dir = tmp_path / "vault" / "wiki"
    wiki_dir.mkdir(parents=True)
    outcome = qfd.regenerate_questions_from_docs(pack_dir, wiki_dir)
    assert outcome.applied is False
    assert "pack.yaml not found" in (outcome.skipped_reason or "")


def test_under_quota_response_triggers_synthesis_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """When LLM returns < min_questions valid entries, marker is dropped."""
    pack_dir, wiki_dir = _make_pack(tmp_path)

    def too_few(**_kw: object) -> tuple[list[SuggestedQuestion], str]:
        # Only one valid question — below the min of 3.
        raise SynthesisError("LLM returned 1 valid question(s); need at least 3")

    monkeypatch.setattr(qfd, "call_llm", too_few)
    outcome = qfd.regenerate_questions_from_docs(pack_dir, wiki_dir)
    assert outcome.applied is False
    assert "need at least" in (outcome.warning or "")
    assert not (pack_dir / "prompts" / qfd.MARKER_FILENAME).exists()


# ---------------------------------------------------------------------------
# Fingerprint-based invalidation (new doc added → rerun)
# ---------------------------------------------------------------------------


def test_fingerprint_changes_when_new_source_page_added(tmp_path: Path) -> None:
    _, wiki_dir = _make_pack(tmp_path)
    page_types = [
        {"id": "source", "folder": "sources", "label": "Fonte"},
        {"id": "concept", "folder": "concepts", "label": "Concetto"},
    ]
    fp1 = qfd.compute_doc_fingerprint(wiki_dir, page_types)
    assert fp1  # non-empty: seeded sources exist
    _write_page(wiki_dir / "sources", "secondo.md", "Secondo doc", "Contenuto nuovo.")
    fp2 = qfd.compute_doc_fingerprint(wiki_dir, page_types)
    assert fp2 and fp2 != fp1


def test_fingerprint_stable_for_same_corpus(tmp_path: Path) -> None:
    _, wiki_dir = _make_pack(tmp_path)
    page_types = [{"id": "source", "folder": "sources", "label": "Fonte"}]
    fp1 = qfd.compute_doc_fingerprint(wiki_dir, page_types)
    # Re-read body of the same page → fingerprint must not change.
    (wiki_dir / "sources" / "guida-base.md").write_text(
        (wiki_dir / "sources" / "guida-base.md").read_text(encoding="utf-8")
        + "\n\nAggiunta inline.\n",
        encoding="utf-8",
    )
    fp2 = qfd.compute_doc_fingerprint(wiki_dir, page_types)
    assert fp1 == fp2  # set of source slugs unchanged


def test_fingerprint_excludes_incomplete_pages(tmp_path: Path) -> None:
    _, wiki_dir = _make_pack(tmp_path)
    page_types = [{"id": "source", "folder": "sources", "label": "Fonte"}]
    fp1 = qfd.compute_doc_fingerprint(wiki_dir, page_types)
    _write_page(wiki_dir / "sources", "draft.new.md", "Draft", "Bozza.")
    _write_page(wiki_dir / "sources", "broken.needs-review.md", "Broken", "Errata.")
    fp2 = qfd.compute_doc_fingerprint(wiki_dir, page_types)
    assert fp1 == fp2  # incomplete suffixes do not count toward corpus


def test_new_doc_invalidates_marker_and_triggers_rerun(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Add a doc after first run → marker stale → regenerate."""
    pack_dir, wiki_dir = _make_pack(tmp_path)
    calls = {"n": 0}

    def fake_call(**_kw: object) -> tuple[list[SuggestedQuestion], str]:
        calls["n"] += 1
        return [SuggestedQuestion(**q) for q in _valid_questions()], "fake-model"

    monkeypatch.setattr(qfd, "call_llm", fake_call)
    first = qfd.regenerate_questions_from_docs(pack_dir, wiki_dir)
    assert first.applied and calls["n"] == 1
    fp_before = first.fingerprint

    # Simulate a new doc ingested into the vault.
    _write_page(
        wiki_dir / "sources",
        "nuovo-doc.md",
        "Nuovo doc",
        "## Sezione\n\nContenuto del nuovo documento.\n",
    )

    second = qfd.regenerate_questions_from_docs(pack_dir, wiki_dir)
    assert second.applied is True  # corpus changed → rerun fired
    assert calls["n"] == 2
    assert second.fingerprint and second.fingerprint != fp_before

    # Third call without further changes → no rerun (idempotent on stable corpus).
    third = qfd.regenerate_questions_from_docs(pack_dir, wiki_dir)
    assert third.applied is False
    assert "fingerprint matches" in (third.skipped_reason or "")
    assert calls["n"] == 2


def test_doc_removal_also_invalidates_marker(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Removing a source page changes the fingerprint → regenerate."""
    pack_dir, wiki_dir = _make_pack(tmp_path)
    _write_page(
        wiki_dir / "sources",
        "secondo.md",
        "Secondo",
        "## Intro\n\nContenuto secondo doc.\n",
    )
    calls = {"n": 0}

    def fake_call(**_kw: object) -> tuple[list[SuggestedQuestion], str]:
        calls["n"] += 1
        return [SuggestedQuestion(**q) for q in _valid_questions()], "fake-model"

    monkeypatch.setattr(qfd, "call_llm", fake_call)
    first = qfd.regenerate_questions_from_docs(pack_dir, wiki_dir)
    assert first.applied and calls["n"] == 1

    (wiki_dir / "sources" / "secondo.md").unlink()
    second = qfd.regenerate_questions_from_docs(pack_dir, wiki_dir)
    assert second.applied is True
    assert calls["n"] == 2
    assert second.fingerprint != first.fingerprint
