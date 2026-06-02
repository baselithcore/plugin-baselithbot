"""
ConfessGPT plugin entrypoint.

Wires together the LLM service, the sigillum-aware session store, the
voice bridge, and the FastAPI router into a single plugin registered
with the core ``PluginRegistry``. Domain logic lives in the
``flow``/``sigillum``/``voice_bridge`` modules; this file only composes.

Sacred-Core compliance:
- This file imports only from ``core/`` and from sibling plugin
  modules. No reverse imports from other plugins.
- All sacramental state is held in-memory by ``SigillumStore`` and is
  wiped on shutdown to honor CCC §1467.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fastapi import APIRouter

from core.observability.logging import get_logger
from core.plugins import AgentPlugin, RouterPlugin
from core.services.voice import VoiceProvider, VoiceService

from .flow import ConfessionFlow
from .llm_adapter import LLMServiceBackend, build_llm_service
from .prompt import load_system_prompt
from .sigillum import SigillumStore
from .voice_bridge import VoiceBridge

logger = get_logger(__name__)


class ConfessGptPlugin(AgentPlugin, RouterPlugin):
    """Sacramental confessor agent for BaselithCore."""

    def __init__(self) -> None:
        super().__init__()
        self.store: SigillumStore | None = None
        self.flow: ConfessionFlow | None = None
        self.voice_bridge: VoiceBridge | None = None
        self.model_id: str | None = None
        self._system_prompt: str = ""
        self._llm_backend: LLMServiceBackend | None = None

    async def initialize(self, config: dict[str, Any]) -> None:
        await super().initialize(config)

        self._system_prompt = load_system_prompt()
        self.store = SigillumStore()

        model_id = config.get("model_id") or os.getenv("CONFESSGPT_MODEL_ID")
        self.model_id = model_id

        llm_service = build_llm_service(enable_cache=False)
        self._llm_backend = LLMServiceBackend(service=llm_service, model_id=model_id)
        self.flow = ConfessionFlow(
            store=self.store,
            llm=self._llm_backend,
            system_prompt=self._system_prompt,
        )

        self.voice_bridge = _build_voice_bridge(config)

        logger.info(
            "confessgpt_initialized",
            voice_enabled=self.voice_bridge is not None,
            model_id=model_id,
        )

    async def shutdown(self) -> None:
        # Wipe every session before tearing down: sigillum holds even
        # on graceful exit.
        if self.store is not None:
            await self.store.close_all()
        self.store = None
        self.flow = None
        self.voice_bridge = None
        await super().shutdown()

    # -- AgentPlugin -------------------------------------------------------

    def create_agent(self, service: Any, **kwargs: Any) -> Any:
        """ConfessGPT is a flow-driven plugin; no standalone agent object."""
        del service, kwargs
        return None

    def get_agents(self) -> list[Any]:
        return []

    def get_intent_patterns(self) -> list[dict[str, Any]]:
        # Italian-first intent patterns. The orchestrator can route a
        # plain-text request to the confessor when the user explicitly
        # asks for confession. Sacred Core fan-out happens upstream.
        return [
            {
                "name": "confessgpt_open",
                "patterns": [
                    "voglio confessarmi",
                    "mi voglio confessare",
                    "padre, ascoltami",
                    "benedicimi padre",
                    "vorrei confessione",
                ],
                "handler": "open",
                "priority": 200,
            }
        ]

    # -- RouterPlugin ------------------------------------------------------

    def create_router(self) -> APIRouter:
        # Import here so the router module never executes at plugin
        # import-time — keeps the load order clean and Sacred-Core
        # boundary checks satisfied.
        from .router import create_router

        return create_router(self)

    def get_config_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "model_id": {
                    "type": "string",
                    "description": (
                        "Override LLM model id used for the confessor. "
                        "Falls back to the global LLM service default."
                    ),
                },
                "voice": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean", "default": True},
                        "provider": {
                            "type": "string",
                            "enum": [p.value for p in VoiceProvider],
                        },
                        "voice_name": {"type": "string"},
                        "speed": {
                            "type": "number",
                            "minimum": 0.25,
                            "maximum": 4.0,
                        },
                    },
                },
            },
        }

    def get_ui_tabs(self) -> list[dict[str, str]]:
        return [{"id": "confessgpt", "label": "Confessionale"}]

    def get_static_assets_path(self) -> Path | None:
        """Mount the ``ui/`` SPA at ``/confessgpt/`` and ``/plugins/confessgpt/static/``.

        The core lifespan helper auto-detects ``index.html`` and creates
        an SPA mount in addition to the raw static mount.
        """
        return _UI_DIR if _UI_DIR.exists() else None


def _build_voice_bridge(config: dict[str, Any]) -> VoiceBridge | None:
    """Instantiate the voice bridge, or None if voice is disabled."""
    voice_cfg = config.get("voice") if isinstance(config, dict) else None
    voice_cfg = voice_cfg if isinstance(voice_cfg, dict) else {}
    enabled = voice_cfg.get("enabled", True)
    if not enabled:
        return None

    provider_str = voice_cfg.get("provider") or os.getenv("CONFESSGPT_VOICE_PROVIDER")
    provider: VoiceProvider | None = None
    if provider_str:
        try:
            provider = VoiceProvider(provider_str)
        except ValueError:
            logger.warning("confessgpt_voice_unknown_provider", provider=provider_str)
            provider = None

    voice_name = voice_cfg.get("voice_name") or os.getenv("CONFESSGPT_VOICE_NAME")
    speed = voice_cfg.get("speed")

    try:
        service = VoiceService(default_provider=provider or VoiceProvider.OPENAI)
    except Exception as exc:  # noqa: BLE001
        logger.warning("confessgpt_voice_init_failed", error=str(exc)[:200])
        return None

    return VoiceBridge(
        service=service,
        voice_name=voice_name,
        voice_speed=float(speed) if speed is not None else VoiceBridge.DEFAULT_SPEED,
        provider=provider,
    )


# Surface a default prompt path for offline tooling that wants to
# render the system prompt without importing the plugin.
SYSTEM_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "system_confessor.md"

# UI bundle directory — React+Vite SPA, compiled into ``ui/dist`` by
# ``npm run build``. The lifespan helper auto-mounts the SPA at
# ``/confessgpt/`` and the raw assets at ``/plugins/confessgpt/static``.
_UI_DIR = Path(__file__).resolve().parent / "ui" / "dist"
