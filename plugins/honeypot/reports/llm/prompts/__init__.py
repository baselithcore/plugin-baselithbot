"""Prompt builders for LLM report generation."""

from .builders import (
    build_executive_summary_prompt,
    build_recommendations_prompt,
    build_research_insights_prompt,
    build_ioc_analysis_prompt,
)

from .research_prompts import (
    build_abstract_prompt,
    build_key_findings_prompt,
    build_mitre_attack_prompt,
    build_methodology_section,
    build_statistical_analysis_prompt,
    build_trend_analysis_prompt,
    build_references_section,
    build_appendix_prompt,
)

__all__ = [
    # Core prompts
    "build_executive_summary_prompt",
    "build_recommendations_prompt",
    "build_research_insights_prompt",
    "build_ioc_analysis_prompt",
    # Advanced research prompts
    "build_abstract_prompt",
    "build_key_findings_prompt",
    "build_mitre_attack_prompt",
    "build_methodology_section",
    "build_statistical_analysis_prompt",
    "build_trend_analysis_prompt",
    "build_references_section",
    "build_appendix_prompt",
]
