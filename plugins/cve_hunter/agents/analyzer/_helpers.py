"""CVE Analyzer Agent — prompt builders, scoring, experience & event helpers."""

from typing import Any, Dict, List, TYPE_CHECKING

from core.observability.logging import get_logger

try:
    from ...models import CVERecord
    from ...events import CVEHunterEvents, CVEEventData, emit_cve_event
except ImportError:
    from models import CVERecord  # type: ignore[no-redef]
    from events import CVEHunterEvents, CVEEventData, emit_cve_event  # type: ignore[no-redef]

if TYPE_CHECKING:
    from core.learning import ExperienceReplay

logger = get_logger(__name__)


def build_analysis_prompt(cve: "CVERecord") -> str:
    """Build analysis prompt for LLM."""
    affected = ", ".join(f"{p.vendor} {p.product}" for p in cve.affected_products[:5])
    refs = "\n".join(f"- {r.url}" for r in cve.references[:3])

    return f"""Analyze this security vulnerability:

CVE ID: {cve.cve_id}
Severity: {cve.severity.value.upper()}
CVSS Score: {cve.cvss_score}
Description: {cve.description}
Affected Products: {affected or "Not specified"}
CWE IDs: {", ".join(cve.cwe_ids) or "Not specified"}

References:
{refs or "None"}

Provide:
1. A one-paragraph executive summary
2. Key technical details
3. Recommended mitigation steps
4. Priority level for remediation
"""


def get_system_prompt() -> str:
    """Get system prompt for CVE analysis."""
    return """You are a senior cybersecurity analyst specializing in vulnerability assessment.
Provide clear, actionable analysis of CVEs. Be concise but thorough.
Focus on practical security implications and remediation guidance.
Use technical language appropriate for security professionals."""


def calculate_priority_score(cve: "CVERecord") -> int:
    """Calculate priority score for a CVE (1-5, 1 is highest).

    Args:
        cve: CVE record

    Returns:
        Priority score
    """
    score = 5

    if cve.cvss_score >= 9.0:
        score = 1
    elif cve.cvss_score >= 7.0:
        score = 2
    elif cve.cvss_score >= 5.0:
        score = 3
    elif cve.cvss_score >= 3.0:
        score = 4

    if cve.exploit_available:
        score = max(1, score - 1)
    if not cve.patch_available:
        score = max(1, score - 1)

    return score


def correlate_cves(cves: List["CVERecord"]) -> List[List[str]]:
    """Find related CVEs in a list grouped by CWE/product.

    Args:
        cves: List of CVE records

    Returns:
        List of related CVE ID groups
    """
    cwe_groups: Dict[str, List[str]] = {}
    for cve in cves:
        for cwe in cve.cwe_ids:
            if cwe not in cwe_groups:
                cwe_groups[cwe] = []
            cwe_groups[cwe].append(cve.cve_id)

    product_groups: Dict[str, List[str]] = {}
    for cve in cves:
        for product in cve.affected_products:
            key = f"{product.vendor}:{product.product}"
            if key not in product_groups:
                product_groups[key] = []
            product_groups[key].append(cve.cve_id)

    correlated = []
    for group in list(cwe_groups.values()) + list(product_groups.values()):
        if len(group) > 1 and group not in correlated:
            correlated.append(group)

    return correlated


def record_experience(
    experience: "ExperienceReplay",
    cve_id: str,
    action: str,
    success: bool,
    severity: str,
) -> None:
    """Record an experience for learning.

    Args:
        experience: ExperienceReplay buffer
        cve_id: CVE identifier
        action: Action taken (e.g., "analyze")
        success: Whether the action succeeded
        severity: CVE severity level
    """
    try:
        from core.learning.types import Experience

        reward = 1.0 if success else -0.5
        if severity == "critical":
            reward *= 1.5

        exp = Experience(
            state={"cve_id": cve_id, "severity": severity},
            action=action,
            reward=reward,
            next_state={"analyzed": success},
            done=True,
        )
        experience.add(exp)

    except Exception as e:
        logger.debug(f"Failed to record experience: {e}")


async def emit_analysis_event(cve: "CVERecord", analysis: Dict[str, Any]) -> None:
    """Emit CVE analyzed event.

    Args:
        cve: CVE record that was analyzed
        analysis: Analysis result
    """
    try:
        event_data = CVEEventData(
            cve_id=cve.cve_id,
            severity=cve.severity.value,
            cvss_score=cve.cvss_score,
            source=cve.source.value if cve.source else "unknown",
            title=cve.title,
            is_new=False,
            has_exploit=cve.exploit_available,
        )
        await emit_cve_event(
            CVEHunterEvents.CVE_ANALYZED,
            event_data.to_dict(),
        )
    except Exception as e:
        logger.debug(f"Failed to emit analysis event: {e}")
