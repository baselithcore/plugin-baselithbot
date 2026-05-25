"""LLM Security Guardrails for Honeypot Plugin.

Provides hardened system prompts, output filtering, instruction hierarchy,
and explicit refusal policies to prevent LLM manipulation attacks.
"""

from .prompts import (
    InstructionPriority,
    TaggedInstruction,
    InstructionHierarchy,
    HardenedSystemPrompt,
    SSH_HARDENED_PROMPT,
    HTTP_HARDENED_PROMPT,
)
from .filtering import OutputFilterConfig, OutputFilter
from .refusal import RefusalReason, RefusalResponse, RefusalPolicy
from .core import LLMSecurityLayer

__all__ = [
    # Instruction Hierarchy
    "InstructionPriority",
    "TaggedInstruction",
    "InstructionHierarchy",
    # System Prompt
    "HardenedSystemPrompt",
    "SSH_HARDENED_PROMPT",
    "HTTP_HARDENED_PROMPT",
    # Output Filtering
    "OutputFilterConfig",
    "OutputFilter",
    # Refusal Policy
    "RefusalReason",
    "RefusalResponse",
    "RefusalPolicy",
    # Integrated Layer
    "LLMSecurityLayer",
]
