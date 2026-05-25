"""Modular LLM Report Generation Module.

Provides structured, maintainable LLM-powered report generation with:
- Separate generators for each report section
- Reusable prompt builders
- Fallback handlers for robustness
"""

from .service import ModularReportLLMService

__all__ = ["ModularReportLLMService"]
