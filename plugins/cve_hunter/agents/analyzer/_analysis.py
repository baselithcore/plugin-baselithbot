"""CVE Analyzer Agent — extended analysis methods.

Contains: analyze_attack_chain, assess_exploitability, analyze_strategic_situation,
analyze_attack_payload. These methods require an LLM and are used less frequently
than the core analyze_cve / summarize_batch path.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from core.observability.logging import get_logger

try:
    from ...models import CVERecord, CVEStats
except ImportError:
    from models import CVERecord, CVEStats  # type: ignore[no-redef]

from ._helpers import get_system_prompt

logger = get_logger(__name__)


class AnalysisMethods:
    """Mixin providing extended LLM-powered analysis methods for CVEAnalyzerAgent."""

    async def analyze_attack_chain(self, chain: Dict[str, Any]) -> str:
        """Analyze an attack chain using AI.

        Args:
            chain: Attack chain dictionary

        Returns:
            AI-generated analysis report
        """
        llm = await self._get_llm()

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

        full_prompt = (
            f"You are a strategic security analyst specializing in attack paths.\n\n"
            f"{prompt}"
        )

        try:
            response = await llm.generate_response(prompt=full_prompt)
            return response
        except Exception as e:
            logger.error(f"Attack chain analysis failed: {e}")
            return f"Analysis failed: {e}"

    async def assess_exploitability(self, cve: "CVERecord") -> Dict[str, Any]:
        """Assess exploitability of a CVE.

        Args:
            cve: CVE record

        Returns:
            Exploitability assessment
        """
        llm = await self._get_llm()

        exploit_tags = ["exploit", "poc", "proof-of-concept", "metasploit"]
        has_exploit_refs = any(
            any(
                tag in ref.url.lower() or tag in str(ref.tags).lower()
                for tag in exploit_tags
            )
            for ref in cve.references
        )

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

        full_prompt = (
            f"You are a penetration testing expert assessing vulnerability "
            f"exploitability.\n\n{prompt}"
        )

        try:
            response = await llm.generate_response(prompt=full_prompt)
            return {
                "cve_id": cve.cve_id,
                "has_known_exploits": has_exploit_refs or cve.exploit_available,
                "assessment": response,
                "success": True,
            }
        except Exception as e:
            logger.error(f"Exploitability assessment failed: {e}")
            return {
                "cve_id": cve.cve_id,
                "has_known_exploits": has_exploit_refs,
                "error": str(e),
                "success": False,
            }

    async def analyze_strategic_situation(
        self,
        stats: "CVEStats",
        active_chains: List[Dict[str, Any]],
        top_cves: List["CVERecord"],
        recent_findings: List[Dict[str, Any]],
    ) -> str:
        """Perform a strategic analysis of the current security situation.

        Args:
            stats: Current CVE statistics
            active_chains: List of detected attack chains
            top_cves: List of top critical/high CVEs
            recent_findings: List of recent discovery findings

        Returns:
            Markdown formatted situation report
        """
        llm = await self._get_llm()

        chains_summary = (
            "\n".join(
                f"- {c['name']} (Severity: {c['total_severity']})"
                for c in active_chains
            )
            if active_chains
            else "No active attack chains detected."
        )

        cves_summary = (
            "\n".join(
                f"- {c.cve_id}: {c.severity.value} (CVSS {c.cvss_score}) - {c.title}"
                for c in top_cves
            )
            if top_cves
            else "No open critical vulnerabilities."
        )

        findings_summary = (
            "\n".join(
                f"- [{f.get('timestamp', 'recent')}] {f.get('pattern', 'unknown')} "
                f"(Conf: {f.get('confidence', 'N/A')})"
                for f in recent_findings[:5]
            )
            if recent_findings
            else "No recent anomalies currently."
        )

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

        full_prompt = f"{get_system_prompt()}\n\n{prompt}"

        try:
            response = await llm.generate_response(prompt=full_prompt)
            return response
        except Exception as e:
            logger.error(f"Strategic analysis failed: {e}")

    async def analyze_attack_payload(
        self,
        payload: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Analyze a raw attack payload using deep inspection.

        Args:
            payload: Attack payload string
            context: Context dictionary (protocol, source_ip, etc.)

        Returns:
            Analysis result dictionary
        """
        llm = await self._get_llm()
        context = context or {}

        protocol = context.get("protocol", "unknown")
        source_ip = context.get("source_ip", "unknown")

        prompt = f"""Analyze this suspicious payload detected by our honeypot ({protocol}):

PAYLOAD:
{payload}

CONTEXT:
Source IP: {source_ip}
Protocol: {protocol}
Additional Context: {context}

Task:
1. Decode/De-obfuscate the payload if necessary.
2. Identify the specific attack technique (MITRE ATT&CK if applicable).
3. Determine the intent and potential impact.
4. Check if this resembles any known CVE exploit patterns.

Provide specific, technical analysis."""

        full_prompt = f"{get_system_prompt()}\n\n{prompt}"

        try:
            response = await llm.generate_response(prompt=full_prompt)
            return {
                "payload_preview": payload[:100],
                "analysis_summary": response,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "success": True,
            }
        except Exception as e:
            logger.error(f"Payload analysis failed: {e}")
            return {"error": str(e), "success": False}
