"""Models describing a learned communicative style.

A :class:`StyleProfile` is the compact, explainable fingerprint of how the owner
writes — quantitative metrics plus a few-shot exemplar set — that the prompt
assembler injects so generated replies sound like the owner rather than a
generic assistant.
"""

from __future__ import annotations

from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict, Field


class StyleExemplar(BaseModel):
    """A short representative snippet of the owner's writing for few-shot priming."""

    model_config = ConfigDict(frozen=True)

    text: str
    contact_id: str | None = None


class StyleMetrics(BaseModel):
    """Quantitative style signals distilled from the owner's message history."""

    model_config = ConfigDict(frozen=True)

    avg_message_chars: float = 0.0
    avg_words_per_message: float = 0.0
    emoji_rate: float = 0.0  # emoji per message.
    question_rate: float = 0.0  # share of messages ending with '?'.
    exclamation_rate: float = 0.0
    uppercase_ratio: float = 0.0  # share of all-caps tokens.
    formality: float = 0.5  # 0 = very casual, 1 = very formal (heuristic).
    top_emojis: list[str] = Field(default_factory=list)
    top_expressions: list[str] = Field(default_factory=list)
    dominant_locale: str = "en"


class StyleProfile(BaseModel):
    """The full learned style fingerprint for one owner."""

    model_config = ConfigDict(frozen=True)

    owner_id: str
    sample_size: int = 0
    trained: bool = False
    metrics: StyleMetrics = Field(default_factory=StyleMetrics)
    exemplars: list[StyleExemplar] = Field(default_factory=list)
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


__all__ = ["StyleProfile", "StyleMetrics", "StyleExemplar"]
