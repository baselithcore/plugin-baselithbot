from __future__ import annotations

import logging
import time
from collections import Counter
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Optional

from agent_jira.kb_labels import build_kb_label
from agent_jira.metrics import AGENT_FAILURE_TOTAL, AGENT_STEP_LATENCY_SECONDS
from agent_jira.project_manager.story_count import parse_requested_story_count

from .events import ErrorEvent, FinalPayloadEvent, StatusEvent, TokenEvent, format_event

# Backward compatibility: import handlers
from .handlers import GlobalAnalysisStreamHandler, SystemStreamHandler

if TYPE_CHECKING:
    from agent_jira.agents.jira_agent import JiraAgent
    from agent_jira.agents.rag_agent import RAGAgent
    from agent_jira.chat.service import ChatService

logger = logging.getLogger(__name__)

__all__ = [
    "RAGStreamHandler",
    "JiraStreamHandler",
    "SystemStreamHandler",
    "GlobalAnalysisStreamHandler",
]


class RAGStreamHandler:
    """Handles streaming RAG flow with formalized events."""

    def __init__(
        self,
        service: ChatService,
        rag_agent: RAGAgent,
        generator_agent: Optional[Any] = None,
    ) -> None:
        self.service = service
        self.rag_agent = rag_agent
        self.generator_agent = generator_agent

    def handle(
        self,
        query: str,
        history_text: str,
        history_turns: List[Any],
        kb_label: Optional[str] = None,
    ) -> Generator[str, None, None]:
        t_total = time.perf_counter()
        logger.info("Starting RAG flow (Stream).")
        full_answer = []

        if not self.generator_agent:
            yield format_event(ErrorEvent(message="GeneratorAgent missing."))
            return

        yield format_event(
            StatusEvent(
                message="Ricerca documenti in corso...",
                step="retrieval",
                agent="rag",
            )
        )

        try:
            # 1. Retrieval
            t0 = time.perf_counter()
            retrieval_result = self.rag_agent.retrieve_context(
                query,
                history=history_text,
                history_turns=history_turns,
                kb_label=kb_label,
            )
            AGENT_STEP_LATENCY_SECONDS.labels(
                step_name="retrieval", agent_type="rag"
            ).observe(time.perf_counter() - t0)

            context = retrieval_result.get("context", "")
            sources = retrieval_result.get("sources", [])
            jira_issues = retrieval_result.get("jira_issues", [])

            yield format_event(
                StatusEvent(
                    message="Generazione risposta...",
                    step="synthesis",
                    agent="rag",
                )
            )

            # 2. Streaming Synthesis
            t1 = time.perf_counter()
            generator = self.generator_agent.synthesize_stream(
                query=query, context=context, history=history_text
            )
            for chunk in generator:
                full_answer.append(chunk)
                yield format_event(TokenEvent(text=chunk))

            AGENT_STEP_LATENCY_SECONDS.labels(
                step_name="synthesis", agent_type="rag"
            ).observe(time.perf_counter() - t1)

            # 3. Final Payload
            yield format_event(
                FinalPayloadEvent(
                    answer="".join(full_answer),
                    sources=sources,
                    jira_issues=jira_issues,
                    duration=time.perf_counter() - t_total,
                )
            )

        except Exception as e:
            AGENT_FAILURE_TOTAL.labels(
                agent_type="rag", failure_type=type(e).__name__
            ).inc()
            logger.error(f"RAG Stream failed: {e}", exc_info=True)
            yield format_event(
                ErrorEvent(message=f"Errore durante la generazione: {str(e)}")
            )


class JiraStreamHandler:
    """Handles streaming Jira flow with formalized events."""

    def __init__(
        self,
        service: ChatService,
        rag_agent: RAGAgent,
        jira_agent: JiraAgent,
        generator_agent: Optional[Any] = None,
    ) -> None:
        self.service = service
        self.rag_agent = rag_agent
        self.jira_agent = jira_agent
        self.generator_agent = generator_agent

    def handle(
        self,
        query: str,
        history_text: str,
        history_turns: List[Any],
        kb_label: Optional[str] = None,
    ) -> Generator[str, None, None]:
        t_total = time.perf_counter()
        logger.info("Starting Jira flow (Stream).")

        yield format_event(
            StatusEvent(
                message="Analisi richiesta e recupero contesto...",
                step="classification",
                agent="jira",
            )
        )

        try:
            # 0. Check Project Context
            project_key = self.jira_agent.detect_project_context(query, history="")
            if not project_key:
                yield from self._handle_missing_project(query, history_turns)
                return

            yield format_event(
                StatusEvent(
                    message=f"Progetto identificato: {project_key}",
                    step="context",
                    agent="jira",
                )
            )

            # 1. Retrieve Context
            t0 = time.perf_counter()
            rag_result = self.rag_agent.retrieve_context(
                query,
                history=history_text,
                history_turns=history_turns,
                kb_label=kb_label,
            )
            AGENT_STEP_LATENCY_SECONDS.labels(
                step_name="retrieval", agent_type="jira"
            ).observe(time.perf_counter() - t0)

            sources = rag_result.get("sources", [])

            yield format_event(
                StatusEvent(
                    message="Generazione piano di progetto...",
                    step="planning",
                    agent="jira",
                )
            )

            context_text = self._build_context_from_rag(rag_result)
            max_stories = self._parse_story_count(query)

            # 2. Generate Backlog
            t1 = time.perf_counter()
            backlog = self.jira_agent.generate_backlog(
                context=context_text,
                goal=query,
                history=history_text,
                jira_project_key=project_key,
                max_stories=max_stories,
            )
            AGENT_STEP_LATENCY_SECONDS.labels(
                step_name="planning", agent_type="jira"
            ).observe(time.perf_counter() - t1)

            yield format_event(
                StatusEvent(
                    message="Sincronizzazione con Jira in corso...",
                    step="sync",
                    agent="jira",
                )
            )

            # 3. Sync to Jira
            t2 = time.perf_counter()
            kb_label = self._infer_kb_label(sources, kb_label)
            jira_results = self.jira_agent.sync_backlog_to_jira(
                backlog, doc_sources=sources, kb_label=kb_label, project_key=project_key
            )
            AGENT_STEP_LATENCY_SECONDS.labels(
                step_name="jira_sync", agent_type="jira"
            ).observe(time.perf_counter() - t2)

            # 4. Final Response
            answer = self._build_jira_response(jira_results)
            final_jira_list = self._collect_jira_issues(
                rag_result, jira_results, history_turns
            )

            yield format_event(
                FinalPayloadEvent(
                    answer=answer,
                    sources=sources,
                    project_plan=backlog,
                    jira_issues=final_jira_list,
                    created_jira_issues=[
                        issue
                        for issue in jira_results
                        if issue.get("key") or issue.get("error")
                    ],
                    duration=time.perf_counter() - t_total,
                )
            )

        except Exception as e:
            AGENT_FAILURE_TOTAL.labels(
                agent_type="jira", failure_type=type(e).__name__
            ).inc()
            logger.error(f"Jira Stream failed: {e}", exc_info=True)
            yield format_event(
                ErrorEvent(message=f"Errore durante l'operazione Jira: {str(e)}")
            )

    def _handle_missing_project(
        self, query: str, history_turns: List[Any]
    ) -> Generator[str, None, None]:
        projects = self.jira_agent.get_available_projects()
        suggested_actions = [
            {
                "label": f"{p.get('name')} ({p.get('key')})",
                "payload": f"{query} per il progetto {p.get('key')}",
            }
            for p in projects
        ]

        answer = "⚠️ Progetto non specificato. Scegli uno dei progetti disponibili o specificalo nella richiesta."
        yield format_event(
            StatusEvent(
                message="In attesa del progetto Jira per continuare la creazione.",
                step="context",
                agent="jira",
            )
        )
        yield format_event(
            FinalPayloadEvent(
                answer=answer,
                suggested_actions=suggested_actions,
                created_jira_issues=[],
            )
        )

    def _build_context_from_rag(self, rag_result: Dict[str, Any]) -> str:
        chunks = rag_result.get("used_chunks", [])
        context_parts = [
            (getattr(c, "payload", {}) or {}).get("text", "") for c in chunks
        ]
        reconstructed = "\n\n".join(filter(None, context_parts))
        return (
            rag_result.get("context", "")
            or reconstructed
            or rag_result.get("answer", "")
        )

    def _parse_story_count(self, query: str) -> int:
        return parse_requested_story_count(query, default=3) or 3

    def _infer_kb_label(
        self, sources: List[Dict[str, Any]], kb_label: Optional[str]
    ) -> Optional[str]:
        weights = Counter()
        for src in sources:
            path_str = src.get("path") or src.get("relative_path")
            if path_str:
                try:
                    lbl = build_kb_label(Path(path_str))
                    if lbl:
                        weights[lbl] += src.get("chunks_used", 1)
                except Exception:
                    pass
        return weights.most_common(1)[0][0] if weights else kb_label

    def _build_jira_response(self, jira_results: List[Dict[str, Any]]) -> str:
        created = len([r for r in jira_results if not r.get("error")])
        failed = len(jira_results) - created
        ans = "Backlog creato con successo." if created > 0 else "Nessun ticket creato."
        if created > 0:
            ans += f" ✅ {created} ticket creati."
        if failed > 0:
            ans += f" ⚠️ {failed} falliti."
        created_refs = []
        for issue in jira_results:
            key = issue.get("key")
            if not key or issue.get("error"):
                continue
            summary = issue.get("summary") or "Senza titolo"
            url = issue.get("url")
            if url:
                created_refs.append(f"- [{key}]({url}) - {summary}")
            else:
                created_refs.append(f"- {key} - {summary}")
        if created_refs:
            ans += "\n\nRiferimenti Jira creati:\n" + "\n".join(created_refs)
        return ans

    def _collect_jira_issues(
        self,
        rag_result: Dict[str, Any],
        jira_results: List[Dict[str, Any]],
        history_turns: List[Any],
    ) -> List[Dict[str, Any]]:
        issues = []
        seen = set()
        # From RAG
        for issue in rag_result.get("jira_issues", []):
            if issue.get("key") and issue["key"] not in seen:
                issues.append(issue)
                seen.add(issue["key"])
        # From History
        for turn in history_turns:
            for old in turn.get("jira_issues", []):
                if old.get("key") and old["key"] not in seen:
                    issues.append(old)
                    seen.add(old["key"])
        # New
        for issue in jira_results:
            if issue.get("key") and issue["key"] not in seen:
                issues.append(issue)
                seen.add(issue["key"])
        return issues
