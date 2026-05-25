"""Prompt registry backed by Jinja2 + the active Domain Pack.

Replaces hardcoded ``SYSTEM_PROMPT`` constants and the monolithic
``ingest_raw/prompts.py`` module of the reference project. Templates live
on disk under ``<pack>/prompts/`` and are rendered with strict
``StrictUndefined`` so a missing variable fails loud at request time
(better than emitting a malformed prompt to the LLM).

Naming convention
-----------------
- ``system.j2`` — RAG agent system prompt.
- ``user.j2`` — RAG user message template (vars: ``context``, ``question``).
- ``classify.j2`` — ingest planner classify-step user prompt.
- ``plan.j2`` — ingest planner outline-step user prompt.
- ``source_page.j2`` / ``entity_page.j2`` / ``refine.j2`` — ingest generator.
- ``no_hits.j2`` — fallback message when retrieval returns zero chunks.

Each template receives a base context with ``pack`` (the
:class:`DomainPack`), plus per-call kwargs.
"""

from __future__ import annotations

import threading
from functools import lru_cache
from pathlib import Path
from typing import Any

from jinja2 import (
    FileSystemLoader,
    StrictUndefined,
    TemplateNotFound,
    select_autoescape,
)
from jinja2.sandbox import SandboxedEnvironment

from llm_wiki.domain.pack import DomainPack
from llm_wiki.domain.registry import get_pack


class PromptNotFoundError(KeyError):
    """Template name does not exist under the active pack's prompts dir."""


class PromptRegistry:
    """Render Jinja2 templates from a Domain Pack's prompts directory.

    One registry per pack. Construction is cheap (no I/O): templates are
    loaded lazily and cached by Jinja2's bytecode cache.
    """

    def __init__(self, pack: DomainPack) -> None:
        self._pack = pack
        self._env = SandboxedEnvironment(
            loader=FileSystemLoader(str(pack.prompts_path)),
            autoescape=select_autoescape(default=False),
            undefined=StrictUndefined,
            keep_trailing_newline=False,
            trim_blocks=True,
            lstrip_blocks=True,
        )

    @property
    def pack(self) -> DomainPack:
        return self._pack

    @property
    def prompts_path(self) -> Path:
        return self._pack.prompts_path

    def has(self, name: str) -> bool:
        try:
            self._env.get_template(name)
        except TemplateNotFound:
            return False
        return True

    def render(self, name: str, /, **vars: Any) -> str:
        """Render ``<name>`` with ``vars`` plus ``pack`` injected by default.

        Variables passed by the caller win over the defaults — keeps tests
        deterministic and lets specific call sites override pack metadata
        when they need to.
        """
        try:
            template = self._env.get_template(name)
        except TemplateNotFound as exc:
            raise PromptNotFoundError(
                f"prompt {name!r} not found under {self.prompts_path}. "
                f"Available: {sorted(self._env.list_templates())}"
            ) from exc
        ctx: dict[str, Any] = {"pack": self._pack, **vars}
        return template.render(**ctx)


_lock = threading.Lock()
_cached_registry: PromptRegistry | None = None
_cached_pack_root: Path | None = None


def get_registry() -> PromptRegistry:
    """Return the process-wide :class:`PromptRegistry`.

    Tied to the loaded Domain Pack: if the pack's ``root`` changes (tests
    reset the cache), the registry is rebuilt.
    """
    global _cached_registry, _cached_pack_root
    pack = get_pack()
    with _lock:
        if _cached_registry is None or _cached_pack_root != pack.root:
            _cached_registry = PromptRegistry(pack)
            _cached_pack_root = pack.root
        return _cached_registry


def render(name: str, /, **vars: Any) -> str:
    """Shortcut: ``get_registry().render(name, **vars)``."""
    return get_registry().render(name, **vars)


def reset_registry_cache() -> None:
    """Test-only: drop the cached registry so the next call rebuilds it."""
    global _cached_registry, _cached_pack_root
    with _lock:
        _cached_registry = None
        _cached_pack_root = None
    # also drop any lru_cache decorated helpers added later
    for fn in (_render_string,):
        fn.cache_clear()


@lru_cache(maxsize=64)
def _render_string(template_source: str) -> str:
    """Internal: render a one-off inline template (no pack file). Cached."""
    env = SandboxedEnvironment(
        autoescape=select_autoescape(default=False),
        undefined=StrictUndefined,
    )
    return env.from_string(template_source).render()
