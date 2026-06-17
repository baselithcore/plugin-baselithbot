"""Live agent execution via the core ReAct loop.

The ``operate`` capability turns a blueprint into a *running* agent: it composes
the framework's :class:`ReActAgent` (core Thought/Action/Observation loop) with
the platform's scoped runtime tools and the blueprint's chosen provider. The
reasoning trace is preserved in the run result for transparency and audit.
"""

from __future__ import annotations

import uuid

from core.observability.logging import get_logger
from core.reasoning.react import ReActAgent

from .providers import resolve_llm_service
from .tools_runtime import ToolConfig, build_runtime_tools
from .types import (
    AgentBlueprint,
    AgentCapability,
    AgentRunResult,
    DocCitation,
    RunStatus,
)

logger = get_logger(__name__)

__all__ = ["AgentExecutor"]


class AgentExecutor:
    """Runs a blueprint's ``operate`` capability as a live ReAct agent.

    Args:
        tool_config: Credentials/policy for the runtime tools (Telegram, SSRF).
        ollama_base: Optional Ollama base URL for local-model runs.
    """

    def __init__(self, tool_config: ToolConfig, ollama_base: str | None = None) -> None:
        self._tool_config = tool_config
        self._ollama_base = ollama_base

    async def operate(
        self,
        blueprint: AgentBlueprint,
        task: str,
        citations: list[DocCitation],
    ) -> AgentRunResult:
        """Execute a live, tool-using agent run for *task*.

        Args:
            blueprint: The agent specification (provider, scope, directive).
            task: The operational instruction to carry out.
            citations: Documentation excerpts used to ground the run.

        Returns:
            An :class:`AgentRunResult` whose ``output`` is the agent's final
            answer and whose ``metadata`` carries the full reasoning trace.
        """
        run_id = uuid.uuid4().hex
        tools = build_runtime_tools(blueprint.scope.allowed_tools, self._tool_config)
        service = resolve_llm_service(
            blueprint.provider, blueprint.model, self._ollama_base
        )

        doc_context = "\n".join(
            f"- {c.namespace}: {c.snippet[:160]}" for c in citations
        )
        directive = blueprint.system_directive or (
            "You are a focused operational agent. Use tools precisely and stop "
            "as soon as the task is done."
        )
        extra = directive
        if doc_context:
            extra += f"\n\nReference context:\n{doc_context}"

        agent = ReActAgent(
            tools=tools,
            max_iterations=blueprint.scope.max_iterations,
            llm_service=service,
            system_prompt_extra=extra,
        )

        result = await agent.run(task)
        logger.info(
            "operate_run_complete",
            blueprint=blueprint.id,
            iterations=result.iterations_used,
            hit_limit=result.hit_limit,
            tools=len(tools),
        )
        return AgentRunResult(
            run_id=run_id,
            blueprint_id=blueprint.id,
            capability=AgentCapability.OPERATE,
            status=RunStatus.SUCCEEDED if not result.hit_limit else RunStatus.FAILED,
            output=result.final_answer,
            explanation=(
                f"operated in {result.iterations_used} step(s) "
                f"with {len(tools)} tool(s)"
            ),
            iterations=result.iterations_used,
            error="iteration budget exhausted" if result.hit_limit else None,
            citations=citations,
            metadata={
                "tools": [t.name for t in tools],
                "trace": [str(step) for step in result.trace],
                "hit_limit": result.hit_limit,
            },
        )
