"""
ConfessGPT — Pydantic models for the sacrament state machine.

The confessor never persists penitent content. Models are ephemeral and
live only in process memory for the duration of one session.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class RitePhase(str, Enum):
    """Phases of the Rite of Reconciliation (Roman, post-Vatican II)."""

    ACCOGLIENZA = "ACCOGLIENZA"
    INVITO = "INVITO"
    ASCOLTO = "ASCOLTO"
    ESORTAZIONE = "ESORTAZIONE"
    PENITENZA = "PENITENZA"
    ATTO_DOLORE = "ATTO_DOLORE"
    VERIFICA_CONTRIZIONE = "VERIFICA_CONTRIZIONE"
    ASSOLUZIONE = "ASSOLUZIONE"
    CONGEDO = "CONGEDO"
    INVITO_RIFLESSIONE = "INVITO_RIFLESSIONE"


class ConfessorTurn(BaseModel):
    """Single confessor utterance with phase metadata.

    This is what the LLM returns and what the router emits per turn.
    """

    model_config = ConfigDict(extra="forbid")

    phase: RitePhase
    utterance: str = Field(min_length=1, max_length=2000)
    next_phase: RitePhase
    advance_on_user_reply: bool = True
    contrition_detected: bool | None = None
    amendment_purpose_detected: bool | None = None
    explicit_refusal_of_repentance: bool = False
    rationale: str = ""


class SessionState(BaseModel):
    """In-memory session state. Never persisted, never logged in clear."""

    model_config = ConfigDict(extra="forbid")

    session_id: str
    current_phase: RitePhase = RitePhase.ACCOGLIENZA
    contrition_detected: bool | None = None
    amendment_purpose_detected: bool | None = None
    explicit_refusal_of_repentance: bool = False
    turn_count: int = 0
    # Phase visit counters — used to break liturgical loops when the
    # LLM keeps the rite stuck on a single step.
    atto_dolore_attempts: int = 0
    ascolto_attempts: int = 0
    closed: bool = False


class TurnRequest(BaseModel):
    """Penitent input for a single turn."""

    session_id: str
    utterance: str = Field(default="", max_length=8000)


class TurnResponse(BaseModel):
    """Confessor response payload returned by the router."""

    session_id: str
    phase: RitePhase
    utterance: str
    next_phase: RitePhase
    advance_on_user_reply: bool
    closed: bool = False
    audio_base64: str | None = None
    audio_mime: str | None = None


class SessionCreateRequest(BaseModel):
    """Optional session creation parameters."""

    voice_enabled: bool = False
    voice_name: str | None = None


class SessionCreateResponse(BaseModel):
    """Session creation result."""

    session_id: str
    opening_phase: Literal[RitePhase.ACCOGLIENZA] = RitePhase.ACCOGLIENZA
