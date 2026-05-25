"""Validation helpers for synthesised system prompts.

Pure functions — no LLM I/O. Pulled out so :mod:`models` can reference
them in pydantic field validators without dragging in the meta-prompt /
baseline payloads.
"""

from __future__ import annotations

import re
from typing import Any

import jinja2

# Sections every synthesised system prompt MUST mention. Substring match
# (lowercase) — the LLM picks its own exact heading wording.
_REQUIRED_SECTIONS = (
    "ruolo",
    "grounding",
    "assenza",
    "citazion",
    "output",
    "disclaimer",
)


# Negative-constraint sentinels: the synthesised body MUST repeat the
# anti-hallucination rules verbatim because the runtime LLM does not see
# the meta-prompt. Each entry is a group: AT LEAST ONE alternative
# (substring, lowercase) must appear in the body.
_NEGATIVE_CONSTRAINT_GROUPS: tuple[tuple[str, ...], ...] = (
    (
        "esclusivamente sul contesto",
        "solo dal contesto",
        "solo sul contesto",
        "basati esclusivamente",
        "fondati esclusivamente",
    ),
    ("non inventare", "non inventi", "mai inventare", "mai inventi", "non fabbricare"),
    ("dichiara", "dichiarare"),
    ("wikilink", "[[", "obsidian"),
    ("registro", "register"),
    ("operational", "operativo", "operative"),
    ("conceptual", "concettuale"),
)


_PLACEHOLDER_RE = re.compile(r"<[a-zA-Z][\w/ -]{0,40}>")
_SLUG_RE = re.compile(r"[^a-z0-9]+")
_JINJA_TAG_RE = re.compile(r"\{\{|\}\}|\{%|%\}|\{#|#\}")

# Output di questo Environment non finisce mai in HTML: i template
# producono prompt LLM (`system.j2`, `no_hits.j2`) destinati a `prompts/`
# su filesystem e all'API del modello. Autoescape rovinerebbe `&`/`<`/`>`
# legittimi nel testo dei prompt (es. "<DOMINIO>" → `&lt;DOMINIO&gt;`).
_JINJA_ENV = jinja2.Environment(  # nosec B701 — non-HTML rendering, vedi sopra
    autoescape=False,
    undefined=jinja2.StrictUndefined,
    keep_trailing_newline=True,
    trim_blocks=False,
    lstrip_blocks=False,
)


_CITATION_METAPHORS = frozenset(
    {"folder", "slug", "nome", "nome_pagina", "page", "page_slug", "wikilink"}
)


def _assert_valid_jinja(text: str, *, label: str) -> None:
    try:
        _JINJA_ENV.parse(text)
    except jinja2.TemplateSyntaxError as exc:
        raise ValueError(
            f"{label} contains invalid Jinja2: {exc.message} (line {exc.lineno})"
        ) from exc


def _assert_no_jinja_tags(text: str, *, label: str) -> None:
    """Reject any Jinja delimiter in the LLM-synthesised body.

    The engine baseline owns the templated section; the LLM body is
    plain text concatenated after.
    """
    match = _JINJA_TAG_RE.search(text)
    if match:
        raise ValueError(
            f"{label} contains Jinja delimiter {match.group(0)!r}. "
            "LLM-synthesised body must be plain text — the engine baseline "
            "owns the templated section."
        )


def _has_unresolved_placeholders(text: str) -> bool:
    """Detect leftover ``<token>`` fill-ins from the ``_template`` skeleton.

    Citation-grammar metaphors (``<folder>``, ``<slug>``, ``<nome>``,
    ``<nome-pagina>``) are allow-listed: they are pedagogically useful
    when the synthesised prompt teaches the runtime LLM how to format
    Obsidian wikilinks.
    """
    for match in _PLACEHOLDER_RE.finditer(text):
        token = match.group(0)
        inside = token[1:-1].strip()
        if " " not in inside and inside.islower() and inside.isidentifier():
            if inside in _CITATION_METAPHORS:
                continue
            return True
    return False


def _slugify_subtype(value: str) -> str:
    """Normalise a free-text subtype label into a stable slug."""
    v = value.strip().lower()
    v = _SLUG_RE.sub("_", v).strip("_")
    return v[:48]


def _collect_folders(page_types: list[dict[str, Any]]) -> set[str]:
    """Pull the ``folder`` value (or fallback id/plural) from each page type."""
    folders: set[str] = set()
    for pt in page_types:
        folder = pt.get("folder") or pt.get("plural") or pt.get("id")
        if isinstance(folder, str) and folder:
            folders.add(folder)
    return folders


def _assert_anchors_to_engine_folders(text: str, allowed: set[str]) -> None:
    """Reject synth bodies that ignore the configured page-type folders.

    Bar: at least half of the folder slugs (rounded up, minimum 1) must
    appear somewhere in the synthesised system prompt.
    """
    from llm_wiki.admin.prompt_synthesizer.models import SynthesisError

    target = max(1, (len(allowed) + 1) // 2)
    hits = sum(1 for f in allowed if f in text)
    if hits < target:
        raise SynthesisError(
            f"synthesised system prompt references {hits} of {len(allowed)} configured "
            f"folders ({sorted(allowed)}) — expected at least {target}. The LLM likely "
            f"invented its own taxonomy; rejecting and falling back to _template."
        )
