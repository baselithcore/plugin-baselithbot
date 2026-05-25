from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class BaseStreamEvent(BaseModel):
    """Base class for all streaming events."""

    event_type: str


class TokenEvent(BaseStreamEvent):
    """Event containing a text token/chunk."""

    event_type: Literal["token"] = "token"
    text: str


class StatusEvent(BaseStreamEvent):
    """Event containing a status update or progress block."""

    event_type: Literal["status"] = "status"
    message: str
    step: Optional[str] = None
    agent: Optional[str] = None
    progress: Optional[float] = None  # 0.0 to 1.0


class FinalPayloadEvent(BaseStreamEvent):
    """Event containing the final consolidated result."""

    event_type: Literal["final_payload"] = "final_payload"
    answer: str
    sources: List[Dict[str, Any]] = Field(default_factory=list)
    project_plan: Optional[Dict[str, Any]] = None
    jira_issues: List[Dict[str, Any]] = Field(default_factory=list)
    created_jira_issues: List[Dict[str, Any]] = Field(default_factory=list)
    duration: Optional[float] = None
    suggested_actions: List[Dict[str, Any]] = Field(default_factory=list)


class ErrorEvent(BaseStreamEvent):
    """Event containing an error message."""

    event_type: Literal["error"] = "error"
    message: str
    code: Optional[str] = None


def format_event(event: BaseStreamEvent) -> str:
    """Serialize event to JSON string for streaming (NDJSON format)."""
    return event.model_dump_json() + "\n"
