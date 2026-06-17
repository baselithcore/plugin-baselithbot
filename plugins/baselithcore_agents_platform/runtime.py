"""Scoped execution runtime for synthesised agents.

The runtime is where a blueprint is enforced. Every invocation is gated against
the blueprint's capability allow-list and grounded in the documentation
namespaces the blueprint declares. Heavy lifting (fix/test loops, sandboxed
execution) is delegated to the framework's native ``CodingAgent`` rather than
re-implemented — the platform composes core capabilities, it does not fork them.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any

from core.observability import get_tracer
from core.observability.logging import get_logger
from core.orchestration.limits import BudgetExceededError, LoopBudget, LoopLimits

from .docs_index import DocIndexer
from .prompts import SCOPED_CODING_SYSTEM_PROMPT, get_scoped_generate_prompt
from .providers import ProviderUnavailableError, resolve_llm_service
from .types import (
    AgentBlueprint,
    AgentCapability,
    AgentRunResult,
    DocCitation,
    RunStatus,
)

logger = get_logger(__name__)

__all__ = ["AgentRuntime"]


def _strip_fences(text: str) -> str:
    """Remove a single leading/trailing Markdown code fence if present."""
    stripped = text.strip()
    if not stripped.startswith("```"):
        return stripped
    first_newline = stripped.find("\n")
    if first_newline == -1:
        return stripped
    body = stripped[first_newline + 1 :]
    if body.rstrip().endswith("```"):
        body = body.rstrip()[:-3]
    return body.strip()


class _CodingAgentLLM:
    """Adapter exposing the ``generate(...) -> obj.content`` API CodingAgent
    expects, backed by the framework's ``LLMService.generate_response``."""

    def __init__(self, service: Any) -> None:
        self._service = service

    async def generate(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.0,
        **_: Any,
    ) -> SimpleNamespace:
        """Return an object whose ``.content`` holds the generated text."""
        del temperature  # honoured by the underlying service config
        text = await self._service.generate_response(
            prompt=prompt, system_prompt=system_prompt
        )
        return SimpleNamespace(content=text)


class AgentRuntime:
    """Executes a blueprint's capabilities within its declared scope.

    Args:
        docs: Shared documentation indexer used for grounding.
        ollama_base: Optional Ollama base URL for local-model runs.
    """

    def __init__(
        self,
        docs: DocIndexer,
        ollama_base: str | None = None,
        executor: Any | None = None,
    ) -> None:
        self._docs = docs
        self._ollama_base = ollama_base
        self._executor = executor
        self._tracer = get_tracer("agents-platform")

    async def run(
        self,
        blueprint: AgentBlueprint,
        capability: AgentCapability,
        task: str,
        extra_context: str = "",
    ) -> AgentRunResult:
        """Run one capability of an agent against a task.

        Args:
            blueprint: The agent specification to execute.
            capability: The requested action; rejected if outside scope.
            task: The concrete instruction (description, code, or error).
            extra_context: Optional caller-supplied context (e.g. failing code).

        Returns:
            An :class:`AgentRunResult` capturing output, citations, and status.
        """
        run_id = uuid.uuid4().hex
        if capability not in blueprint.scope.capabilities:
            logger.warning(
                "capability_out_of_scope",
                blueprint=blueprint.id,
                capability=capability.value,
            )
            return AgentRunResult(
                run_id=run_id,
                blueprint_id=blueprint.id,
                capability=capability,
                status=RunStatus.REJECTED,
                error=(
                    f"capability '{capability.value}' is outside this agent's "
                    f"declared scope {[c.value for c in blueprint.scope.capabilities]}"
                ),
            )

        # Native loop-budget: hard caps on iterations and tool calls for this
        # run, derived from the blueprint's scope. Mirrors the orchestrator's
        # ExecutionMixin contract (tick before a step, record each tool call).
        budget = LoopBudget(
            LoopLimits(
                max_iterations=blueprint.scope.max_iterations,
                max_tool_calls=blueprint.scope.max_iterations * 2,
            )
        )
        citations = await self._ground(blueprint, task)

        with self._tracer.start_span(
            "agents_platform.run",
            attributes={
                "agent.blueprint": blueprint.id,
                "agent.capability": capability.value,
                "agent.provider": blueprint.provider.value,
            },
        ) as span:
            try:
                budget.tick()
                result = await self._dispatch(
                    run_id,
                    blueprint,
                    capability,
                    task,
                    extra_context,
                    citations,
                    budget,
                )
            except BudgetExceededError as exc:
                span.set_attribute("agent.status", "budget_exceeded")
                return self._failed(run_id, blueprint, capability, str(exc), citations)
            except ProviderUnavailableError as exc:
                span.set_attribute("agent.status", RunStatus.FAILED.value)
                return self._failed(run_id, blueprint, capability, str(exc), citations)
            except Exception as exc:  # never leak a raw 500 to the caller
                logger.error("agent_run_error", blueprint=blueprint.id, error=str(exc))
                span.set_attribute("agent.status", RunStatus.FAILED.value)
                return self._failed(run_id, blueprint, capability, str(exc), citations)

            snapshot = budget.snapshot()
            result.metadata["budget"] = {
                "iterations": snapshot.iterations,
                "tool_calls": snapshot.tool_calls,
            }
            span.set_attribute("agent.status", result.status.value)
            span.set_attribute("agent.tool_calls", snapshot.tool_calls)
            return result

    async def _ground(self, blueprint: AgentBlueprint, task: str) -> list[DocCitation]:
        """Retrieve documentation excerpts scoped to the blueprint."""
        return await self._docs.search(
            query=f"{blueprint.description} {task}",
            namespaces=blueprint.scope.doc_namespaces or None,
            top_k=4,
        )

    async def _dispatch(
        self,
        run_id: str,
        blueprint: AgentBlueprint,
        capability: AgentCapability,
        task: str,
        extra_context: str,
        citations: list[DocCitation],
        budget: LoopBudget,
    ) -> AgentRunResult:
        """Route a capability to its handler."""
        if capability is AgentCapability.OPERATE:
            if self._executor is None:
                raise RuntimeError("operate capability requires a configured executor")
            budget.record_tool_call()
            return await self._executor.operate(blueprint, task, citations)
        if capability in (AgentCapability.FIX, AgentCapability.TEST):
            return await self._via_coding_agent(
                run_id, blueprint, capability, task, extra_context, citations, budget
            )
        return await self._via_scoped_llm(
            run_id, blueprint, capability, task, citations, budget
        )

    async def _via_scoped_llm(
        self,
        run_id: str,
        blueprint: AgentBlueprint,
        capability: AgentCapability,
        task: str,
        citations: list[DocCitation],
        budget: LoopBudget,
    ) -> AgentRunResult:
        """Handle generate/refactor/explain via a doc-grounded LLM call."""
        budget.record_tool_call()
        service = resolve_llm_service(
            blueprint.provider, blueprint.model, self._ollama_base
        )
        doc_context = "\n\n".join(f"# {c.namespace}\n{c.snippet}" for c in citations)
        prompt = get_scoped_generate_prompt(
            blueprint.system_directive,
            task,
            blueprint.scope.language,
            doc_context,
        )
        response = await service.generate_response(
            prompt=prompt,
            system_prompt=SCOPED_CODING_SYSTEM_PROMPT,
        )
        is_prose = capability is AgentCapability.EXPLAIN
        output = response.strip() if is_prose else _strip_fences(response)
        return AgentRunResult(
            run_id=run_id,
            blueprint_id=blueprint.id,
            capability=capability,
            status=RunStatus.SUCCEEDED,
            output=output,
            explanation=f"{capability.value} completed for '{blueprint.name}'",
            iterations=1,
            citations=citations,
        )

    async def _via_coding_agent(
        self,
        run_id: str,
        blueprint: AgentBlueprint,
        capability: AgentCapability,
        task: str,
        extra_context: str,
        citations: list[DocCitation],
        budget: LoopBudget,
    ) -> AgentRunResult:
        """Delegate fix/test to the native CodingAgent (sandbox-backed)."""
        budget.record_tool_call()
        agent = self._make_coding_agent(blueprint)
        if capability is AgentCapability.FIX:
            result = await agent.fix_code(
                code=extra_context, error_message=task, context=blueprint.description
            )
        else:  # TEST
            result = await agent.generate_tests(code=extra_context or task)

        return AgentRunResult(
            run_id=run_id,
            blueprint_id=blueprint.id,
            capability=capability,
            status=RunStatus.SUCCEEDED if result.success else RunStatus.FAILED,
            output=result.final_code,
            explanation=result.explanation,
            iterations=result.iterations,
            error=result.error,
            citations=citations,
        )

    def _make_coding_agent(self, blueprint: AgentBlueprint) -> Any:
        """Instantiate the native CodingAgent bound to the blueprint's scope.

        The CodingAgent expects an LLM client exposing ``generate(...) -> obj``
        with a ``.content`` attribute, but the framework's ``LLMService`` exposes
        ``generate_response(...) -> str``. We inject a thin adapter so the native
        sandbox/auto-debug loop runs against the blueprint's chosen provider.
        """
        from plugins.coding_agent.agent import CodingAgent
        from plugins.coding_agent.types import CodeLanguage

        try:
            language = CodeLanguage(blueprint.scope.language)
        except ValueError:
            language = CodeLanguage.PYTHON
        agent = CodingAgent(
            max_fix_attempts=blueprint.scope.max_iterations,
            language=language,
        )
        agent._llm = _CodingAgentLLM(
            resolve_llm_service(blueprint.provider, blueprint.model, self._ollama_base)
        )
        return agent

    @staticmethod
    def _failed(
        run_id: str,
        blueprint: AgentBlueprint,
        capability: AgentCapability,
        error: str,
        citations: list[DocCitation],
    ) -> AgentRunResult:
        """Build a failed run result."""
        return AgentRunResult(
            run_id=run_id,
            blueprint_id=blueprint.id,
            capability=capability,
            status=RunStatus.FAILED,
            error=error,
            citations=citations,
        )
