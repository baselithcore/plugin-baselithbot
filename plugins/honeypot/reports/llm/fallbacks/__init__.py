"""Fallback handlers for LLM report generation."""

from .handlers import (
    fallback_executive_summary,
    fallback_threat_analysis,
    fallback_recommendations,
    fallback_ioc_analysis,
)

__all__ = [
    "fallback_executive_summary",
    "fallback_threat_analysis",
    "fallback_recommendations",
    "fallback_ioc_analysis",
]
