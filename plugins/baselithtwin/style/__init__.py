"""Communicative-style extraction subsystem."""

from __future__ import annotations

from .extractor import extract_style
from .models import StyleExemplar, StyleMetrics, StyleProfile

__all__ = ["extract_style", "StyleProfile", "StyleMetrics", "StyleExemplar"]
