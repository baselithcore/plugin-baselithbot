"""Prompt Builders for LLM Report Generation.

Constructs research-focused prompts for honeypot attack pattern analysis.
"""

import json
from typing import Dict, Any, Optional

from ...models import ReportType


def build_executive_summary_prompt(
    context: Dict[str, Any],
    report_type: ReportType,
    org_name: Optional[str] = None,
) -> str:
    """Build LLM prompt for research-focused executive summary.

    Args:
        context: Report context data
        report_type: Type of report
        org_name: Organization name

    Returns:
        Formatted prompt string
    """
    org = org_name or "the research environment"
    period = f"{context.get('time_range', 'the observation period')}"

    # Extract target infrastructure if available
    target_infra = ""
    if "target_infrastructure" in context:
        ti = context["target_infrastructure"]
        tags_str = ", ".join(ti.get("tags", []))
        target_infra = f"""
**Targeted Infrastructure Analysis:**
- **System:** {ti.get("name")}
- **Service Type:** {ti.get("type")}
- **Structure:** {ti.get("description")}
- **Classification Tags:** {tags_str}
"""

    # Extract payload samples if available
    payload_context = ""
    if "attack_samples" in context and context["attack_samples"]:
        samples_list = "\n".join(
            [
                f"  - **{s['category'].upper()}** [{s['severity']}] from {s['source_country']}: `{s['payload_preview'][:100]}...`"
                for s in context["attack_samples"]
            ]
        )
        payload_context = f"""
**Representative Attack Samples:**
{samples_list}

Use these payload examples to explain SPECIFIC attack techniques in your analysis.
"""

    base_prompt = f"""You are a cybersecurity researcher writing an academic-style analysis of honeypot data. Generate a research summary for attack pattern analysis.

**Collected Data Context:**
{json.dumps(context, indent=2)}

**Research Environment:** {org}
**Observation Period:** {period}{target_infra}
{payload_context}

"""

    # Add type-specific instructions
    if report_type == ReportType.EXECUTIVE:
        base_prompt += _get_research_executive_instructions()
    elif report_type == ReportType.THREAT_INTEL:
        base_prompt += _get_threat_research_instructions()
    elif report_type == ReportType.COMPLIANCE:
        base_prompt += _get_compliance_research_instructions()
    else:  # TECHNICAL, INCIDENT, PENTEST
        base_prompt += _get_technical_research_instructions()

    base_prompt += "\n\nGenerate the research summary now:"
    return base_prompt


def _get_research_executive_instructions() -> str:
    """Get instructions for research executive summaries."""
    return """**Audience:** Security researchers and academic reviewers
**Style:** Academic, analytical, objective
**Focus:** Key findings, notable patterns, research significance

**Instructions:**
1. Start with a data collection overview (total events, unique sources)
2. Summarize the most significant attack patterns observed
3. Highlight notable behavioral characteristics worth studying
4. Discuss the research value of the collected data
5. Use objective, analytical language (avoid alarmist terms)
6. Use markdown formatting with proper headers (##, ###)
7. Be concise (200-300 words)

**Format:**
## Research Overview

### Data Collection Summary

[Your analysis here - focus on patterns and findings, not risks]

**CRITICAL FORMATTING RULES:**
- Start each paragraph with PROSE, NOT bullet points
- Only use bullet points for lists WITHIN paragraphs
- Write in complete sentences and paragraphs
- Example CORRECT format:
  "The top attack methods identified during this observation included several distinct patterns. Exploit attempts against known vulnerabilities were predominant, followed by path traversal attacks. Additionally, unclassified attack methods were detected, indicating novel or custom attack strategies."
- Example WRONG format:
  "• Exploit Attempts: These were predominant..."
"""


def _get_threat_research_instructions() -> str:
    """Get instructions for threat intelligence research reports."""
    return """**Audience:** Threat intelligence researchers and academics
**Style:** Analytical, data-driven, objective
**Focus:** Attack patterns, behavioral analysis, campaign characteristics

**Instructions:**
1. Analyze observed attack patterns and techniques
2. Identify behavioral signatures and coordination patterns
3. Discuss botnet architecture and C&C communication patterns
4. Examine geographic distribution patterns
5. Use research terminology (pattern analysis, behavioral clustering, temporal correlation)
6. Use markdown with headers and bullet points
7. Be detailed but objective (300-400 words)

**Format:**
## Attack Pattern Research Findings

[Your analysis here - focus on patterns and academic insights]

**CRITICAL FORMATTING RULES:**
- Write in full paragraphs, NOT bullet lists
- Start each section with prose that explains the pattern
- Reference specific payload examples when available (e.g., "As seen in the SQL injection payload '...'")
- Only use bullet points for sub-items within a paragraph, not as paragraph starters
"""


def _get_compliance_research_instructions() -> str:
    """Get instructions for compliance-oriented research reports."""
    return """**Audience:** Security researchers focused on detection methodologies
**Style:** Formal, methodology-focused
**Focus:** Detection patterns, logging analysis, classification accuracy

**Instructions:**
1. Analyze event categorization accuracy and patterns
2. Discuss detection methodology effectiveness
3. Examine event classification distribution
4. Evaluate logging completeness for research
5. Use formal research language
6. Use markdown with headers and lists
7. Be thorough (250-350 words)

**Format:**
## Detection Methodology Analysis

[Your analysis here]

**CRITICAL FORMATTING RULES:**
- Write in full paragraphs with proper narrative flow
- Begin sections with explanatory prose
- Use bullet points only for listing items within a larger paragraph
"""


def _get_technical_research_instructions() -> str:
    """Get instructions for technical research reports."""
    return """**Audience:** Security researchers and technical analysts
**Style:** Technical, detailed, academic
**Focus:** Attack techniques, protocol analysis, behavioral patterns

**Instructions:**
1. Analyze the technical characteristics of observed attacks
2. Provide detailed protocol and technique breakdowns
3. Identify patterns in attack vectors and methodologies
4. Include statistical analysis of attack characteristics
5. Use technical security research terminology
6. Use markdown with headers and bullet points
7. Be detailed (300-400 words)
8. Focus on "what we observe" not "what you should do"

**Format:**
## Technical Analysis Findings

### Attack Characteristics Overview

[Your analysis here - organized with subheadings and data points]

**CRITICAL FORMATTING RULES:**
- Every section must start with a complete paragraph of prose
- Reference specific attack payloads to illustrate technical points
- Bullet points are ONLY for sub-items, never as first-level content
- Example: "The observed attacks demonstrated sophisticated command injection techniques. Analysis of captured payloads revealed the use of shell metacharacters and encoded strings to bypass basic input validation."
"""


def build_research_insights_prompt(
    context: Dict[str, Any],
    report_type: ReportType,
) -> str:
    """Build prompt for research insights section (replaces recommendations).

    Args:
        context: Report context data
        report_type: Type of report

    Returns:
        Formatted prompt string
    """
    return f"""You are a cybersecurity researcher. Based on the following honeypot data, generate research insights and suggestions for future study.

**Collected Data Context:**
{json.dumps(context, indent=2)}

**Report Type:** {report_type.value}

**Instructions:**
1. Provide 4-6 key research insights from the data
2. Each insight should highlight an interesting pattern or behavior
3. Suggest areas for deeper investigation
4. Discuss potential research questions raised by the data
5. Use markdown bullet points
6. Each insight should be 1-2 sentences
7. Focus on "what this data tells us" not "what to fix"

**Format:**
### Research Insights & Future Directions

- **Pattern Observation:** Description of an interesting pattern
- **Behavioral Insight:** What this suggests about attacker behavior
- **Research Question:** A question raised by this data
...

Generate research insights now:"""


# Keep the old function name as an alias for backward compatibility
def build_recommendations_prompt(
    context: Dict[str, Any],
    report_type: ReportType,
) -> str:
    """Build prompt for recommendations/insights section.

    Now generates research insights instead of security recommendations.
    Kept for backward compatibility.

    Args:
        context: Report context data
        report_type: Type of report

    Returns:
        Formatted prompt string
    """
    return build_research_insights_prompt(context, report_type)


def build_ioc_analysis_prompt(context: Dict[str, Any]) -> str:
    """Build prompt for IOC pattern analysis section.

    Args:
        context: IOC context data

    Returns:
        Formatted prompt string
    """
    return f"""You are a threat intelligence researcher. Analyze the following Indicators of Compromise (IOCs) from a research perspective.

**IOC Data:**
{json.dumps(context, indent=2)}

**Instructions:**
1. Categorize IOCs by type and prevalence
2. Identify clustering patterns and relationships
3. Analyze temporal and geographic distributions
4. Discuss what these patterns reveal about attack campaigns
5. Highlight IOCs that exhibit interesting characteristics
6. Use markdown formatting
7. Be analytical and objective (200-300 words)

**Format:**
### IOC Pattern Analysis

#### Distribution Overview
[Statistical breakdown of IOC types]

#### Clustering Patterns
[Analysis of IOC relationships and groupings]

#### Research Observations
[Notable patterns and their significance]

Generate the analysis now:"""
