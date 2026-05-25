"""LLM-driven planner configuration mixin.

Activated when ``llm_planner_enabled=True`` and an engagement's
autonomy reaches at least ``execute_active``. The orchestrator
substitutes :class:`LLMReasoningPlanner` for the rule-based default.

All knobs default to safe values: planner stays off, falls back to the
deterministic chain on any LLM failure, and a hard token cap stops
runaway loops from burning provider budget.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class _LLMPlannerConfig(BaseModel):
    llm_planner_enabled: bool = Field(
        default=False,
        description=(
            "Enable the LLM reasoning planner. When false the orchestrator "
            "uses ChainingPlanner / DeterministicPlanner per multi_step_chains."
        ),
    )
    llm_planner_provider: Literal["anthropic", "openai", "ollama"] = Field(
        default="anthropic",
        description="LLM provider used by the planner. Falls back per fallback policy.",
    )
    llm_planner_model: str = Field(
        default="claude-opus-4-7",
        description=(
            "Model identifier passed to the provider. Reasoning-heavy default "
            "for plan synthesis; switch to a smaller model for cost/latency."
        ),
    )
    llm_planner_max_tokens_per_scan: int = Field(
        default=50_000,
        description=(
            "Hard token budget per scan summed across all planner LLM calls. "
            "Once exhausted the planner halts and the scan reaches COMPLETED "
            "with whatever findings have been collected."
        ),
    )
    llm_planner_max_iterations: int = Field(
        default=8,
        description="Upper bound on planner iterations per scan.",
    )
    llm_planner_max_tokens_per_call: int = Field(
        default=2_048,
        description="Per-call generation cap passed through to the provider.",
    )
    llm_planner_temperature: float = Field(
        default=0.2,
        description=(
            "Sampling temperature. Low default keeps plans deterministic; "
            "raise for exploratory engagements."
        ),
    )
    llm_planner_redact_secrets: bool = Field(
        default=True,
        description=(
            "Strip known credential / token patterns from finding evidence "
            "before passing to the LLM. Disable only for offline labs."
        ),
    )
    llm_planner_fallback_to_deterministic: bool = Field(
        default=True,
        description=(
            "On provider error, parse failure, or budget exhaustion, fall "
            "back to ChainingPlanner for the rest of the scan instead of "
            "halting immediately."
        ),
    )


__all__ = ["_LLMPlannerConfig"]
