"""Modular Prompt Library for Report Generation.

Organized collection of LLM prompts for different report sections.
"""

# Vulnerability & CVE prompts
from .vulnerability_prompts import (
    vulnerability_analysis_prompt,
    cve_exploitation_analysis_prompt,
)

# Threat Intelligence prompts
from .threat_intel_prompts import (
    attack_pattern_analysis_prompt,
    botnet_intelligence_prompt,
    geographic_threat_analysis_prompt,
    threat_actor_attribution_prompt,
)

# Incident & Timeline prompts
from .incident_prompts import incident_timeline_narrative_prompt

# Compliance & Risk prompts
from .compliance_prompts import (
    compliance_assessment_prompt,
    executive_risk_briefing_prompt,
)

# Custom section prompts
from .custom_prompts import get_custom_section_prompt

# Research report prompts (enterprise-grade)
from .research_report_prompts import (
    RESEARCH_ANALYST_PERSONA,
    research_abstract_prompt,
    research_key_findings_prompt,
    research_mitre_mapping_prompt,
    research_payload_analysis_prompt,
    research_conclusions_prompt,
    research_trend_analysis_prompt,
)

__all__ = [
    # Vulnerability
    "vulnerability_analysis_prompt",
    "cve_exploitation_analysis_prompt",
    # Threat Intelligence
    "attack_pattern_analysis_prompt",
    "botnet_intelligence_prompt",
    "geographic_threat_analysis_prompt",
    "threat_actor_attribution_prompt",
    # Incident
    "incident_timeline_narrative_prompt",
    # Compliance
    "compliance_assessment_prompt",
    "executive_risk_briefing_prompt",
    # Custom
    "get_custom_section_prompt",
    # Research (enterprise-grade)
    "RESEARCH_ANALYST_PERSONA",
    "research_abstract_prompt",
    "research_key_findings_prompt",
    "research_mitre_mapping_prompt",
    "research_payload_analysis_prompt",
    "research_conclusions_prompt",
    "research_trend_analysis_prompt",
]
