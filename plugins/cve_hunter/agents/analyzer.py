"""CVE Analyzer Agent.

Agent responsible for analyzing CVE data using LLM capabilities
to generate summaries, assess impact, and correlate vulnerabilities.

Enhanced with:
- SelfCorrector for analysis validation
- ExperienceReplay for continuous learning
"""

from core.observability.logging import get_logger
import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, TYPE_CHECKING
from core.di import ServiceRegistry
from core.interfaces import LLMServiceProtocol

# Support both relative imports (when installed) and absolute imports (when via sys.path)
try:
    from ..config import CVEHunterConfig, get_cve_hunter_config
    from ..models import CVERecord, CVEStats
    from ..events import CVEHunterEvents, CVEEventData, emit_cve_event
except ImportError:
    from config import CVEHunterConfig, get_cve_hunter_config  # type: ignore[no-redef]
    from models import CVERecord, CVEStats  # type: ignore[no-redef]
    from events import CVEHunterEvents, CVEEventData, emit_cve_event  # type: ignore[no-redef]

if TYPE_CHECKING:
    from core.reasoning.self_correction import SelfCorrector
    from core.learning import ExperienceReplay

logger = get_logger(__name__)


class CVEAnalyzerAgent:
    """Agent for AI-powered CVE analysis.

    Uses LLM to generate summaries, assess impact, and
    identify related vulnerabilities.

    Example:
        ```python
        agent = CVEAnalyzerAgent()
        analysis = await agent.analyze_cve(cve_record)
        print(analysis["summary"])
        ```
    """

    name = "cve-analyzer"

    def __init__(
        self,
        config: Optional[CVEHunterConfig] = None,
        llm_service: Optional[LLMServiceProtocol] = None,
        self_corrector: Optional["SelfCorrector"] = None,
        experience_replay: Optional["ExperienceReplay"] = None,
    ):
        """Initialize analyzer agent.

        Args:
            config: CVE Hunter configuration
            llm_service: LLM service for AI analysis (injected or from DI)
            self_corrector: Optional SelfCorrector for analysis validation
            experience_replay: Optional ExperienceReplay for learning
        """
        self.config = config or get_cve_hunter_config()
        self._llm_service = llm_service
        self._corrector = self_corrector
        self._experience = experience_replay
        self._corrector_initialized = False
        self._experience_initialized = False

    async def _get_llm(self) -> LLMServiceProtocol:
        """Get LLM service from DI container."""
        if self._llm_service is None:
            service_or_factory = ServiceRegistry.get(LLMServiceProtocol)

            # Handle lazy loading factory
            if asyncio.iscoroutinefunction(service_or_factory) or (
                callable(service_or_factory)
                and not isinstance(service_or_factory, type)
            ):
                if asyncio.iscoroutinefunction(service_or_factory):
                    self._llm_service = await service_or_factory()
                else:
                    result = service_or_factory()
                    if asyncio.iscoroutine(result):
                        self._llm_service = await result
                    else:
                        self._llm_service = result
            else:
                self._llm_service = service_or_factory

        return self._llm_service

    def _get_corrector(self) -> Optional["SelfCorrector"]:
        """Lazy-load SelfCorrector."""
        if self._corrector is None and not self._corrector_initialized:
            self._corrector_initialized = True
            if self.config.enable_self_correction:
                try:
                    from core.reasoning.self_correction import SelfCorrector

                    self._corrector = SelfCorrector(
                        max_corrections=self.config.max_correction_iterations
                    )
                    logger.debug("SelfCorrector initialized for CVE analysis")
                except ImportError:
                    logger.debug("SelfCorrector not available")
        return self._corrector

    def _get_experience(self) -> Optional["ExperienceReplay"]:
        """Lazy-load ExperienceReplay."""
        if self._experience is None and not self._experience_initialized:
            self._experience_initialized = True
            if self.config.enable_learning:
                try:
                    from core.learning import ExperienceReplay

                    self._experience = ExperienceReplay(
                        capacity=self.config.experience_buffer_size,
                        prioritized=True,
                        priority_alpha=self.config.learning_priority_alpha,
                    )
                    logger.debug("ExperienceReplay initialized for CVE analysis")
                except ImportError:
                    logger.debug("ExperienceReplay not available")
        return self._experience

    async def analyze_cve(self, cve: CVERecord) -> Dict[str, Any]:
        """Analyze a single CVE with AI.

        Uses SelfCorrector to validate and improve the analysis.
        Records experience for continuous learning.

        Args:
            cve: CVE record to analyze

        Returns:
            Analysis dict with summary, impact, recommendations
        """
        llm = await self._get_llm()

        prompt = self._build_analysis_prompt(cve)
        full_prompt = f"{self._get_system_prompt()}\n\n{prompt}"

        analysis_result: Dict[str, Any] = {
            "cve_id": cve.cve_id,
            "severity": cve.severity.value,
            "cvss_score": cve.cvss_score,
            "analyzed": False,
        }

        try:
            # Generate initial analysis
            response = await llm.generate_response(prompt=full_prompt)

            # Apply self-correction if enabled
            corrector = self._get_corrector()
            if corrector and response:
                try:
                    correction_result = await corrector.correct(
                        response=response,
                        context=f"CVE: {cve.cve_id}, Severity: {cve.severity.value}",
                    )
                    response = correction_result.corrected
                    analysis_result["corrections_made"] = (
                        correction_result.corrections_made
                    )
                    logger.debug(
                        f"Analysis corrected {correction_result.corrections_made} times"
                    )
                except Exception as e:
                    logger.debug(f"Self-correction failed: {e}")

            analysis_result["ai_summary"] = response
            analysis_result["analyzed"] = True

            # Record successful experience
            experience = self._get_experience()
            if experience:
                self._record_experience(
                    experience=experience,
                    cve_id=cve.cve_id,
                    action="analyze",
                    success=True,
                    severity=cve.severity.value,
                )

            # Emit analysis event
            await self._emit_analysis_event(cve, analysis_result)

            return analysis_result

        except Exception as e:
            logger.error(f"Analysis failed for {cve.cve_id}: {e}")

            # Record failed experience
            experience = self._get_experience()
            if experience:
                self._record_experience(
                    experience=experience,
                    cve_id=cve.cve_id,
                    action="analyze",
                    success=False,
                    severity=cve.severity.value,
                )

            analysis_result["ai_summary"] = None
            analysis_result["error"] = str(e)
            return analysis_result

    async def summarize_batch(
        self,
        cves: List[CVERecord],
        max_items: int = 10,
    ) -> str:
        """Generate summary of multiple CVEs.

        Args:
            cves: List of CVE records
            max_items: Maximum items to include

        Returns:
            Summary text
        """
        llm = await self._get_llm()

        # Take most critical CVEs
        sorted_cves = sorted(cves, key=lambda c: c.cvss_score, reverse=True)[:max_items]

        cve_list = "\n".join(
            f"- {c.cve_id}: {c.severity.value.upper()} (CVSS {c.cvss_score}) - "
            f"{c.description[:100]}..."
            for c in sorted_cves
        )

        prompt = f"""Provide a brief security briefing summary of these {len(sorted_cves)} vulnerabilities:

{cve_list}

Include:
1. Most critical items requiring immediate attention
2. Common themes or affected systems
3. Overall risk assessment
"""

        full_prompt = (
            f"You are a security analyst providing vulnerability briefings.\n\n{prompt}"
        )

        try:
            response = await llm.generate_response(
                prompt=full_prompt,
            )
            return response

        except Exception as e:
            logger.error(f"Batch summary failed: {e}")
            return f"Summary generation failed: {e}"

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

        full_prompt = f"You are a strategic security analyst specializing in attack paths.\n\n{prompt}"

        try:
            response = await llm.generate_response(prompt=full_prompt)
            return response
        except Exception as e:
            logger.error(f"Attack chain analysis failed: {e}")
            return f"Analysis failed: {e}"

    async def assess_exploitability(self, cve: CVERecord) -> Dict[str, Any]:
        """Assess exploitability of a CVE.

        Args:
            cve: CVE record

        Returns:
            Exploitability assessment
        """
        llm = await self._get_llm()

        # Check for exploit indicators in references
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

        full_prompt = f"You are a penetration testing expert assessing vulnerability exploitability.\n\n{prompt}"

        try:
            response = await llm.generate_response(
                prompt=full_prompt,
            )

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

    async def correlate_cves(self, cves: List[CVERecord]) -> List[List[str]]:
        """Find related CVEs in a list.

        Args:
            cves: List of CVE records

        Returns:
            List of related CVE ID groups
        """
        # Group by CWE
        cwe_groups: Dict[str, List[str]] = {}
        for cve in cves:
            for cwe in cve.cwe_ids:
                if cwe not in cwe_groups:
                    cwe_groups[cwe] = []
                cwe_groups[cwe].append(cve.cve_id)

        # Group by affected product
        product_groups: Dict[str, List[str]] = {}
        for cve in cves:
            for product in cve.affected_products:
                key = f"{product.vendor}:{product.product}"
                if key not in product_groups:
                    product_groups[key] = []
                product_groups[key].append(cve.cve_id)

        # Return groups with more than 1 CVE
        correlated = []
        for group in list(cwe_groups.values()) + list(product_groups.values()):
            if len(group) > 1 and group not in correlated:
                correlated.append(group)

        return correlated

    def calculate_priority_score(self, cve: CVERecord) -> int:
        """Calculate priority score for a CVE.

        Args:
            cve: CVE record

        Returns:
            Priority score (1-5, 1 is highest)
        """
        score = 5  # Default low priority

        # CVSS score impact
        if cve.cvss_score >= 9.0:
            score = 1
        elif cve.cvss_score >= 7.0:
            score = 2
        elif cve.cvss_score >= 5.0:
            score = 3
        elif cve.cvss_score >= 3.0:
            score = 4

        # Exploit availability increases priority
        if cve.exploit_available:
            score = max(1, score - 1)

        # No patch available increases priority
        if not cve.patch_available:
            score = max(1, score - 1)

        return score

    def _build_analysis_prompt(self, cve: CVERecord) -> str:
        """Build analysis prompt for LLM."""
        affected = ", ".join(
            f"{p.vendor} {p.product}" for p in cve.affected_products[:5]
        )
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

    def _get_system_prompt(self) -> str:
        """Get system prompt for CVE analysis."""
        return """You are a senior cybersecurity analyst specializing in vulnerability assessment.
Provide clear, actionable analysis of CVEs. Be concise but thorough.
Focus on practical security implications and remediation guidance.
Use technical language appropriate for security professionals."""

    # =========================================================================
    # Experience & Event Helpers
    # =========================================================================

    def _record_experience(
        self,
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

            # Calculate reward based on success and severity
            reward = 1.0 if success else -0.5
            if severity == "critical":
                reward *= 1.5  # Higher reward for critical CVEs

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

    async def _emit_analysis_event(
        self, cve: CVERecord, analysis: Dict[str, Any]
    ) -> None:
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

        # Format input data
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
                f"- [{f.get('timestamp', 'recent')}] {f.get('pattern', 'unknown')} (Conf: {f.get('confidence', 'N/A')})"
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

        full_prompt = f"{self._get_system_prompt()}\n\n{prompt}"

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

        # Build prompt
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

        full_prompt = f"{self._get_system_prompt()}\n\n{prompt}"

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
