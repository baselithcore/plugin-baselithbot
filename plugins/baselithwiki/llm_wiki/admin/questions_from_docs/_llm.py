"""LLM call + meta-prompt builder for doc-grounded starter questions."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from llm_wiki.admin.prompt_synthesizer.models import (
    SuggestedQuestion,
    SynthesisError,
)
from llm_wiki.admin.prompt_synthesizer.vendor import (
    _parse_json_payload,
    _resolve_synthesis_model,
    _synthesis_vendor,
)
from llm_wiki.admin.questions_from_docs._sampler import PageSample

logger = logging.getLogger(__name__)


def call_llm(
    *,
    pack_data: dict[str, Any],
    samples: list[PageSample],
    min_questions: int,
    max_questions: int,
) -> tuple[list[SuggestedQuestion], str]:
    """Call the synth-tier model and return validated questions + model id.

    Raises :class:`SynthesisError` on any failure (network, empty body,
    JSON parse error, schema violation, under-quota after dedup) — the
    caller swallows and leaves the marker untouched so subsequent runs
    can retry.
    """
    from llm_wiki.utils import llm as llm_client

    label = str(pack_data.get("label") or pack_data.get("name") or "Wiki")
    description = str(pack_data.get("description") or "")
    language = str(pack_data.get("language") or "it")
    page_types = list(pack_data.get("page_types") or [])

    system_msg, user_msg = build_meta_prompt(
        label=label,
        description=description,
        language=language,
        page_types=page_types,
        samples=samples,
        min_questions=min_questions,
        max_questions=max_questions,
    )

    model_id = _resolve_synthesis_model()
    vendor = _synthesis_vendor()
    try:
        raw = llm_client.generate(
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            model=model_id,
            json_mode=True,
            use_cache=False,
            vendor=vendor,
        )
    except Exception as exc:  # noqa: BLE001
        raise SynthesisError(f"LLM call failed: {exc}") from exc

    if not raw.strip():
        raise SynthesisError("LLM returned empty response")

    payload = _parse_json_payload(raw)
    items = payload.get("suggested_questions")
    if not isinstance(items, list) or not items:
        raise SynthesisError("LLM payload missing non-empty `suggested_questions` list")

    questions: list[SuggestedQuestion] = []
    seen_labels: set[str] = set()
    for entry in items:
        if not isinstance(entry, dict):
            continue
        try:
            q = SuggestedQuestion(**entry)
        except ValidationError as exc:
            logger.debug("[questions-from-docs] dropping invalid entry: %s", exc)
            continue
        key = q.label.lower().strip()
        if key in seen_labels:
            continue
        seen_labels.add(key)
        questions.append(q)
        if len(questions) >= max_questions:
            break

    if len(questions) < min_questions:
        raise SynthesisError(
            f"LLM returned {len(questions)} valid question(s); need at least {min_questions}"
        )
    return questions, model_id


def build_meta_prompt(
    *,
    label: str,
    description: str,
    language: str,
    page_types: list[dict[str, Any]],
    samples: list[PageSample],
    min_questions: int,
    max_questions: int,
) -> tuple[str, str]:
    folder_lines = "\n".join(
        f"- `{pt.get('folder') or pt.get('plural') or pt.get('id')}/` — "
        f"{pt.get('label') or pt.get('id')}"
        for pt in page_types
    )
    sample_blocks: list[str] = []
    for i, s in enumerate(samples, 1):
        sample_blocks.append(
            f"### Documento {i} — `{s.relative_path}` ({s.page_type})\n"
            f"**Titolo:** {s.title}\n\n"
            f"{s.excerpt}"
        )
    samples_md = "\n\n---\n\n".join(sample_blocks)

    system = _SYS_META.strip().replace("<<LANGUAGE>>", language)
    user = (
        _USER_META.strip()
        .replace("<<LABEL>>", label)
        .replace("<<DESCRIPTION>>", description or f"Wiki {label}.")
        .replace("<<FOLDERS>>", folder_lines or "(taxonomy non specificata)")
        .replace("<<SAMPLES>>", samples_md)
        .replace("<<MIN>>", str(min_questions))
        .replace("<<MAX>>", str(max_questions))
    )
    return system, user


_SYS_META = """\
You are a UX writer for a retrieval-augmented knowledge wiki. Given a
handful of real pages that already live in the vault, produce a small
set of homepage starter questions that an end-user can click to begin
exploring the wiki.

Hard rules
----------
1. Write every string in the language requested below (`<<LANGUAGE>>`,
   ISO 639-1). Do not switch language inside a string.
2. Reply with ONE JSON object — no prose, no code fences, no markdown
   framing. The very first character of the response is `{`.
3. JSON shape:
   {
     "suggested_questions": [
       {"category": "...", "label": "...", "hint": "...",
        "icon": "Sparkles", "prompt": "..."},
       ...
     ]
   }
4. Each `prompt` MUST be answerable from the provided documents — never
   invent organisations, products, statutes, drugs, court rulings,
   article numbers, dates or any other identifier that does not appear
   verbatim in the samples. Speak in CATEGORIES when in doubt
   ("la normativa citata", "i processi descritti").
5. `prompt` is the literal text the user sends to the chat. Phrase it
   as a natural question in the target language, 8-30 words, no
   trailing instructions to the model ("rispondi…", "elenca…" only if
   it reads naturally for a curious end-user).
6. Cover COMPLEMENTARY intent archetypes across the set — never two
   questions of the same shape. Typical mix:
   - one **definitional** ("Cos'è X?", "Quali sono i principi di X?")
   - one **procedural / operativo** if the corpus contains how-to /
     runbook / process content
   - one **comparativa / sintesi** that spans multiple documents
     ("Confronta X e Y", "Quali differenze ci sono tra…")
   - one **overview / mappa** ("Da dove inizio se voglio capire…?")
   - optionally one **caso / esempio** when the corpus has case studies
7. `category` is a 1-2 word lowercase tag (e.g. `definizione`,
   `procedura`, `confronto`, `panoramica`, `esempio`). `hint` is a
   short uppercase-friendly subtitle (3-6 words) — what the user sees
   under the label.
8. `icon` MUST be exactly one of:
   Sparkles, FileSearch, BookOpen, GraduationCap, Stethoscope, Scale,
   Wrench, Briefcase, Users, Shield, FileText, Search, HelpCircle,
   Lightbulb, Zap, Building2, ClipboardList.
   Pick whichever best matches the archetype (Lightbulb for
   definitional, ClipboardList for procedural, FileSearch for
   comparative, BookOpen for overview, Sparkles as neutral default).
9. NO duplicate `label`s. NO chips that read as marketing copy.
10. Produce between <<MIN>> and <<MAX>> entries. Stop at <<MAX>>.
"""


_USER_META = """\
Genera le starter question per la wiki seguente.

- Nome visualizzato: <<LABEL>>
- Descrizione:       <<DESCRIPTION>>

Tassonomia cartelle (per orientamento):
<<FOLDERS>>

Documenti reali pescati dal vault (ancorati a queste fonti TUTTE le
domande che proponi):

<<SAMPLES>>

Output: SOLO il JSON object descritto nel system message, con
<<MIN>>..<<MAX>> entries. Inizia immediatamente con `{`.
"""


__all__ = ["build_meta_prompt", "call_llm"]
