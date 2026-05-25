"""Compliance and Risk Assessment Prompts.

Prompts for compliance assessments and executive risk briefings.
"""

from typing import Dict, Any


def compliance_assessment_prompt(
    compliance_data: Dict[str, Any], framework: str = "SOC2"
) -> str:
    """Generate prompt for compliance assessment.

    Args:
        compliance_data: Compliance-related data
        framework: Compliance framework (SOC2, ISO27001, NIST, etc.)

    Returns:
        Formatted prompt string
    """
    return f"""You are a compliance auditor specializing in {framework}. Generate a compliance assessment based on honeypot security monitoring data.

**Compliance Context:**
- Framework: {framework}
- Assessment data: {compliance_data}

**Instructions:**
1. Evaluate logging completeness and retention
2. Assess incident detection and response procedures
3. Review security monitoring coverage and effectiveness
4. Verify audit trail integrity and documentation
5. Identify compliance gaps or deficiencies
6. Provide remediation recommendations aligned with {framework}
7. Use formal compliance and audit terminology
8. Professional markdown format (350-500 words)

**Format:**
### {framework} Compliance Assessment

#### Logging & Monitoring Controls
[Evaluation of logging practices against {framework} requirements]

#### Incident Management
[Assessment of detection, response, and documentation procedures]

#### Security Control Effectiveness
[Analysis of deployed security controls and coverage]

#### Compliance Gaps Identified
[Deficiencies or areas requiring improvement]

#### Remediation Recommendations
[Specific actions to achieve full {framework} compliance]

Generate assessment now:"""


def executive_risk_briefing_prompt(
    risk_data: Dict[str, Any], business_context: str
) -> str:
    """Generate prompt for executive risk briefing.

    Args:
        risk_data: Risk assessment data
        business_context: Business context information

    Returns:
        Formatted prompt string
    """
    return f"""You are a CISO preparing an executive risk briefing for the board of directors. Translate technical security findings into business risk language.

**Risk Context:**
- Business context: {business_context}
- Risk data: {risk_data}

**Instructions:**
1. Translate technical threats into business risk terms
2. Quantify potential business impact (financial, reputational, operational)
3. Assess risk likelihood and severity for each threat category
4. Prioritize risks by business criticality
5. Provide strategic recommendations (not technical tactics)
6. Use executive-appropriate language (minimal jargon)
7. Focus on decision-making insights
8. Professional markdown (300-400 words)

**Format:**
### Executive Risk Briefing

#### Risk Posture Summary
[High-level assessment of current security risk position]

#### Top Business Risks
[3-5 critical risks ranked by business impact]

**Risk 1: [Risk Name]**
- **Business Impact:** [Financial/operational/reputational consequences]
- **Likelihood:** [HIGH/MEDIUM/LOW with justification]
- **Potential Cost:** [Estimated financial impact]

**Risk 2: [Risk Name]**
[Repeat format]

#### Strategic Recommendations
[Board-level actions and investment priorities]

#### Risk Trend Analysis
[Are risks increasing, stable, or decreasing?]

Generate briefing now:"""
