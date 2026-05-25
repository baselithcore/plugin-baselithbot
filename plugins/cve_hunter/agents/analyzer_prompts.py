"""CVE Analyzer Prompts.

This module contains prompt generation logic for CVE analysis
to separate concern from the main agent class.
"""

from typing import Any, Dict

try:
    from ..models import CVERecord, CVEStats
except ImportError:
    from models import CVERecord, CVEStats  # type: ignore[no-redef]


def get_system_prompt() -> str:
    """Get system prompt for CVE analysis."""
    return """You are a senior cybersecurity analyst specializing in vulnerability assessment.
Provide clear, actionable analysis of CVEs. Be concise but thorough.
Focus on practical security implications and remediation guidance.
Use technical language appropriate for security professionals."""


def build_analysis_prompt(cve: CVERecord) -> str:
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


def build_batch_summary_prompt(cve_list: str, count: int) -> str:
    """Build prompt for batch summary."""
    prompt = f"""Provide a brief security briefing summary of these {count} vulnerabilities:

{cve_list}

Include:
1. Most critical items requiring immediate attention
2. Common themes or affected systems
3. Overall risk assessment
"""
    return f"You are a security analyst providing vulnerability briefings.\n\n{prompt}"


def build_attack_chain_prompt(chain: Dict[str, Any]) -> str:
    """Build prompt for attack chain analysis."""
    name = chain.get("name", "Unknown Chain")
    description = chain.get("description", "")
    severity = chain.get("total_severity", 0)
    cve_ids = chain.get("cve_ids", [])
    techniques = chain.get("mitre_techniques", [])

    prompt = f"""Perform a "Kill Chain Analysis" for this detected attack chain:

Name: {name}
Description: {description}
Total Severity: {severity}
CVEs Involved: {", ".join(cve_ids)}
MITRE ATT&CK Techniques: {", ".join(techniques)}

Provide a tactical breakdown:
1. **Kill Chain Verification**: Is this a viable escalation path?
2. **Leading Indicators**: What logs or signals would precede this attack?
3. **Choke Points**: Where is the best place to break this chain?
4. **Immediate Countermeasures**: Top 3 actions to prevent this specific chain.

Format as a concise Markdown briefing.
IMPORTANT: Do NOT use markdown tables. Use bulleted lists or headers instead.
"""
    return f"You are a strategic security analyst specializing in attack paths.\n\n{prompt}"


def build_exploitability_prompt(cve: CVERecord, has_exploit_refs: bool) -> str:
    """Build prompt for exploitability assessment."""
    prompt = f"""Assess the exploitability of this vulnerability:

CVE: {cve.cve_id}
Severity: {cve.severity.value}
CVSS: {cve.cvss_score}
Description: {cve.description}
Has exploit references: {has_exploit_refs}
CWEs: {", ".join(cve.cwe_ids)}

Provide:
1. Exploitability score (1-10)
2. Attack complexity (low/medium/high)
3. Prerequisites for exploitation
4. Likely attack vectors
"""
    return f"You are a penetration testing expert assessing vulnerability exploitability.\n\n{prompt}"


def build_strategic_analysis_prompt(
    stats: CVEStats,
    chains_summary: str,
    cves_summary: str,
    findings_summary: str,
) -> str:
    """Build prompt for strategic analysis."""
    prompt = f"""Perform a tactical security analysis based on the current situation:

## Current Status
- Active Alerts: {stats.active_alerts}
- Critical/High CVEs: {stats.critical_count} Critical, {stats.high_count} High
- Exploitable: {stats.with_exploit}

## Attack Chains (Correlated Risks)
{chains_summary}

## Top Vulnerabilities
{cves_summary}

## Recent Live Insights (Zero-Day Candidates)
{findings_summary}

Provide a "Tactical Insight" report in Markdown format with:
1. **Situation Summary**: High-level assessment of the threat level.
2. **Critical Focus**: Which specific CVEs or chains need immediate patching/mitigation?
3. **Strategic Recommendation**: What should the security team do in the next hour?
4. **Threat Horizon**: One sentence on potential emerging risks based on findings.

Be concise, direct, and act as a senior cyber-commander.
"""
    return f"{get_system_prompt()}\n\n{prompt}"
