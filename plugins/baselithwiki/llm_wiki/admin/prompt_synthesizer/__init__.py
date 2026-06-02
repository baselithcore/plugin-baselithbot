"""Domain-aware prompt synthesis for newly scaffolded packs.

When an end-user scaffolds a custom pack (e.g. ``hr``, ``finance``,
``research``) the bare ``_template`` ships only a *generic* skeleton —
its Decomposizione/Pairing/Citazioni sections are placeholders that
nobody is going to fill in by hand. The result is a wiki whose system
prompt sounds vaguely on-topic but never mentions HR-specific slots
(rapporto subordinato, CCNL, inquadramento) or HR-specific pairing
(spettanza ferie + maturazione + decadenza).

This package closes that gap. Given the user-supplied identity of the
new pack and its page-type taxonomy, it prompts the configured LLM to
**synthesise a vertical-tuned system prompt** that respects the
engine's structural skeleton and produces:

- ``system.j2``   — vertical-specific system prompt
- ``no_hits.j2``  — vertical-specific empty-retrieval fallback
- ``subtypes``    — page-type subtype taxonomy for ``pack.yaml``
- ``disclaimer``  — vertical-appropriate liability disclaimer
- ``suggested_questions`` — homepage chips tailored to the domain

Engine-invariant baselines
--------------------------
The Karpathy LLM-Wiki pattern (``istruzioni.md``) imposes invariants
that *every* pack must respect. These invariants are NOT delegated to
the LLM. Instead, the caller (``scaffold._maybe_synthesise_prompts``)
prepends a deterministic baseline header (``BASELINE_SYSTEM_J2`` /
``BASELINE_NO_HITS_J2``) that references ``pack.page_types`` via
Jinja2 and is rendered at runtime by ``PromptRegistry``.

Modular layout (>500 LOC budget):
- :mod:`.validators` — pure validation helpers (Jinja2 sanity, placeholder
  detection, folder-anchor enforcement, required-section gates).
- :mod:`.models`     — pydantic ``SynthesisResult`` / ``SuggestedQuestion``
  plus :class:`SynthesisError`.
- :mod:`.vendor`     — vendor/model resolution + JSON payload parser.
- :mod:`.meta_prompt`— ``_build_meta_prompt`` + system/user message templates.
- :mod:`.baselines`  — engine baseline j2 headers prepended to every result.
- This module       — orchestrator :func:`synthesize_pack`.
"""

from __future__ import annotations

import logging
from typing import Any

from pydantic import ValidationError

from llm_wiki.admin.prompt_synthesizer.baselines import (
    BASELINE_NO_HITS_J2,
    BASELINE_SYSTEM_J2,
)
from llm_wiki.admin.prompt_synthesizer.meta_prompt import _build_meta_prompt
from llm_wiki.admin.prompt_synthesizer.models import (
    SuggestedQuestion,
    SynthesisError,
    SynthesisResult,
)
from llm_wiki.admin.prompt_synthesizer.validators import (
    _assert_anchors_to_engine_folders,
    _collect_folders,
)
from llm_wiki.admin.prompt_synthesizer.vendor import (
    _parse_json_payload,
    _resolve_synthesis_model,
    _synthesis_vendor,
)
from llm_wiki.utils import llm as llm_client

logger = logging.getLogger(__name__)


def synthesize_pack(
    *,
    name: str,
    label: str,
    description: str,
    language: str,
    page_types: list[dict[str, Any]],
) -> SynthesisResult:
    """Call the configured LLM and return a validated, ready-to-write pack.

    ``page_types`` is the exact taxonomy that lives in the freshly-copied
    ``pack.yaml`` (each entry has at minimum ``id`` / ``label`` /
    ``plural`` / ``folder``). It is fed to the meta-prompt so the LLM
    references real folder names instead of inventing its own, and is
    used as the allow-list for the post-synthesis folder-anchor check.

    Raises :class:`SynthesisError` on any failure (LLM unreachable, JSON
    parse error, schema violation, Jinja syntax error, body that fails
    to anchor to the configured folders). The caller is expected to log
    and fall back to the bare ``_template`` files.
    """
    if not page_types:
        raise SynthesisError("page_types must not be empty")

    folder_set = _collect_folders(page_types)
    if not folder_set:
        raise SynthesisError("page_types contain no valid folder entries")

    model_id = _resolve_synthesis_model()
    system_msg, user_msg = _build_meta_prompt(
        name=name,
        label=label or name.title(),
        description=description or f"Wiki di dominio {name}.",
        language=language,
        page_types=page_types,
    )
    try:
        raw = llm_client.generate(
            messages=[
                {"role": "system", "content": system_msg},
                {"role": "user", "content": user_msg},
            ],
            model=model_id,
            json_mode=True,
            use_cache=False,
            vendor=_synthesis_vendor(),
        )
    except Exception as exc:  # network, timeout, model not pulled, etc.
        raise SynthesisError(f"LLM call failed: {exc}") from exc

    if not raw.strip():
        raise SynthesisError("LLM returned empty response")

    payload = _parse_json_payload(raw)

    try:
        result = SynthesisResult(
            system_prompt=str(payload.get("system_prompt", "")).strip(),
            no_hits=str(payload.get("no_hits", "")).strip(),
            subtypes=payload.get("subtypes") or {},
            disclaimer=str(payload.get("disclaimer", "")).strip(),
            suggested_questions=payload.get("suggested_questions") or [],
            model=model_id,
            vendor=_synthesis_vendor(),
        )
    except ValidationError as exc:
        raise SynthesisError(f"synthesised pack failed validation: {exc}") from exc

    _assert_anchors_to_engine_folders(result.system_prompt, folder_set)

    return result


__all__ = [
    "BASELINE_NO_HITS_J2",
    "BASELINE_SYSTEM_J2",
    "SuggestedQuestion",
    "SynthesisError",
    "SynthesisResult",
    "synthesize_pack",
]
