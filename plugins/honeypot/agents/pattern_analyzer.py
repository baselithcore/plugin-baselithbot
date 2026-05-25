"""Pattern Analyzer Agent.

AI-powered attack pattern analysis using core LLMService.
"""

from core.observability.logging import get_logger
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..config import HoneypotConfig, get_honeypot_config
from ..models import AttackCategory, AttackSeverity

logger = get_logger(__name__)


class PatternAnalyzer:
    """AI-powered attack pattern analyzer."""

    def __init__(self, config: Optional[HoneypotConfig] = None):
        """Initialize pattern analyzer.

        Args:
            config: Honeypot configuration
        """
        self.config = config or get_honeypot_config()
        self._llm_service = None
        self._initialized = False

        # Known attack signatures for quick matching
        self._signatures: Dict[str, Dict[str, Any]] = {}
        # Cache for LLM analysis results
        self._cache: Dict[str, Any] = {}

    async def initialize(self) -> bool:
        """Initialize analyzer with dedicated LLM service."""
        if self._initialized:
            return True

        try:
            from core.services.llm import LLMService
            from core.config import LLMConfig
            import os

            # Create specific config for analysis
            # Fallback to env var if not in config
            api_key = self.config.analysis_llm_api_key or os.environ.get(
                "HONEYPOT_ANALYSIS_LLM_API_KEY"
            )

            # If no specific key provided and provider is same as global, might rely on global env?
            # But here we want explicit separation. If provider is "openai", we likely need a key.
            # We trust LLMService to validation.

            analysis_config = LLMConfig(
                provider=self.config.analysis_llm_provider,
                model=self.config.analysis_llm_model,
                api_key=api_key,
                enable_cache=True,
            )

            self._llm_service = LLMService(config=analysis_config)
            self._initialized = True

            logger.info(
                f"Pattern analyzer initialized with dedicated provider: {analysis_config.provider} ({analysis_config.model})"
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to initialize pattern analyzer: {e}")
            return False

    async def analyze_payload(
        self,
        payload: str,
        protocol: str,
        source_ip: str,
        force_llm: bool = False,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Analyze attack payload for patterns and intent.

        Args:
            payload: Raw attack payload
            protocol: Protocol (ssh/http)
            source_ip: Attacker IP
            force_llm: Force LLM analysis even if signature matches

        Returns:
            Analysis result with patterns, category, severity
        """
        analysis_id = f"analysis-{uuid4().hex[:8]}"

        # Quick signature match first
        quick_match = self._quick_signature_match(payload)

        # If we have a match and NOT forcing LLM, return early (fast path)
        if quick_match and not force_llm:
            return {
                "analysis_id": analysis_id,
                "matched_signature": quick_match["name"],
                "category": quick_match["category"],
                "severity": quick_match["severity"],
                "confidence": 0.9,
                "llm_analysis": None,
            }

        # Deep LLM analysis if available
        llm_result = None
        if self._initialized and self._llm_service:
            # Check cache first (skip cache if forcing fresh analysis)
            import hashlib

            payload_hash = hashlib.sha256(payload.encode()).hexdigest()

            if payload_hash in self._cache and not force_llm:
                logger.info(f"Cache hit for payload hash {payload_hash}")
                llm_result = self._cache[payload_hash]
            else:
                llm_result = await self._llm_analyze(payload, protocol, context)
                if llm_result:
                    # simplistic cache eviction policy
                    if len(self._cache) > 1000:
                        self._cache.pop(next(iter(self._cache)))
                    self._cache[payload_hash] = llm_result

        # If LLM failed/skipped but we had a quick match, use that
        if not llm_result and quick_match:
            return {
                "analysis_id": analysis_id,
                "matched_signature": quick_match["name"],
                "category": quick_match["category"],
                "severity": quick_match["severity"],
                "confidence": 0.9,
                "llm_analysis": None,
            }

        return {
            "analysis_id": analysis_id,
            "matched_signature": quick_match["name"] if quick_match else None,
            "category": llm_result.get("category", "unknown")
            if llm_result
            else "unknown",
            "severity": llm_result.get("severity", "medium")
            if llm_result
            else "medium",
            "confidence": llm_result.get("confidence", 0.5) if llm_result else 0.5,
            "llm_analysis": llm_result,
        }

    async def _llm_analyze(
        self,
        payload: str,
        protocol: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        """Perform LLM-based analysis with full context.

        Args:
            payload: The attack payload to analyze
            protocol: Protocol (ssh/http/tcp)
            context: Optional context dict with honeypot metadata, CVEs, patterns

        Returns:
            Analysis result dict or None if failed
        """
        try:
            # SECURITY: Sanitize payload before passing to LLM
            from ..security import sanitize_for_llm

            safe_payload = sanitize_for_llm(payload[:2000], max_length=2000)

            # Build context sections for the prompt
            context_sections = self._build_context_sections(context)

            prompt = f"""You are a senior cybersecurity analyst specializing in threat intelligence and attack pattern analysis.
Analyze the following {protocol.upper()} attack payload captured by our honeypot system.
{context_sections}
Your task:
1. Identify the attack type and techniques used
2. Explain what the attacker is trying to accomplish
3. Decode any obfuscation or encoding (base64, URL encoding, hex, etc.)
4. Assess the sophistication level and potential impact
5. Correlate with any known CVEs if applicable
6. Provide actionable insights about the threat

PAYLOAD:
{safe_payload}

Provide your analysis in JSON format with the following structure:
{{
  "category": "sql_injection|command_injection|xss|path_traversal|reconnaissance|brute_force|credential_harvesting|malware_download|exploit_attempt|unknown",
  "severity": "info|low|medium|high|critical",
  "confidence": 0.0-1.0,
  "techniques": ["MITRE ATT&CK techniques or attack methods used"],
  "summary": "One concise sentence describing the attack",
  "detailed_analysis": "Complete technical breakdown: What does this payload do? What is the attacker trying to achieve? If there's encoding/obfuscation, decode it and explain. What systems or vulnerabilities is it targeting? What would happen if successful? Include specific commands, techniques, and potential impact. Be thorough and technical. If this relates to known CVEs, explain the connection."
}}

Remember: Be specific, technical, and actionable. This analysis will be used by security teams to understand and respond to threats."""

            response = await self._llm_service.generate_response(prompt=prompt)
            logger.info(f"LLM Raw Analysis Response: {response[:500]}...")

            import json
            import re

            try:
                # Clean up markdown code blocks if present
                clean_response = response.strip()
                if "```json" in clean_response:
                    match = re.search(
                        r"```json\s*(.*?)\s*```", clean_response, re.DOTALL
                    )
                    if match:
                        clean_response = match.group(1)
                elif "```" in clean_response:
                    match = re.search(r"```\s*(.*?)\s*```", clean_response, re.DOTALL)
                    if match:
                        clean_response = match.group(1)

                return json.loads(clean_response)
            except json.JSONDecodeError as e:
                logger.warning(
                    f"LLM output was not valid JSON: {response[:100]}... Error: {e}"
                )
                return None

        except Exception as e:
            logger.warning(f"LLM analysis failed: {e}")
            return None

    def _build_context_sections(self, context: Optional[Dict[str, Any]]) -> str:
        """Build context sections for the LLM prompt.

        Args:
            context: Context dict with honeypot metadata, CVEs, patterns

        Returns:
            Formatted context string for inclusion in prompt
        """
        if not context:
            return ""

        sections = []

        # Honeypot context
        honeypot_name = context.get("honeypot_name", "")
        honeypot_desc = context.get("honeypot_description", "")
        cve_tags = context.get("honeypot_cve_tags", [])

        if honeypot_name or honeypot_desc or cve_tags:
            sections.append("\n=== HONEYPOT CONTEXT ===")
            if honeypot_name:
                sections.append(f"Honeypot: {honeypot_name}")
            if honeypot_desc:
                sections.append(f"Purpose: {honeypot_desc}")
            if cve_tags:
                cve_upper = [cve.upper().replace("-", "-") for cve in cve_tags]
                sections.append(f"Targeted CVE(s): {', '.join(cve_upper)}")

        # Already detected patterns and classification
        category = context.get("category")
        severity = context.get("severity")
        patterns = context.get("detected_patterns", [])

        if category or severity or patterns:
            sections.append("\n=== PRELIMINARY CLASSIFICATION ===")
            if category and category != "unknown":
                sections.append(f"Category: {category}")
            if severity and severity != "info":
                sections.append(f"Severity: {severity}")
            if patterns:
                sections.append(f"Detected Patterns: {', '.join(patterns)}")

        # CVE/CWE correlations already found
        matched_cves = context.get("matched_cves", [])
        matched_cwes = context.get("matched_cwes", [])

        if matched_cves or matched_cwes:
            sections.append("\n=== CORRELATED VULNERABILITIES ===")
            if matched_cves:
                sections.append(f"Matched CVEs: {', '.join(matched_cves)}")
            if matched_cwes:
                sections.append(f"Matched CWEs: {', '.join(matched_cwes)}")

        # Bot detection info
        is_bot = context.get("is_bot")
        bot_confidence = context.get("bot_confidence")

        if is_bot is not None:
            sections.append("\n=== ATTACKER PROFILE ===")
            bot_status = "Automated Bot" if is_bot else "Likely Human"
            if bot_confidence:
                sections.append(
                    f"Classification: {bot_status} (confidence: {bot_confidence:.0%})"
                )
            else:
                sections.append(f"Classification: {bot_status}")

        if sections:
            return "\n".join(sections) + "\n"
        return ""

    def _quick_signature_match(self, payload: str) -> Optional[Dict[str, Any]]:
        """Quick signature-based matching."""
        payload_lower = payload.lower()

        # SQL Injection signatures
        sql_patterns = ["union select", "' or '1'='1", "drop table", "insert into"]
        for pattern in sql_patterns:
            if pattern in payload_lower:
                return {
                    "name": "sql_injection",
                    "category": AttackCategory.SQL_INJECTION.value,
                    "severity": AttackSeverity.HIGH.value,
                }

        # Command Injection signatures
        cmd_patterns = ["; cat ", "|cat ", "$(", "bash -i", "nc -e"]
        for pattern in cmd_patterns:
            if pattern in payload_lower:
                return {
                    "name": "command_injection",
                    "category": AttackCategory.COMMAND_INJECTION.value,
                    "severity": AttackSeverity.CRITICAL.value,
                }

        # Path Traversal
        if "../" in payload or "..\\" in payload or "/etc/passwd" in payload_lower:
            return {
                "name": "path_traversal",
                "category": AttackCategory.PATH_TRAVERSAL.value,
                "severity": AttackSeverity.MEDIUM.value,
            }

        # XSS
        if "<script" in payload_lower or "javascript:" in payload_lower:
            return {
                "name": "xss",
                "category": AttackCategory.XSS.value,
                "severity": AttackSeverity.MEDIUM.value,
            }

        # Helper regex search
        import re

        def has_word(word_list, text):
            # Matches any word in the list as a whole word (b)
            # e.g. "ls" matches "ls -la" but NOT "pulse"
            pattern = r"\b(" + "|".join(map(re.escape, word_list)) + r")\b"
            return bool(re.search(pattern, text))

        # Malware/Downloader signatures
        download_cmds = ["wget", "curl", "tftp", "ftp", "certutil", "powershell"]
        if has_word(download_cmds, payload_lower):
            return {
                "name": "malware_download",
                "category": AttackCategory.MALWARE_DELIVERY.value,
                "severity": AttackSeverity.HIGH.value,
            }

        # System Modification
        mod_cmds = ["mkdir", "touch", "rm", "chmod", "chown", "cp", "mv", "scp", "echo"]
        if has_word(mod_cmds, payload_lower):
            return {
                "name": "system_modification",
                "category": AttackCategory.EXPLOIT_ATTEMPT.value,
                "severity": AttackSeverity.MEDIUM.value,
            }

        # Reconnaissance / System Info
        recon_cmds = [
            "ls",
            "dir",
            "cd",
            "pwd",
            "whoami",
            "id",
            "uname",
            "ps",
            "netstat",
            "ip",
            "ifconfig",
            "cat",
            "grep",
            "tail",
            "head",
            "more",
            "less",
        ]
        if has_word(recon_cmds, payload_lower) or "cat /proc/" in payload_lower:
            return {
                "name": "system_recon",
                "category": AttackCategory.RECONNAISSANCE.value,
                "severity": AttackSeverity.LOW.value,
            }

        return None

    async def correlate_with_cves(
        self,
        category: str,
        patterns: List[str],
    ) -> List[str]:
        """Get CWE IDs that map to attack patterns.

        Args:
            category: Attack category
            patterns: Detected patterns

        Returns:
            List of CWE IDs
        """
        # CWE mapping
        category_cwe_map = {
            "sql_injection": ["CWE-89", "CWE-564"],
            "command_injection": ["CWE-78", "CWE-77"],
            "path_traversal": ["CWE-22", "CWE-23"],
            "xss": ["CWE-79", "CWE-80"],
            "brute_force": ["CWE-307", "CWE-521"],
            "reconnaissance": ["CWE-200"],
            "credential_harvesting": ["CWE-522", "CWE-523"],
        }
        return category_cwe_map.get(category, [])

    async def request_deep_analysis(
        self,
        payload: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[str]:
        """Request deep AI analysis from CVE Hunter plugin.

        Args:
            payload: Attack payload
            context: Analysis context

        Returns:
            Request ID if successful
        """
        try:
            from ..events import emit_honeypot_event

            request_id = f"req-{uuid4().hex[:8]}"

            await emit_honeypot_event(
                "honeypot.integration.attack_for_analysis",
                {
                    "request_id": request_id,
                    "payload": payload,
                    "context": context or {},
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

            logger.info(f"Requested deep analysis from CVE Hunter: {request_id}")
            return request_id

        except Exception as e:
            logger.error(f"Failed to request deep analysis: {e}")
            return None
