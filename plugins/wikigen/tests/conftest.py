"""Test-suite-wide fixtures.

Disables the LLM-backed prompt synthesizer by default for every test in
this package. Without this autouse fixture, any call to
:func:`llm_wiki.admin.scaffold.scaffold_pack` would (with the field's
production default ``synthesize_prompts=True``) try to reach the
configured LLM provider and either hang on the network timeout or
emit a non-deterministic prompt — neither acceptable in CI.

Tests that want to exercise the synthesizer explicitly (see
``test_prompt_synthesizer.py``) override the patch with their own
``monkeypatch.setattr(ps, "synthesize_pack", ...)`` call, which wins
because pytest applies the test-local patch *after* the autouse fixture.
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def _disable_llm_synthesis(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Make ``synthesize_pack`` raise a fast SynthesisError so the scaffold
    helper falls back to the bare ``_template`` files (its documented
    graceful-degradation path).
    """
    from llm_wiki.admin import prompt_synthesizer as ps

    def _no_call(**_kw: object) -> ps.SynthesisResult:
        raise ps.SynthesisError("synthesis disabled in test session")

    monkeypatch.setattr(ps, "synthesize_pack", _no_call)
    yield
