"""Natural-language → :class:`AgentBlueprint` synthesis.

The builder is the platform's front door: it turns a free-text description into
a validated, scope-bounded blueprint. Synthesis is LLM-driven but defensive —
malformed model output never crashes the request; it degrades to a conservative
heuristic blueprint so the platform stays usable offline or on a weak model.
"""

from __future__ import annotations

import json
import re
from typing import Any

from core.observability.logging import get_logger

from .prompts import BLUEPRINT_SYSTEM_PROMPT, get_blueprint_prompt
from .providers import ProviderUnavailableError, resolve_llm_service
from .types import (
    AgentBlueprint,
    AgentCapability,
    BlueprintScope,
    ModelProvider,
)

logger = get_logger(__name__)

__all__ = ["BlueprintBuilder"]

_SLUG_RE = re.compile(r"[^a-z0-9]+")
_JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def _slugify(name: str, fallback: str = "agent") -> str:
    """Derive a stable kebab-case slug from a human name."""
    slug = _SLUG_RE.sub("-", name.strip().lower()).strip("-")
    return slug or fallback


def _coerce_capabilities(values: Any) -> list[AgentCapability]:
    """Best-effort map arbitrary model output onto known capabilities."""
    out: list[AgentCapability] = []
    for item in values or []:
        try:
            out.append(AgentCapability(str(item).strip().lower()))
        except ValueError:
            continue
    return out or [AgentCapability.GENERATE]


class BlueprintBuilder:
    """Synthesises validated agent blueprints from natural language.

    Args:
        default_provider: Provider assumed when a request does not specify one.
        ollama_base: Optional Ollama base URL passed through to the synthesiser.
    """

    def __init__(
        self,
        default_provider: ModelProvider = ModelProvider.OLLAMA,
        ollama_base: str | None = None,
    ) -> None:
        self._default_provider = default_provider
        self._ollama_base = ollama_base

    async def build(self, description: str) -> AgentBlueprint:
        """Produce a blueprint from a natural-language description.

        Always returns a valid blueprint: on any synthesis or parse failure it
        falls back to a minimal single-capability agent seeded from the request.

        Args:
            description: The user's free-text agent description.

        Returns:
            A validated :class:`AgentBlueprint`.
        """
        description = description.strip()
        if not description:
            raise ValueError("description must not be empty")

        raw = await self._synthesise(description)
        if raw is None:
            return self._fallback(description)

        try:
            return self._assemble(raw, description)
        except (ValueError, KeyError, TypeError) as exc:
            logger.warning("blueprint_assemble_failed", error=str(exc))
            return self._fallback(description)

    async def _synthesise(self, description: str) -> dict[str, Any] | None:
        """Ask the default provider for a blueprint JSON object."""
        try:
            service = resolve_llm_service(
                self._default_provider, ollama_base=self._ollama_base
            )
        except ProviderUnavailableError as exc:
            logger.warning("blueprint_provider_unavailable", error=str(exc))
            return None

        prompt = get_blueprint_prompt(description, self._default_provider.value)
        try:
            response = await service.generate_response(
                prompt=prompt,
                system_prompt=BLUEPRINT_SYSTEM_PROMPT,
                json=True,
            )
        except Exception as exc:  # provider/runtime errors must not 500 the call
            logger.warning("blueprint_synthesis_error", error=str(exc))
            return None
        return self._extract_json(response)

    @staticmethod
    def _extract_json(response: str) -> dict[str, Any] | None:
        """Parse a JSON object from a (possibly noisy) model response."""
        candidate = response.strip()
        match = _JSON_BLOCK_RE.search(candidate)
        if match:
            candidate = match.group(0)
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def _assemble(self, raw: dict[str, Any], description: str) -> AgentBlueprint:
        """Validate raw model output into a typed blueprint."""
        raw_scope = raw.get("scope") or {}
        scope = BlueprintScope(
            capabilities=_coerce_capabilities(raw_scope.get("capabilities")),
            doc_namespaces=[str(n) for n in raw_scope.get("doc_namespaces", [])],
            allowed_tools=[str(t) for t in raw_scope.get("allowed_tools", [])],
            max_iterations=int(raw_scope.get("max_iterations", 3)),
            language=str(raw_scope.get("language", "python")).lower(),
            allow_execution=bool(raw_scope.get("allow_execution", True)),
        )

        provider = self._parse_provider(raw.get("provider"))
        name = str(raw.get("name") or "Generated Agent")[:80]

        return AgentBlueprint(
            id=_slugify(name),
            name=name,
            description=str(raw.get("description", ""))[:500],
            system_directive=str(raw.get("system_directive", ""))[:4000],
            provider=provider,
            model=(str(raw["model"]) if raw.get("model") else None),
            scope=scope,
            tags=[str(t) for t in raw.get("tags", [])][:12],
            source_prompt=description,
        )

    def _parse_provider(self, value: Any) -> ModelProvider:
        """Map model output to a provider, defaulting when unrecognised."""
        try:
            return ModelProvider(str(value).strip().lower())
        except (ValueError, AttributeError):
            return self._default_provider

    def _fallback(self, description: str) -> AgentBlueprint:
        """Construct a conservative blueprint without any model assistance."""
        logger.info("blueprint_fallback_used")
        return AgentBlueprint(
            id=_slugify(description[:40], fallback="generated-agent"),
            name=description[:60] or "Generated Agent",
            description=description[:200],
            system_directive=(
                "You are a focused BaselithCore coding assistant. Stay strictly "
                "within the requested task and the provided documentation context."
            ),
            provider=self._default_provider,
            model=None,
            scope=BlueprintScope(capabilities=[AgentCapability.GENERATE]),
            tags=["generated"],
            source_prompt=description,
        )
