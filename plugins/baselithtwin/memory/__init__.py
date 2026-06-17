"""Long-term memory subsystem: salient-fact extraction and retrieval."""

from __future__ import annotations

from .facts import extract_facts
from .ltm import LTMIndex

__all__ = ["extract_facts", "LTMIndex"]
