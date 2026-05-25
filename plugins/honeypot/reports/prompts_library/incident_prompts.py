"""Incident and Timeline Analysis Prompts.

Prompts for incident narratives and timeline reconstruction.
"""

from typing import List, Dict, Any


def incident_timeline_narrative_prompt(
    timeline_events: List[Dict[str, Any]], incident_type: str
) -> str:
    """Generate prompt for incident timeline narrative.

    Args:
        timeline_events: List of timeline events
        incident_type: Type of incident

    Returns:
        Formatted prompt string
    """
    return f"""You are an incident response analyst. Generate a professional incident timeline narrative based on the following security events.

**Incident Context:**
- Incident Type: {incident_type}
- Timeline Events: {len(timeline_events)}
- Event samples: {timeline_events[:20]}

**Instructions:**
1. Create a chronological narrative of the incident
2. Identify initial compromise vector and lateral movement
3. Highlight critical decision points and escalation moments
4. Assess attacker objectives and success level
5. Evaluate defender detection and response effectiveness
6. Use timestamps and specific technical details
7. Professional incident response terminology
8. Markdown format with timeline sections (400-600 words)

**Format:**
### Incident Timeline Narrative

#### Initial Access (Time: [timestamp])
[How the attacker gained initial access]

#### Reconnaissance & Discovery
[Attacker enumeration and discovery activities]

#### Lateral Movement & Escalation
[Progression through the environment]

#### Objective Achievement
[Attacker goals and what was accomplished]

#### Detection & Response
[When/how the incident was detected and contained]

#### Impact Assessment
[Business and technical impact evaluation]

Generate timeline narrative now:"""
