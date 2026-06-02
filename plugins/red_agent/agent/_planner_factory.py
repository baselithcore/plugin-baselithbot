"""Default-planner selection extracted from ``agent.py``.

Kept out of ``RedAgent.__init__`` to avoid an import cycle through the
LLM planner's optional ``core.services.llm`` dependency.
"""

from __future__ import annotations

from plugins.red_agent.audit import AuditLogger
from plugins.red_agent.config import RedAgentConfig
from plugins.red_agent.planner import (
    AttackPlanner,
    ChainingPlanner,
    DeterministicPlanner,
)


def _build_default_planner(
    *, config: RedAgentConfig, audit: AuditLogger
) -> AttackPlanner:
    """Pick the planner backend that matches the active configuration.

    LLM planner wins when explicitly enabled; otherwise the rule-based
    chain (multi-step or single-pass deterministic) is used. Kept out
    of ``RedAgent.__init__`` to avoid an import cycle through the LLM
    planner's optional ``core.services.llm`` dependency.
    """

    if getattr(config, "llm_planner_enabled", False):
        from plugins.red_agent.llm_planner import build_llm_planner

        return build_llm_planner(
            config=config,
            audit=audit,
            enabled_scanners=list(config.enabled_scanners),
            fallback_planner=ChainingPlanner(
                max_iterations=config.chain_max_iterations
            ),
        )
    if config.multi_step_chains:
        return ChainingPlanner(max_iterations=config.chain_max_iterations)
    return DeterministicPlanner()
