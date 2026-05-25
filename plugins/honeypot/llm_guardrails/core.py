"""Integrated security layer."""

from typing import Any, Callable, Dict, Optional, Tuple

from .prompts import HardenedSystemPrompt, InstructionHierarchy, InstructionPriority
from .filtering import OutputFilter
from .refusal import RefusalPolicy, RefusalResponse


class LLMSecurityLayer:
    """Integrated security layer combining all guardrails.

    Provides a single interface for applying all security measures
    to LLM interactions.
    """

    def __init__(
        self,
        system_prompt: HardenedSystemPrompt,
        output_filter: Optional[OutputFilter] = None,
        refusal_policy: Optional[RefusalPolicy] = None,
        instruction_hierarchy: Optional[InstructionHierarchy] = None,
    ) -> None:
        """Initialize security layer.

        Args:
            system_prompt: Hardened system prompt to use
            output_filter: Output filter (created if None)
            refusal_policy: Refusal policy (created if None)
            instruction_hierarchy: Instruction hierarchy (created if None)
        """
        self.system_prompt = system_prompt
        self.output_filter = output_filter or OutputFilter()
        self.refusal_policy = refusal_policy or RefusalPolicy()
        self.instruction_hierarchy = instruction_hierarchy or InstructionHierarchy()

        # Add system prompt to hierarchy
        self.instruction_hierarchy.add_instruction(
            content=system_prompt.core_directive,
            priority=InstructionPriority.SYSTEM,
            source="hardened_system_prompt",
        )

    def process_input(
        self,
        user_input: str,
        sanitize_fn: Optional[Callable[[str], str]] = None,
    ) -> Tuple[Optional[str], Optional[RefusalResponse]]:
        """Process and validate user input.

        Args:
            user_input: Raw user input
            sanitize_fn: Optional sanitization function

        Returns:
            Tuple of (safe_prompt, refusal_response)
            If refusal_response is not None, the request should be refused
        """
        # 1. Check instruction hierarchy
        is_safe, override_attempts = self.instruction_hierarchy.validate_input(
            user_input
        )

        if not is_safe:
            reason = self.refusal_policy.should_refuse(
                injection_score=0.0,
                override_detected=True,
            )
            if reason:
                return None, self.refusal_policy.create_refusal(
                    reason=reason,
                    details=f"Override attempts: {override_attempts[:3]}",
                )

        # 2. Sanitize input if function provided
        safe_input = sanitize_fn(user_input) if sanitize_fn else user_input

        # 3. Build secure prompt
        full_prompt = self.system_prompt.build(safe_input)

        return full_prompt, None

    def process_output(self, llm_output: str) -> Tuple[str, Dict[str, Any]]:
        """Process and filter LLM output.

        Args:
            llm_output: Raw LLM output

        Returns:
            Tuple of (filtered_output, filter_stats)
        """
        return self.output_filter.filter(llm_output)
