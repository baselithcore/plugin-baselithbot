from __future__ import annotations

import json
import os
from importlib import import_module
from pathlib import Path
from typing import Callable, Optional

from agent_jira.chat.dependencies import (
    ChatDependencies,
    ChatDependencyConfig,
    create_default_dependencies,
)
from agent_jira.chat.service import ChatService

FACTORY_ENV_VAR = "CHAT_SERVICE_FACTORY"
CONFIG_ENV_VAR = "CHAT_SERVICE_CONFIG_FILE"


def create_chat_service_from_config(
    config: Optional[ChatDependencyConfig] = None,
    *,
    dependencies_factory: Optional[
        Callable[[Optional[ChatDependencyConfig]], ChatDependencies]
    ] = None,
) -> ChatService:
    dependencies_builder = dependencies_factory or create_default_dependencies
    dependencies = _invoke_dependencies_factory(dependencies_builder, config)
    return ChatService(dependencies=dependencies)


def load_chat_dependency_config(path: Path) -> ChatDependencyConfig:
    raw = path.read_text(encoding="utf-8")
    payload = json.loads(raw)
    if not isinstance(payload, dict):
        raise ValueError(
            f"Il file di configurazione '{path}' deve contenere un oggetto JSON."
        )
    return ChatDependencyConfig.from_mapping(payload)


def resolve_chat_service(
    *,
    factory_path: Optional[str] = None,
    config_path: Optional[Path] = None,
) -> ChatService:
    config = _load_config_from_path(config_path)

    factory_callable = _load_factory(factory_path)
    return _invoke_service_factory(factory_callable, config)


def _load_config_from_path(
    config_path: Optional[Path],
) -> Optional[ChatDependencyConfig]:
    path = config_path
    if path is None:
        env_value = os.getenv(CONFIG_ENV_VAR)
        if env_value:
            path = Path(env_value).expanduser()
    if path is None:
        return None
    if not path.exists():
        raise FileNotFoundError(f"File di configurazione '{path}' non trovato.")
    return load_chat_dependency_config(path)


def _load_factory(factory_path: Optional[str]) -> Callable[..., ChatService]:
    path = factory_path or os.getenv(FACTORY_ENV_VAR)
    if not path:
        return create_chat_service_from_config
    module_name, attr_name = _split_import_path(path)
    module = import_module(module_name)
    candidate = getattr(module, attr_name)
    if not callable(candidate):
        raise TypeError(
            f"Il factory specificato '{path}' non è invocabile (ottenuto {type(candidate)!r})."
        )
    return candidate


def _split_import_path(dotted_path: str) -> tuple[str, str]:
    if ":" in dotted_path:
        module_name, attr_name = dotted_path.rsplit(":", 1)
    else:
        module_name, attr_name = dotted_path.rsplit(".", 1)
    return module_name, attr_name


def _invoke_service_factory(
    factory: Callable[..., ChatService],
    config: Optional[ChatDependencyConfig],
) -> ChatService:
    try:
        if config is None:
            return factory()
        return factory(config=config)
    except TypeError as first_exc:
        try:
            if config is None:
                return factory(config=None)
            return factory(config)
        except TypeError as second_exc:
            if config is not None:
                raise TypeError(
                    "Il factory di ChatService deve accettare facoltativamente un argomento 'config'."
                ) from second_exc
            raise TypeError(
                "Il factory di ChatService deve essere invocabile senza argomenti."
            ) from first_exc


def _invoke_dependencies_factory(
    factory: Callable[[Optional[ChatDependencyConfig]], ChatDependencies],
    config: Optional[ChatDependencyConfig],
) -> ChatDependencies:
    try:
        return factory(config=config)
    except TypeError:
        if config is None:
            return factory(None)
        return factory(config)


__all__ = [
    "create_chat_service_from_config",
    "load_chat_dependency_config",
    "resolve_chat_service",
]
