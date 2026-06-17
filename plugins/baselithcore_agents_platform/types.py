"""Typed domain model for the BaselithCore Agents Platform.

This module is the single source of truth for the plugin's data shapes. It is
deliberately free of I/O and framework imports so it can be reused by the
builder, runtime, MCP bridge, and API layers without creating import cycles.

The public surface is split into three concerns:
    * Enumerations — closed vocabularies (providers, capabilities, run state).
    * Blueprints — the validated specification synthesised from natural language.
    * Results — the immutable record produced by a single agent run.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator

__all__ = [
    "ModelProvider",
    "AgentCapability",
    "RunStatus",
    "BlueprintScope",
    "AgentBlueprint",
    "DocCitation",
    "AgentRunResult",
    "ScheduleSpec",
    "utcnow",
]


def utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp (avoids naive-datetime drift)."""
    return datetime.now(timezone.utc)


class ModelProvider(str, Enum):
    """Coding model backends the platform can route to.

    The values map onto the framework's native ``LLMConfig.provider`` literals,
    so a blueprint can be lowered onto the core LLM service without translation.
    """

    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    OLLAMA = "ollama"


class AgentCapability(str, Enum):
    """Discrete actions a synthesised agent is permitted to perform.

    Capabilities double as a scope-control primitive: the runtime refuses any
    request whose capability is absent from the blueprint's allow-list.
    """

    GENERATE = "generate"
    FIX = "fix"
    TEST = "test"
    REFACTOR = "refactor"
    EXPLAIN = "explain"
    OPERATE = "operate"


class RunStatus(str, Enum):
    """Lifecycle state of an agent run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    REJECTED = "rejected"


class BlueprintScope(BaseModel):
    """Hard guardrails that bound what a synthesised agent may do.

    The scope is the security contract of the platform: it is enforced by the
    runtime on every invocation, never advisory. Keeping it as a frozen model
    means a blueprint cannot be silently widened after synthesis.
    """

    model_config = {"frozen": True}

    capabilities: list[AgentCapability] = Field(
        default_factory=lambda: [AgentCapability.GENERATE],
        description="Closed set of actions this agent may perform.",
    )
    doc_namespaces: list[str] = Field(
        default_factory=list,
        description=(
            "Documentation namespaces (path prefixes) the agent is grounded "
            "in. Empty means the full indexed corpus is available."
        ),
    )
    allowed_tools: list[str] = Field(
        default_factory=list,
        description=(
            "Runtime tools the agent may call during an 'operate' run "
            "(e.g. http_get, send_telegram, now). Empty disables tool use."
        ),
    )
    max_iterations: int = Field(
        default=3,
        ge=1,
        le=10,
        description="Upper bound on the auto-debug fix loop.",
    )
    language: str = Field(
        default="python",
        description="Primary target language for generated code.",
    )
    allow_execution: bool = Field(
        default=True,
        description="Whether generated code may be run in the core sandbox.",
    )

    @field_validator("capabilities")
    @classmethod
    def _non_empty(cls, value: list[AgentCapability]) -> list[AgentCapability]:
        """An agent with no capabilities is meaningless — reject it early."""
        if not value:
            raise ValueError("scope.capabilities must declare at least one capability")
        return value


class AgentBlueprint(BaseModel):
    """Validated specification of an agent distilled from natural language.

    A blueprint is provider-agnostic and fully serialisable: it is the artefact
    persisted by the registry and handed to the runtime. The ``source_prompt``
    field preserves provenance for audit and reproducibility.
    """

    id: str = Field(..., description="Stable slug identifier (kebab-case).")
    name: str = Field(..., min_length=1, max_length=80)
    description: str = Field(default="", max_length=500)
    system_directive: str = Field(
        default="",
        max_length=4000,
        description="Persona/system prompt steering the underlying model.",
    )
    provider: ModelProvider = Field(default=ModelProvider.OLLAMA)
    model: str | None = Field(
        default=None,
        description="Optional explicit model id; None uses provider default.",
    )
    scope: BlueprintScope = Field(default_factory=BlueprintScope)
    tags: list[str] = Field(default_factory=list)
    source_prompt: str = Field(
        default="",
        description="Original natural-language request the blueprint was built from.",
    )
    created_at: datetime = Field(default_factory=utcnow)

    @field_validator("id")
    @classmethod
    def _slug(cls, value: str) -> str:
        """Enforce a filesystem- and URL-safe identifier."""
        normalized = value.strip().lower()
        if not normalized or not all(c.isalnum() or c in "-_" for c in normalized):
            raise ValueError("id must be a non-empty kebab/snake-case slug")
        return normalized


class DocCitation(BaseModel):
    """A single documentation source that grounded an agent run."""

    namespace: str = Field(..., description="Relative doc path, e.g. 'CLAUDE.md'.")
    snippet: str = Field(default="", max_length=600)
    score: float = Field(default=0.0, ge=0.0)


class AgentRunResult(BaseModel):
    """Immutable record of one agent invocation.

    Carries everything the UI and audit log need: the produced artefact, the
    documentation that grounded it, and the failure detail when unsuccessful.
    """

    run_id: str
    blueprint_id: str
    capability: AgentCapability
    status: RunStatus
    output: str = Field(default="", description="Generated/transformed code or prose.")
    explanation: str = Field(default="")
    iterations: int = Field(default=0, ge=0)
    error: str | None = Field(default=None)
    citations: list[DocCitation] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Run telemetry (e.g. loop-budget snapshot, model id).",
    )
    created_at: datetime = Field(default_factory=utcnow)


class ScheduleSpec(BaseModel):
    """A recurring agent run on a fixed interval.

    Drives the interval scheduler: every ``interval_seconds`` the named
    capability is executed against ``task``. Bookkeeping fields record the last
    outcome so the dashboard can surface health without a separate run lookup.
    """

    id: str = Field(..., description="Schedule identifier (uuid hex).")
    blueprint_id: str
    capability: AgentCapability
    task: str = Field(..., min_length=1, max_length=8000)
    interval_seconds: float = Field(..., ge=5.0, le=604800.0)
    enabled: bool = Field(default=True)
    runs: int = Field(default=0, ge=0)
    last_run_at: datetime | None = Field(default=None)
    last_status: RunStatus | None = Field(default=None)
    last_error: str | None = Field(default=None)
    created_at: datetime = Field(default_factory=utcnow)
