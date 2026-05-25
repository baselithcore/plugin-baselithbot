"""Tests for the LLM-backed prompt synthesizer (admin path).

The synthesizer owns the contract between user-supplied identity (name/
label/description) and the artefacts that land in the freshly scaffolded
pack: ``system.j2``, ``no_hits.j2``, ``pack.yaml.subtypes`` /
``pack.yaml.ui.disclaimer`` / ``pack.yaml.ui.suggested_questions``.

Failure of the LLM call must NEVER break scaffolding — these tests
pin both the validation contract (good payloads in, schema failures
out) and the graceful-degradation behaviour at the scaffold boundary.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from llm_wiki.admin import prompt_synthesizer as ps
from llm_wiki.admin.scaffold import ScaffoldRequest, repo_root, scaffold_pack

REPO = repo_root()


_DEFAULT_PAGE_TYPES = [
    {"id": "source", "label": "Fonte", "plural": "fonti", "folder": "sources"},
    {"id": "concept", "label": "Concetto", "plural": "concetti", "folder": "concepts"},
    {"id": "entity", "label": "Entità", "plural": "entità", "folder": "entities"},
    {"id": "topic", "label": "Tema", "plural": "temi", "folder": "topics"},
]


def _valid_payload() -> dict[str, object]:
    """A minimally-valid synthesizer payload that passes every validator.

    Each test mutates one field at a time so failure messages stay focused
    on the specific check that fired. The body literally references the
    default page-type folders (``sources`` / ``concepts``) so the
    folder-anchor check (run in ``synthesize_pack``, not in the pydantic
    validators) does not trip — tests that exercise the anchor check
    explicitly override this.
    """
    sys_p = (
        "# Ruolo e obiettivo\n"
        "Sei l'assistente di una wiki HR.\n\n"
        "# Principio di grounding\n"
        "Basati ESCLUSIVAMENTE sul CONTESTO fornito; mai inventare cifre o procedure.\n\n"
        "# Adattamento al registro del CONTESTO\n"
        "Distingui registro operativo da concettuale prima di rispondere.\n\n"
        "# Trattamento dell'assenza\n"
        "Dichiara onestamente quando il vault non contiene il dato richiesto.\n\n"
        "# Citazioni\n"
        "Cita le fonti come wikilink Obsidian `[[sources/ccnl-metalmeccanici]]` o "
        "`[[concepts/ferie]]`.\n\n"
        "# Output\n"
        "Sezione Fonti finale con wikilink alle pagine `entities/` e `topics/`.\n\n"
        "# Disclaimer di responsabilità\n"
        "Verifica direttamente i CCNL.\n"
    ) * 6  # ~3500 chars, comfortably inside [1500, 12000].
    return {
        "system_prompt": sys_p,
        "no_hits": "Il retrieval non ha trovato chunk rilevanti. " * 12,
        "subtypes": {"source": ["ccnl", "policy_aziendale"]},
        "disclaimer": "Sintesi grounded sulle fonti. " * 4,
        "suggested_questions": [
            {
                "category": "policy",
                "label": "Ferie",
                "hint": "Spettanza e maturazione",
                "icon": "Briefcase",
                "prompt": "Quante ferie spettano nel primo anno di assunzione?",
            },
            {
                "category": "procedura",
                "label": "Permessi",
                "hint": "Modalità di richiesta",
                "icon": "ClipboardList",
                "prompt": "Quali sono le modalità di richiesta dei permessi retribuiti?",
            },
            {
                "category": "definizione",
                "label": "RAL",
                "hint": "Cosa comprende",
                "icon": "FileText",
                "prompt": "Cosa comprende la RAL e come si calcola in busta paga?",
            },
            {
                "category": "panoramica",
                "label": "Mappa CCNL",
                "hint": "Da dove iniziare",
                "icon": "BookOpen",
                "prompt": "Da dove inizio se voglio capire i CCNL principali del settore?",
            },
        ],
        "model": "test-model",
        "vendor": "ollama",
    }


# --- validation contract ---------------------------------------------------


def test_synthesis_result_accepts_minimal_valid_payload() -> None:
    r = ps.SynthesisResult(**_valid_payload())  # type: ignore[arg-type]
    assert r.subtypes == {"source": ["ccnl", "policy_aziendale"]}
    assert len(r.suggested_questions) == 4


def test_missing_required_section_rejected() -> None:
    payload = _valid_payload()
    # Replace the entire prompt with one that omits "grounding".
    payload["system_prompt"] = ("ruolo assenza citazion output disclaimer text. ") * 80
    with pytest.raises(ValidationError) as exc:
        ps.SynthesisResult(**payload)  # type: ignore[arg-type]
    assert "grounding" in str(exc.value)


def test_unresolved_placeholder_rejected() -> None:
    payload = _valid_payload()
    # Inject the kind of `<argomento>` token the meta-prompt warns the
    # LLM against. Validator must catch it. Body includes the negative
    # constraints AND the register-adaptation tokens (registro / operational
    # / conceptual) so all other guard groups pass and the placeholder check
    # is the one that fires.
    payload["system_prompt"] = (
        "# Ruolo\n# Principio di grounding\n"
        "Basati ESCLUSIVAMENTE sul CONTESTO, mai inventare. Dichiara assenza.\n"
        "# Adattamento al registro: operational / conceptual / mixed\n"
        "slot <argomento>\n# Assenza\n"
        "# Citazioni con wikilink\n# Output\n# Disclaimer di responsabilità\n"
    ) * 30
    with pytest.raises(ValidationError) as exc:
        ps.SynthesisResult(**payload)  # type: ignore[arg-type]
    assert "placeholder" in str(exc.value)


def test_missing_negative_constraint_rejected() -> None:
    """Synthesised prompt must REPEAT the anti-hallucination rules.

    Section titles are not enough — small models drop the negative
    constraints ("non inventare cifre/comandi") while keeping the
    section headers. Validator must catch that and force fallback to
    the ``_template`` skeleton.
    """
    payload = _valid_payload()
    # System prompt that names every required SECTION but omits the
    # *content* of the negative constraints (no "esclusivamente", no
    # "mai inventare", no "dichiara"). Naming the sections is not
    # enough — the rules themselves must survive synthesis.
    payload["system_prompt"] = (
        "# Ruolo\nSei l'assistente.\n"
        "# Principio di grounding\nUsa i dati delle fonti.\n"
        "# Trattamento dell'assenza\nSegnala in modo educato.\n"
        "# Citazioni\nUsa wikilink ai folder sources e concepts.\n"
        "# Output\nStruttura adattiva alla domanda.\n"
        "# Disclaimer di responsabilità\nVerifica le fonti.\n"
    ) * 25
    with pytest.raises(ValidationError) as exc:
        ps.SynthesisResult(**payload)  # type: ignore[arg-type]
    assert "negative constraint" in str(exc.value)


def test_invalid_jinja_rejected() -> None:
    payload = _valid_payload()
    # Unclosed `{{` — Jinja env.parse must raise.
    payload["system_prompt"] = (
        "# Ruolo\n# Principio di grounding\n# Assenza\n"
        "# Citazioni\n# Output\n# Disclaimer di responsabilità\n{{ unclosed"
    ) * 30
    with pytest.raises(ValidationError) as exc:
        ps.SynthesisResult(**payload)  # type: ignore[arg-type]
    assert "Jinja2" in str(exc.value) or "unclosed" in str(exc.value).lower()


def test_unknown_page_type_silently_dropped() -> None:
    payload = _valid_payload()
    payload["subtypes"] = {
        "source": ["ccnl"],
        "unknown_page_type": ["nope"],
        "concept": ["Has Spaces 2024!"],
    }
    r = ps.SynthesisResult(**payload)  # type: ignore[arg-type]
    assert "unknown_page_type" not in r.subtypes
    # Free-form labels normalised to slugs.
    assert r.subtypes["concept"] == ["has_spaces_2024"]


def test_icon_outside_allowlist_falls_back_to_sparkles() -> None:
    sq = ps.SuggestedQuestion(
        category="c",
        label="l",
        hint="h",
        icon="NotARealIcon",
        prompt="ten chars min here",
    )
    assert sq.icon == "Sparkles"


# --- meta-prompt + JSON parsing -------------------------------------------


def test_meta_prompt_substitutes_all_placeholders() -> None:
    sys_msg, user_msg = ps._build_meta_prompt(
        name="hr",
        label="Wiki HR",
        description="Politiche aziendali",
        language="it",
        page_types=_DEFAULT_PAGE_TYPES,
    )
    assert "<<NAME>>" not in user_msg
    assert "<<LABEL>>" not in user_msg
    assert "<<DESCRIPTION>>" not in user_msg
    assert "<<LANGUAGE>>" not in user_msg
    assert "<<FOLDERS_TABLE>>" not in user_msg
    assert "<<FOLDERS_TABLE>>" not in sys_msg
    assert "<<FOLDER_SLUGS>>" not in sys_msg
    assert "hr" in user_msg
    assert "Wiki HR" in user_msg
    # Engine folders embedded literally so the LLM uses them in body.
    assert "wiki/sources/" in user_msg
    assert "wiki/concepts/" in user_msg
    assert "`sources`" in sys_msg
    # System message defines the JSON contract verbatim.
    assert "system_prompt" in sys_msg
    assert "no_hits" in sys_msg
    assert "suggested_questions" in sys_msg


def test_parse_json_payload_strips_code_fences() -> None:
    raw = '```json\n{"system_prompt": "x", "no_hits": "y"}\n```'
    parsed = ps._parse_json_payload(raw)
    assert parsed == {"system_prompt": "x", "no_hits": "y"}


def test_parse_json_payload_clips_prose_prefix() -> None:
    raw = 'Here you go:\n{"k": 1}'
    parsed = ps._parse_json_payload(raw)
    assert parsed == {"k": 1}


def test_parse_json_payload_rejects_non_object() -> None:
    with pytest.raises(ps.SynthesisError):
        ps._parse_json_payload("[1, 2, 3]")


# --- engine-folder anchor check -------------------------------------------


def test_anchor_check_rejects_body_without_configured_folders() -> None:
    """Body that ignores ``page_types[*].folder`` is bounced at synth time."""
    text_no_anchor = (
        "Il prompt non menziona nessuna delle cartelle del vault, parla solo di "
        "categorie inventate come `documents/` e `staff/`. " * 10
    )
    with pytest.raises(ps.SynthesisError, match="invented its own taxonomy"):
        ps._assert_anchors_to_engine_folders(
            text_no_anchor, {"sources", "concepts", "entities"}
        )


def test_anchor_check_accepts_body_referencing_configured_folders() -> None:
    text = (
        "La risposta finisce con sezione Fonti, contenente wikilink "
        "`[[sources/<slug>]]` e `[[concepts/<slug>]]`."
    )
    # Should not raise (2 of 4 folders mentioned, target is ceil(4/2)=2).
    ps._assert_anchors_to_engine_folders(
        text, {"sources", "concepts", "entities", "topics"}
    )


def test_collect_folders_falls_back_to_plural_or_id() -> None:
    pts = [
        {"id": "source", "folder": "sources"},
        {"id": "concept", "plural": "concetti"},  # no folder -> plural
        {"id": "topic"},  # no folder + no plural -> id
    ]
    assert ps._collect_folders(pts) == {"sources", "concetti", "topic"}


# --- engine baseline templates --------------------------------------------


def test_baseline_system_j2_renders_with_runtime_pack() -> None:
    """Baseline header must render cleanly via PromptRegistry's Jinja env.

    A stale baseline that references a missing pack attribute would raise
    at first chat request — this test catches that regression at synthesis
    time rather than waiting for a real query.
    """
    import jinja2

    from llm_wiki.domain.pack import DomainPack, PageType, UILabels

    pack = DomainPack(
        name="hr",
        label="Wiki HR",
        description="HR vault",
        language="it",
        page_types=[
            PageType(
                id=p["id"], label=p["label"], plural=p["plural"], folder=p["folder"]
            )
            for p in _DEFAULT_PAGE_TYPES
        ],
        ui=UILabels(app_name="Wiki HR"),
    )
    env = jinja2.Environment(  # nosec B701 — non-HTML prompt templates
        autoescape=False,
        undefined=jinja2.StrictUndefined,
        keep_trailing_newline=True,
    )
    rendered_sys = env.from_string(ps.BASELINE_SYSTEM_J2).render(pack=pack)
    assert "Wiki HR" in rendered_sys
    assert "wiki/sources/" in rendered_sys
    assert "wiki/concepts/" in rendered_sys
    assert "wiki/entities/" in rendered_sys
    assert "wiki/topics/" in rendered_sys
    assert "wiki/index.md" in rendered_sys
    assert "wiki/log.md" in rendered_sys
    assert "raw/" in rendered_sys

    rendered_no_hits = env.from_string(ps.BASELINE_NO_HITS_J2).render(pack=pack)
    assert "Wiki HR" in rendered_no_hits
    for folder in ("sources", "concepts", "entities", "topics"):
        assert f"wiki/{folder}/" in rendered_no_hits


# --- scaffold integration: graceful fallback ------------------------------


@pytest.fixture
def fresh_synth_pack() -> Iterator[tuple[str, Path]]:
    """Yield (slug, target_pack_dir) for an isolated scaffold; cleans up."""
    name = "synthtestpack"
    target = REPO / "domains" / name
    vault = REPO / "vaults" / name
    for p in (target, vault):
        if p.exists():
            shutil.rmtree(p)
    yield name, target
    for p in (target, vault):
        if p.exists():
            shutil.rmtree(p)


def test_scaffold_with_synthesis_off_skips_synthesis_cleanly(
    fresh_synth_pack: tuple[str, Path],
) -> None:
    name, target = fresh_synth_pack
    res = scaffold_pack(
        ScaffoldRequest(
            name=name,
            label="Test",
            description="off",
            language="it",
            write_env=False,
            activate=False,
            synthesize_prompts=False,
        )
    )
    assert res.synthesis_applied is False
    assert res.synthesis_warning is None
    # Generic _template still in place — Jinja vars survive.
    sys_text = (target / "prompts" / "system.j2").read_text(encoding="utf-8")
    assert "{{ pack." in sys_text
    assert not (target / "prompts" / ".synth.meta.json").exists()


def test_scaffold_with_synthesis_failure_falls_back(
    monkeypatch: pytest.MonkeyPatch, fresh_synth_pack: tuple[str, Path]
) -> None:
    """If the synthesizer raises, scaffold completes with a warning, not 500."""
    name, target = fresh_synth_pack

    def _boom(**_kw: object) -> ps.SynthesisResult:
        raise ps.SynthesisError("simulated provider outage")

    # Patch the symbol that scaffold.py imports lazily inside the helper.
    monkeypatch.setattr(ps, "synthesize_pack", _boom)

    res = scaffold_pack(
        ScaffoldRequest(
            name=name,
            label="Fail",
            description="must fall back",
            language="it",
            write_env=False,
            activate=False,
            synthesize_prompts=True,
        )
    )
    assert res.synthesis_applied is False
    assert res.synthesis_warning is not None
    assert "simulated provider outage" in res.synthesis_warning
    # _template prompts must still be on disk.
    assert (target / "prompts" / "system.j2").exists()


def test_scaffold_with_synthesis_success_writes_artefacts(
    monkeypatch: pytest.MonkeyPatch, fresh_synth_pack: tuple[str, Path]
) -> None:
    """Stub a successful synthesis, verify all files + pack.yaml patches land."""
    name, target = fresh_synth_pack

    payload = _valid_payload()
    valid = ps.SynthesisResult(**payload)  # type: ignore[arg-type]

    def _ok(**_kw: object) -> ps.SynthesisResult:
        return valid

    monkeypatch.setattr(ps, "synthesize_pack", _ok)

    res = scaffold_pack(
        ScaffoldRequest(
            name=name,
            label="OK",
            description="hr policies",
            language="it",
            write_env=False,
            activate=False,
            synthesize_prompts=True,
        )
    )
    assert res.synthesis_applied is True
    assert res.synthesis_model == "test-model"
    assert res.synthesis_warning is None

    sys_text = (target / "prompts" / "system.j2").read_text(encoding="utf-8")
    # LLM-synthesised body landed.
    assert "Principio di grounding" in sys_text
    # Engine baseline got prepended (Jinja that resolves at runtime to
    # describe the Karpathy LLM-Wiki layout from `pack.page_types`).
    assert "Architettura del vault" in sys_text
    assert "{% for pt in pack.page_types %}" in sys_text
    assert "wiki/index.md" in sys_text
    assert "wiki/log.md" in sys_text
    # The folder allow-list reference appears literally.
    assert "raw/" in sys_text

    no_hits_text = (target / "prompts" / "no_hits.j2").read_text(encoding="utf-8")
    assert "retrieval" in no_hits_text.lower()
    # no_hits also gets the engine baseline header.
    assert "Sotto-cartelle ispezionate" in no_hits_text

    meta_path = target / "prompts" / ".synth.meta.json"
    assert meta_path.exists()
    import json

    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    assert meta["model"] == "test-model"
    assert meta["name"] == name
    assert "ts" in meta

    pack_data = yaml.safe_load((target / "pack.yaml").read_text(encoding="utf-8"))
    assert pack_data["subtypes"] == {"source": ["ccnl", "policy_aziendale"]}
    assert pack_data["ui"]["disclaimer"].startswith("Sintesi grounded")
    assert len(pack_data["ui"]["suggested_questions"]) == 4


def test_scaffold_skips_synthesis_when_forking_a_seed(
    monkeypatch: pytest.MonkeyPatch, fresh_synth_pack: tuple[str, Path]
) -> None:
    """Seed forks ship curated prompts — synthesizer must not be called."""
    name, target = fresh_synth_pack

    called = {"count": 0}

    def _spy(**_kw: object) -> ps.SynthesisResult:
        called["count"] += 1
        raise ps.SynthesisError("should not be called")

    monkeypatch.setattr(ps, "synthesize_pack", _spy)

    res = scaffold_pack(
        ScaffoldRequest(
            name=name,
            label="Fork",
            description="forked from medical",
            language="it",
            write_env=False,
            activate=False,
            synthesize_prompts=True,
            from_seed="medical",
        )
    )
    assert called["count"] == 0
    assert res.synthesis_applied is False
    assert res.synthesis_warning is None
    # The medical seed system prompt must be present in the fork.
    sys_text = (target / "prompts" / "system.j2").read_text(encoding="utf-8")
    assert "clinic" in sys_text.lower() or "linee guida" in sys_text.lower()
