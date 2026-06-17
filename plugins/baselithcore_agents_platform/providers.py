"""Provider resolution for multi-backend coding models.

Lowers a blueprint's :class:`ModelProvider` onto the framework's native
``LLMService``. Provider selection is the only place the platform touches model
credentials, and it never stores them: keys are read from the core
``LLMConfig`` (already wrapped in ``SecretStr``) and a per-request override
clones that config rather than copying secrets into plugin state.
"""

from __future__ import annotations

from typing import Any

from core.observability.logging import get_logger

from .types import ModelProvider

logger = get_logger(__name__)

__all__ = ["resolve_llm_service", "describe_models", "ProviderUnavailableError"]


# Curated default model per provider, surfaced in the UI and used when a
# blueprint does not pin an explicit model id.
_DEFAULT_MODELS: dict[ModelProvider, str] = {
    ModelProvider.ANTHROPIC: "claude-sonnet-4-6",
    ModelProvider.OPENAI: "gpt-4o",
    ModelProvider.OLLAMA: "llama3.2",
}


class ProviderUnavailableError(RuntimeError):
    """Raised when a provider cannot be initialised (e.g. missing credentials)."""


def describe_models() -> list[dict[str, Any]]:
    """Return the provider/model catalogue for the dashboard.

    Returns:
        One entry per provider with its default model and whether it requires
        an API key (Ollama runs locally and does not).
    """
    return [
        {
            "provider": ModelProvider.ANTHROPIC.value,
            "default_model": _DEFAULT_MODELS[ModelProvider.ANTHROPIC],
            "requires_api_key": True,
            "local": False,
        },
        {
            "provider": ModelProvider.OPENAI.value,
            "default_model": _DEFAULT_MODELS[ModelProvider.OPENAI],
            "requires_api_key": True,
            "local": False,
        },
        {
            "provider": ModelProvider.OLLAMA.value,
            "default_model": _DEFAULT_MODELS[ModelProvider.OLLAMA],
            "requires_api_key": False,
            "local": True,
        },
    ]


def resolve_llm_service(
    provider: ModelProvider,
    model: str | None = None,
    ollama_base: str | None = None,
) -> Any:
    """Build an ``LLMService`` bound to the requested provider and model.

    The base core LLM config is cloned (never mutated) so a per-agent provider
    choice cannot leak into the process-wide service. Credentials remain inside
    the cloned ``SecretStr`` field — they are never read or logged here.

    Args:
        provider: Target backend.
        model: Optional explicit model id; provider default applied when None.
        ollama_base: Optional base URL override for a local Ollama daemon.

    Returns:
        A configured ``LLMService`` instance.

    Raises:
        ProviderUnavailableError: If the core LLM service cannot be imported or
            the provider is missing required credentials.
    """
    try:
        from core.config import get_llm_config
        from core.services.llm.service import LLMService
    except ImportError as exc:  # pragma: no cover - core always present in app
        raise ProviderUnavailableError(
            "core LLM service is unavailable; ensure the framework is installed"
        ) from exc

    base = get_llm_config()
    resolved_model = model or _DEFAULT_MODELS[provider]
    update: dict[str, Any] = {"provider": provider.value, "model": resolved_model}

    if provider is ModelProvider.OLLAMA:
        # Local provider: prefer an explicit base, else keep the configured one.
        update["api_base"] = ollama_base or base.api_base
    elif base.api_key is None:
        # Remote providers need a key; fail loud rather than 500 mid-generation.
        raise ProviderUnavailableError(
            f"provider '{provider.value}' requires an API key (set LLM_API_KEY)"
        )

    cloned = base.model_copy(update=update)
    logger.info("provider_resolved", provider=provider.value, model=resolved_model)
    return LLMService(config=cloned)
