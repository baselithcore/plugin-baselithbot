"""Custom Section Prompts.

Dynamic prompt generation for custom report sections.
"""

from typing import Dict, Any


def get_custom_section_prompt(
    section_name: str,
    section_data: Dict[str, Any],
    context: str = "technical security report",
) -> str:
    """Generate prompt for custom report section.

    Args:
        section_name: Name of the custom section
        section_data: Data for the custom section
        context: Report context (technical, executive, compliance, etc.)

    Returns:
        Formatted prompt string
    """
    return f"""You are a professional cybersecurity analyst. Generate a comprehensive report section for: "{section_name}"

**Context:** This is for a {context}.

**Section Data:**
```json
{section_data}
```

**Instructions:**
1. Analyze the provided data thoroughly
2. Generate insights appropriate for {context} audience
3. Use professional cybersecurity terminology
4. Structure with clear markdown headers and sections
5. Include specific findings, not generic statements
6. Provide actionable insights and recommendations
7. Be concise but comprehensive (300-500 words)
8. Match the tone and style of a {context}

**Format:**
### {section_name}

[Your analysis and insights here, organized with appropriate subheadings]

Generate the section now:"""
