"""HTTP request/response payloads for the platform API.

Domain models (:mod:`.types`) are already Pydantic and serve directly as
response bodies; this module only adds the inbound request shapes so the router
stays declarative and free of inline validation.
"""

from __future__ import annotations

from pydantic import BaseModel, Field

from .types import AgentCapability

__all__ = [
    "CreateBlueprintRequest",
    "RunAgentRequest",
    "ScheduleRequest",
    "HealthResponse",
]


class CreateBlueprintRequest(BaseModel):
    """Request to synthesise an agent from natural language."""

    description: str = Field(
        ...,
        min_length=3,
        max_length=2000,
        description="Natural-language description of the desired agent.",
    )


class RunAgentRequest(BaseModel):
    """Request to execute one capability of a registered agent."""

    capability: AgentCapability = Field(
        ..., description="The action to perform; must be within the agent's scope."
    )
    task: str = Field(
        ...,
        min_length=1,
        max_length=8000,
        description="The instruction, description, or error message to act on.",
    )
    code: str = Field(
        default="",
        max_length=40000,
        description="Source code context for fix/test capabilities.",
    )


class ScheduleRequest(BaseModel):
    """Request to register a recurring agent run."""

    capability: AgentCapability = Field(
        ..., description="The action to run on each tick (must be in scope)."
    )
    task: str = Field(..., min_length=1, max_length=8000)
    interval_seconds: float = Field(
        ...,
        ge=5.0,
        le=604800.0,
        description="Seconds between runs (5s … 7 days).",
    )


class HealthResponse(BaseModel):
    """Liveness/readiness payload for the platform."""

    plugin: str
    version: str
    doc_namespaces: int
