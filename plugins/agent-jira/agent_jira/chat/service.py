import asyncio
import contextvars
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, AsyncIterator, Dict, Iterator, Optional

from agent_jira.chat.dependencies import (
    ChatDependencies,
    ChatDependencyConfig,
    create_default_dependencies,
)
from agent_jira.metrics import (
    CHAT_REQUEST_ERRORS_TOTAL,
    CHAT_REQUEST_LATENCY_SECONDS,
    CHAT_REQUESTS_TOTAL,
)
from agent_jira.models import ChatRequest
from agent_jira.config import (
    CHAT_FINAL_TOP_K,
    CHAT_INITIAL_SEARCH_K,
    CHAT_RERANK_THRESHOLD,
    CHAT_STREAMING_ENABLED,
    JIRA_REQUIRE_MANUAL_APPROVAL,
)

_STREAM_EOF = object()
logger = logging.getLogger(__name__)


def _next_stream_chunk(iterator: Iterator[str]):
    try:
        return next(iterator)
    except StopIteration:
        return _STREAM_EOF


class ChatService:
    FINAL_TOP_K = CHAT_FINAL_TOP_K
    INITIAL_SEARCH_K = CHAT_INITIAL_SEARCH_K
    RERANK_THRESHOLD = CHAT_RERANK_THRESHOLD

    def __init__(
        self,
        *,
        dependencies: Optional[ChatDependencies] = None,
        dependency_config: Optional[ChatDependencyConfig] = None,
    ) -> None:
        if dependencies is None:
            dependencies = create_default_dependencies(dependency_config)
        self.dependencies = dependencies

        self.embedder = self.dependencies.embedder
        self.reranker = self.dependencies.reranker
        self.response_cache = self.dependencies.response_cache
        self.rerank_cache = self.dependencies.rerank_cache
        self.history_manager = self.dependencies.history_manager

        self.newline = self.dependencies.newline
        self.double_newline = self.dependencies.double_newline
        self.section_separator = self.dependencies.section_separator
        self.project_planner = self.dependencies.project_planner
        self.jira_client = self.dependencies.jira_client
        self.jira_manual_approval = JIRA_REQUIRE_MANUAL_APPROVAL

        # Lazy initialization
        self._agent = None
        self._last_sources: dict[str, set[str]] = {}
        self._executor = ThreadPoolExecutor(
            max_workers=20, thread_name_prefix="chat-worker"
        )

    @property
    def agent(self):
        if self._agent is None:
            from agent_jira.agents.orchestrator_agent import OrchestratorAgent

            self._agent = OrchestratorAgent(self)
        return self._agent

    def handle_chat(self, req: ChatRequest) -> Dict[str, Any]:
        start = time.perf_counter()
        CHAT_REQUESTS_TOTAL.labels(route="sync").inc()
        try:
            result = self.agent.handle_user_message(req)
            result["duration"] = time.perf_counter() - start
            return result
        except Exception:
            CHAT_REQUEST_ERRORS_TOTAL.labels(route="sync", reason="exception").inc()
            logger.exception("Chat sync failed")
            raise
        finally:
            duration = time.perf_counter() - start
            CHAT_REQUEST_LATENCY_SECONDS.labels(route="sync").observe(duration)

    def handle_chat_stream(self, req: ChatRequest):
        """
        Gestisce la chat in streaming delegando all'OrchestratorAgent.
        Se CHAT_STREAMING_ENABLED=false, restituisce la risposta completa in un unico blocco.
        """
        start = time.perf_counter()
        CHAT_REQUESTS_TOTAL.labels(route="stream").inc()
        try:
            # Check if streaming is enabled
            if not CHAT_STREAMING_ENABLED:
                # Return full response in one chunk
                result = self.agent.handle_user_message(req)
                # Convert result to a single-chunk iterator
                import json

                response_text = result.get("answer", "")
                # If there are other fields (sources, jira_issues, etc.), append them as JSON
                if any(
                    k in result
                    for k in [
                        "sources",
                        "project_plan",
                        "jira_issues",
                        "created_jira_issues",
                        "suggested_actions",
                    ]
                ):
                    response_text += "\n" + json.dumps(
                        {
                            k: v
                            for k, v in result.items()
                            if k
                            in [
                                "sources",
                                "project_plan",
                                "jira_issues",
                                "created_jira_issues",
                                "suggested_actions",
                                "duration",
                            ]
                        }
                    )
                # Ensure duration is in the result object for logging/tracking
                result["duration"] = time.perf_counter() - start

                return iter([response_text])

            # V2: Streaming reale via Orchestrator
            return self.agent.handle_user_message_stream(req)
        except Exception:
            CHAT_REQUEST_ERRORS_TOTAL.labels(route="stream", reason="exception").inc()
            CHAT_REQUEST_LATENCY_SECONDS.labels(route="stream").observe(
                time.perf_counter() - start
            )
            logger.exception("Chat stream failed")
            # Fallback simple
            return iter(["❌ Errore interno dell'agente."])

    async def handle_chat_async(self, req: ChatRequest) -> Dict[str, Any]:
        loop = asyncio.get_running_loop()
        ctx = contextvars.copy_context()
        return await loop.run_in_executor(
            self._executor, lambda: ctx.run(self.handle_chat, req)
        )

    async def handle_chat_stream_async(self, req: ChatRequest) -> AsyncIterator[str]:
        loop = asyncio.get_running_loop()
        ctx = contextvars.copy_context()

        # Generator creation runs under caller context so tenant ContextVar is captured.
        iterator = ctx.run(self.handle_chat_stream, req)

        async def _async_generator() -> AsyncIterator[str]:
            while True:
                chunk = await loop.run_in_executor(
                    self._executor, lambda: ctx.run(_next_stream_chunk, iterator)
                )
                if chunk is _STREAM_EOF:
                    break
                yield chunk  # type: ignore[misc]

        return _async_generator()


_chat_service: Optional[ChatService] = None


def get_chat_service() -> ChatService:
    global _chat_service
    if _chat_service is None:
        _chat_service = ChatService()
    return _chat_service


def __getattr__(name: str):
    if name == "chat_service":
        return get_chat_service()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


if TYPE_CHECKING:
    chat_service: ChatService


__all__ = ["ChatService", "chat_service", "get_chat_service"]
