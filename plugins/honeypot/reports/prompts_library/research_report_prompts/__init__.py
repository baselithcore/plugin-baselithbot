"""Research Report Prompts package.

Enterprise-grade threat intelligence prompts following MITRE ATT&CK,
SANS, and NIST standards.
"""

from ._core import (
    RESEARCH_ANALYST_PERSONA,
    research_abstract_prompt,
    research_conclusions_prompt,
    research_key_findings_prompt,
    research_mitre_mapping_prompt,
)
from ._narrative_prompts import (
    research_attack_narrative_prompt,
    research_trend_analysis_prompt,
)
from ._payload_prompts import research_payload_analysis_prompt

__all__ = [
    "RESEARCH_ANALYST_PERSONA",
    "research_abstract_prompt",
    "research_key_findings_prompt",
    "research_mitre_mapping_prompt",
    "research_payload_analysis_prompt",
    "research_conclusions_prompt",
    "research_trend_analysis_prompt",
    "research_attack_narrative_prompt",
]
