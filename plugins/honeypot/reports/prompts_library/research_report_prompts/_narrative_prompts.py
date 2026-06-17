"""Narrative and trend analysis prompts."""

from typing import Any, Dict, List

from ._core import RESEARCH_ANALYST_PERSONA


def research_attack_narrative_prompt(
    session_analysis: Any,  # AttackSessionAnalysis
) -> str:
    """Generate prompt for sequential attack narrative.

    Args:
        session_analysis: AttackSessionAnalysis object with steps

    Returns:
        Formatted prompt for LLM
    """
    session_id = session_analysis.session_id
    attacker_ip = session_analysis.attacker_ip
    steps_data = []

    for step in session_analysis.steps:
        steps_data.append(
            {
                "time": step.timestamp.isoformat(),
                "phase": step.phase,
                "action": step.description,
                "payload": step.payload_snippet or "N/A",
            }
        )

    return f"""{RESEARCH_ANALYST_PERSONA}

**Task**: Reconstruct the "Kill Chain" narrative for a specific attack session captured by the honeypot.

**Session Context**:
- Session ID: {session_id}
- Attacker IP: {attacker_ip}
- Total Steps: {len(steps_data)}

**Attack Sequence**:
{chr(10).join(f"- [{s['time']}] {s['phase']}: {s['action']} (Payload: {s['payload']})" for s in steps_data)}

**Requirements**:
1. Write a chronological narrative describing the attacker's actions.
2. **Interpret intent**: Explain *why* the attacker executed specific commands or payloads.
3. Highlight the progression from Reconnaissance -> Initial Access -> Exploitation.
4. If payloads are present, analyze them briefly within the flow.
5. Use professional, forensic language.
6. Keep it concise (1-2 paragraphs per session).

**Format**:
### Attack Session Analysis: {attacker_ip}
[Chronological narrative...]

**Key Techniques Observed**:
- [Technique 1]
- [Technique 2]

Generate the narrative now:"""


def research_trend_analysis_prompt(
    honeypot_name: str,
    timeline_data: List[Dict[str, Any]],
    time_range: str,
) -> str:
    """Generate prompt for temporal trend analysis.

    Args:
        honeypot_name: Honeypot identifier
        timeline_data: Time-series attack data
        time_range: Analysis period

    Returns:
        Formatted prompt for LLM
    """
    return f"""{RESEARCH_ANALYST_PERSONA}

**Task**: Analyze temporal attack trends observed on {honeypot_name}.

**Data Context**:
- Honeypot: {honeypot_name}
- Analysis period: {time_range}
- Timeline events: {len(timeline_data)} data points

**Timeline Sample**:
{timeline_data[:20]}

**Analysis Requirements**:
1. Identify attack volume patterns (daily/weekly cycles)
2. Detect campaign bursts or coordinated activity windows
3. Correlate timing with known threat actor operating hours
4. Highlight any escalation or de-escalation trends
5. Note correlation with external events (patch releases, etc.)

**Format**:
## Temporal Trend Analysis

### Attack Volume Patterns
[Analysis of timing patterns for {honeypot_name}]

### Campaign Detection
[Identification of distinct attack campaigns]

### Trend Assessment
[Overall threat trajectory]

Generate trend analysis now:"""
