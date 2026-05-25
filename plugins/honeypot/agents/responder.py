"""LLM Responder Agent.

Generates realistic responses for honeypot interactions using
the core LLMService with enhanced security guardrails.
"""

from core.observability.logging import get_logger
from typing import Any, Dict, Optional

from ..config import HoneypotConfig, get_honeypot_config
from ..security import (
    sanitize_for_llm,
    detect_injection_attempt,
    calculate_injection_score,
)
from ..llm_guardrails import (
    SSH_HARDENED_PROMPT,
    HTTP_HARDENED_PROMPT,
    LLMSecurityLayer,
    OutputFilter,
    RefusalPolicy,
)
from core.observability.tracing import get_tracer
from core.evaluation.service import EvaluationService

logger = get_logger(__name__)
tracer = get_tracer(__name__)


# Legacy prompts - kept for backward compatibility but deprecated
# New code should use SSH_HARDENED_PROMPT and HTTP_HARDENED_PROMPT from llm_guardrails
SSH_SYSTEM_PROMPT = SSH_HARDENED_PROMPT.core_directive
HTTP_SYSTEM_PROMPT = HTTP_HARDENED_PROMPT.core_directive


class LLMResponder:
    """LLM-powered response generator for honeypot with security guardrails."""

    def __init__(
        self, config: Optional[HoneypotConfig] = None, llm_service: Optional[Any] = None
    ):
        """Initialize LLM responder with security layer.

        Args:
            config: Optional configuration (uses default if None)
            llm_service: Optional LLM service (lazy loaded if None)
        """
        self.config = config or get_honeypot_config()
        self.llm_service = llm_service
        self.evaluation_service: Optional[EvaluationService] = None
        self._initialized = False

        # Response cache to avoid repeated LLM calls
        self._response_cache: Dict[str, str] = {}

        # Initialize security components
        self._output_filter = OutputFilter()
        self._refusal_policy = RefusalPolicy(detection_threshold=0.5)

        # Security layers for different contexts
        self._ssh_security = LLMSecurityLayer(
            system_prompt=SSH_HARDENED_PROMPT,
            output_filter=self._output_filter,
            refusal_policy=self._refusal_policy,
        )
        self._http_security = LLMSecurityLayer(
            system_prompt=HTTP_HARDENED_PROMPT,
            output_filter=self._output_filter,
            refusal_policy=self._refusal_policy,
        )

    async def initialize(self) -> bool:
        """Initialize LLM service.

        Uses HONEYPOT_ATTACK_ANALYSIS_PROVIDER and HONEYPOT_ATTACK_ANALYSIS_MODEL
        env vars if available for attack analysis, otherwise uses default LLM config.

        Returns:
            True if successfully initialized
        """
        if self._initialized:
            return True

        if not self.config.enable_llm_responses:
            logger.info("LLM responses disabled in config")
            return False

        try:
            import os
            from core.services.llm.service import LLMService
            from core.config.services import LLMConfig

            # Check for attack analysis specific LLM configuration (multiple patterns for compatibility)
            analysis_provider = os.getenv(
                "HONEYPOT_ATTACK_ANALYSIS_PROVIDER"
            ) or os.getenv("HONEYPOT_ANALYSIS_LLM_PROVIDER")
            analysis_model = os.getenv("HONEYPOT_ATTACK_ANALYSIS_MODEL") or os.getenv(
                "HONEYPOT_ANALYSIS_LLM_MODEL"
            )
            analysis_api_key = os.getenv(
                "HONEYPOT_ATTACK_ANALYSIS_API_KEY"
            ) or os.getenv("HONEYPOT_ANALYSIS_LLM_API_KEY")

            if analysis_provider and analysis_model:
                # Use attack analysis specific configuration
                logger.info(
                    f"Using attack analysis specific LLM: {analysis_provider}/{analysis_model}"
                )

                # Create custom LLM config with analysis-specific settings
                custom_config = LLMConfig(
                    provider=analysis_provider,
                    model=analysis_model,
                    api_key=analysis_api_key or os.getenv("OPENAI_API_KEY"),
                )
                self._llm_service = LLMService(config=custom_config)
            else:
                # Use default LLM configuration
                from core.services.llm import get_llm_service

                self._llm_service = get_llm_service()
                logger.info(
                    f"LLM Responder initialized with default provider: {self.config.llm_provider}"
                )

            # Lazy load EvaluationService
            if not self.evaluation_service:
                try:
                    from core.evaluation.service import EvaluationService

                    self.evaluation_service = EvaluationService()
                except Exception as e:
                    logger.debug(f"EvaluationService not available: {e}")

            self._initialized = True
            return True

        except Exception as e:
            logger.warning(f"Failed to initialize LLM service: {e}")
            return False

    @tracer.traced(name="honeypot_generate_ssh_response")
    async def generate_ssh_response(
        self,
        command: str,
        session_context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate realistic SSH command response with security guardrails.

        Args:
            command: Command executed by attacker
            session_context: Optional session context for personalization

        Returns:
            Fake command output (filtered for safety)
        """
        # Check cache
        cache_key = f"ssh:{command}"
        if cache_key in self._response_cache:
            return self._response_cache[cache_key]

        # Use static responses if LLM not available
        if not self._initialized or not self._llm_service:
            return self._static_ssh_response(command)

        try:
            # Calculate injection risk score
            injection_score = calculate_injection_score(command)

            # Check if we should refuse this request
            refuse_reason = self._refusal_policy.should_refuse(
                injection_score=injection_score,
                override_detected=injection_score > 0.7,
            )

            if refuse_reason:
                logger.warning(
                    f"SSH request refused: {refuse_reason.name} (score={injection_score})"
                )
                # Return static response instead of LLM response for suspicious input
                return self._static_ssh_response(command)

            # Security: Sanitize attacker input to prevent prompt injection
            safe_command = sanitize_for_llm(
                command, max_length=self.config.llm_sanitization_max_length
            )
            is_suspicious, patterns = detect_injection_attempt(command)
            if is_suspicious:
                logger.warning(
                    f"Potential prompt injection detected in SSH command: {patterns[:3]}"
                )

            # Build secure prompt using hardened system prompt
            full_prompt = SSH_HARDENED_PROMPT.build(safe_command)
            if session_context:
                full_prompt = (
                    f"Session: {session_context.get('username', 'user')}\n{full_prompt}"
                )

            response = await self._llm_service.generate_response(
                prompt=full_prompt,
            )

            # Apply output filtering before caching/returning
            filtered_response, filter_stats = self._output_filter.filter(response)
            if filter_stats["filtered"]:
                logger.info(f"SSH response filtered: {filter_stats}")

            # Optional: Evaluate response quality if service available
            if self.evaluation_service:
                try:
                    eval_result = await self.evaluation_service.evaluate_response(
                        query=command,
                        response=filtered_response,
                        metrics=["relevance", "safety"],
                    )
                    if not eval_result.is_passing:
                        logger.warning(
                            f"LLM response failed safety/relevance check: {eval_result.reason}"
                        )
                        return self._static_ssh_response(command)
                except Exception as e:
                    logger.debug(f"Evaluation skipped: {e}")

            # Cache and return filtered response
            self._response_cache[cache_key] = filtered_response
            return filtered_response

        except Exception as e:
            logger.warning(f"LLM response failed: {e}")
            return self._static_ssh_response(command)

    @tracer.traced(name="honeypot_generate_http_response")
    async def generate_http_response(
        self,
        path: str,
        method: str = "GET",
        body: Optional[str] = None,
    ) -> str:
        """Generate realistic HTTP response content with security guardrails.

        Args:
            path: HTTP request path
            method: HTTP method
            body: Optional request body

        Returns:
            Fake HTTP response content (filtered for safety)
        """
        cache_key = f"http:{method}:{path}"
        if cache_key in self._response_cache:
            return self._response_cache[cache_key]

        if not self._initialized or not self._llm_service:
            return self._static_http_response(path)

        try:
            # Calculate injection risk score for combined input
            combined_input = f"{path} {body or ''}"
            injection_score = calculate_injection_score(combined_input)

            # Check if we should refuse this request
            refuse_reason = self._refusal_policy.should_refuse(
                injection_score=injection_score,
                override_detected=injection_score > 0.7,
            )

            if refuse_reason:
                logger.warning(
                    f"HTTP request refused: {refuse_reason.name} (score={injection_score})"
                )
                return self._static_http_response(path)

            # Security: Sanitize attacker input
            safe_path = sanitize_for_llm(
                path, max_length=self.config.llm_sanitization_max_length
            )
            safe_body = (
                sanitize_for_llm(
                    body[: self.config.llm_sanitization_max_length],
                    max_length=self.config.llm_sanitization_max_length,
                )
                if body
                else None
            )

            is_suspicious, patterns = detect_injection_attempt(combined_input)
            if is_suspicious:
                logger.warning(
                    f"Potential prompt injection detected in HTTP request: {patterns[:3]}"
                )

            # Build context for hardened prompt
            user_context = f"Path: [{safe_path}]\nMethod: {method}"
            if safe_body:
                user_context += f"\nBody: [{safe_body}]"

            # Build secure prompt using hardened system prompt
            full_prompt = HTTP_HARDENED_PROMPT.build(user_context)

            response = await self._llm_service.generate_response(
                prompt=full_prompt,
            )

            # Apply output filtering before caching/returning
            filtered_response, filter_stats = self._output_filter.filter(response)
            if filter_stats["filtered"]:
                logger.info(f"HTTP response filtered: {filter_stats}")

            self._response_cache[cache_key] = filtered_response
            return filtered_response

        except Exception as e:
            logger.warning(f"LLM response failed: {e}")
            return self._static_http_response(path)

    @tracer.traced(name="honeypot_analyze_attack_intent")
    async def analyze_attack_intent(
        self,
        payload: str,
        protocol: str,
    ) -> Dict[str, Any]:
        """Analyze attacker intent from payload.

        Args:
            payload: Attack payload
            protocol: Protocol (ssh/http)

        Returns:
            Analysis with intent, severity, recommendations
        """
        if not self._initialized or not self._llm_service:
            return {
                "intent": "unknown",
                "severity": "medium",
                "summary": "LLM analysis unavailable",
            }

        try:
            # Security: Sanitize payload before LLM analysis
            safe_payload = sanitize_for_llm(
                payload[: self.config.llm_sanitization_max_length],
                max_length=self.config.llm_sanitization_max_length,
            )

            is_suspicious, _ = detect_injection_attempt(payload)
            if is_suspicious:
                logger.warning(
                    "Potential prompt injection in attack payload for analysis"
                )

            prompt = f"""Analyze this {protocol} attack payload:

[ATTACKER_PAYLOAD_START]
{safe_payload}
[ATTACKER_PAYLOAD_END]

Provide brief analysis in JSON format:
{{"intent": "...", "severity": "low/medium/high/critical", "summary": "..."}}"""

            response = await self._llm_service.generate_response(prompt=prompt)

            # Try to parse JSON from response
            import json

            try:
                return json.loads(response)
            except json.JSONDecodeError:
                return {
                    "intent": "unknown",
                    "severity": "medium",
                    "summary": response[:200],
                }

        except Exception as e:
            logger.warning(f"Attack analysis failed: {e}")
            return {
                "intent": "unknown",
                "severity": "medium",
                "summary": str(e),
            }

    def _static_ssh_response(self, command: str) -> str:
        """Generate static SSH response."""
        cmd_lower = command.lower().strip()

        if cmd_lower == "ls" or cmd_lower.startswith("ls "):
            return "Desktop  Documents  Downloads  .ssh  .bashrc  backup.tar.gz"
        if cmd_lower == "pwd":
            return "/home/admin"
        if cmd_lower == "whoami":
            return "admin"
        if cmd_lower == "id":
            return "uid=1000(admin) gid=1000(admin) groups=1000(admin),27(sudo)"
        if cmd_lower.startswith("cat "):
            return "Permission denied"
        if cmd_lower == "uname -a":
            return "Linux server 5.4.0-generic #1 SMP x86_64 GNU/Linux"
        if cmd_lower == "ps aux":
            return "USER  PID %CPU %MEM    VSZ   RSS TTY STAT START   TIME COMMAND\nroot    1  0.0  0.1  51128  3892 ?   Ss   00:00   0:02 /sbin/init"
        if cmd_lower.startswith("cd "):
            return ""

        return f"bash: {command.split()[0]}: command not found"

    def _static_http_response(self, path: str) -> str:
        """Generate static HTTP response."""
        if "login" in path.lower() or "admin" in path.lower():
            return """<!DOCTYPE html>
<html><head><title>Admin Login</title></head>
<body>
<form method="post">
<input name="username" placeholder="Username">
<input name="password" type="password" placeholder="Password">
<button>Login</button>
</form>
</body></html>"""

        if "api" in path.lower():
            return '{"status": "error", "message": "Unauthorized"}'

        return """<!DOCTYPE html>
<html><head><title>Welcome</title></head>
<body><h1>Welcome</h1><p>Server is running.</p></body></html>"""

    def clear_cache(self) -> None:
        """Clear response cache."""
        self._response_cache.clear()
