"""Cognitive core: reply-draft generation and persona prompt assembly."""

from __future__ import annotations

from .engine import DraftEngine
from .prompt import build_system_prompt, build_user_prompt

__all__ = ["DraftEngine", "build_system_prompt", "build_user_prompt"]
