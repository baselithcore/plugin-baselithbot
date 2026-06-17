"""BaselithCore Agents Platform plugin.

Create complex, scope-bounded coding agents from natural language, run them on
Claude / OpenAI / local Ollama models, and ground every run in the framework's
own documentation over MCP — so agents build autonomously without drifting out
of scope.
"""

from __future__ import annotations

from .plugin import AgentsPlatformPlugin
from .service import AgentPlatformService
from .types import (
    AgentBlueprint,
    AgentCapability,
    AgentRunResult,
    BlueprintScope,
    ModelProvider,
    RunStatus,
)

__all__ = [
    "AgentsPlatformPlugin",
    "AgentPlatformService",
    "AgentBlueprint",
    "AgentCapability",
    "AgentRunResult",
    "BlueprintScope",
    "ModelProvider",
    "RunStatus",
]
