from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import TYPE_CHECKING, List

from agent_jira.agents.graph_agent import GraphAgent
from agent_jira.chat.agent_state import AgentState
from agent_jira.graphdb import graph_db
from agent_jira.integrations.jira import JiraIssueResult
from agent_jira.integrations.jira.tenant_resolver import get_tenant_jira_client
from agent_jira.kb_labels import (
    build_document_label_candidates,
    build_kb_label,
    is_supported_document_label,
)
from agent_jira.telemetry import telemetry
from agent_jira.config import PROJECT_PLANNER_ENABLE_TEST_CASES

if TYPE_CHECKING:
    from agent_jira.chat.service import ChatService


logger = logging.getLogger(__name__)


class BacklogPlanner:
    """Generate project plans and sync them with Jira when available."""

    def __init__(self, service: "ChatService") -> None:
        self.service = service

    def plan_backlog(self, state: AgentState) -> None:
        if state.rag_only:
            state.log("planner:skipped_rag_only")
            state.project_plan = None
            state.jira_requires_manual_approval = False
            state.next_action = "generate_answer"
            return

        planner = getattr(self.service, "project_planner", None)
        if planner is None:
            state.log("planner:disabled")
            state.project_plan = None
            state.next_action = "sync_with_jira"
            return

        try:
            plan = planner.generate_plan(
                query=state.user_query,
                context=state.context,
                history_text=state.history_text,
            )
        except Exception:
            telemetry.increment("planner.error")
            state.log("planner:error")
            state.project_plan = None
        else:
            telemetry.increment("planner.generated")
            state.project_plan = plan

            # --- Duplicate Detection ---
            if graph_db.is_enabled():
                try:
                    ga = GraphAgent(graph_db)
                    for story in plan.user_stories:
                        # Find similar stories
                        similar = ga.find_similar_stories(
                            story.title, threshold=0.80, limit=3
                        )
                        if similar:
                            state.log(f"planner:duplicate_detected:{story.title[:30]}")
                            warning_lines = [
                                "\n\n> [!WARNING] Possible Duplicate",
                                "> This story appears similar to existing stories:",
                            ]
                            for s in similar:
                                warning_lines.append(
                                    f"> - **{s['summary']}** ({s['status']}) - Score: {s['score']:.2f}"
                                )

                            # Update story description with warning
                            current_desc = story.description
                            story._description = (
                                current_desc + "\n" + "\n".join(warning_lines)
                            )
                except Exception as e:
                    logger.warning(f"Duplicate detection failed: {e}", exc_info=True)
            # ---------------------------

        tenant_jira_client = get_tenant_jira_client(
            fallback_client=getattr(self.service, "jira_client", None)
        )
        jira_ready = bool(tenant_jira_client and tenant_jira_client.is_ready())
        state.jira_requires_manual_approval = bool(
            getattr(self.service, "jira_manual_approval", False)
            and jira_ready
            and state.project_plan
            and list(getattr(state.project_plan, "user_stories", ()))
        )

        state.next_action = "sync_with_jira"

    def sync_with_jira(self, state: AgentState) -> None:
        if state.rag_only:
            state.next_action = "generate_answer"
            return

        project_plan = state.project_plan
        state.jira_results = []
        if project_plan is None or not list(getattr(project_plan, "user_stories", ())):
            state.next_action = "generate_answer"
            return

        if state.jira_requires_manual_approval:
            state.log("jira:manual_required")
            state.next_action = "generate_answer"
            return

        jira_client = get_tenant_jira_client(
            fallback_client=getattr(self.service, "jira_client", None)
        )
        if jira_client is None or not jira_client.is_ready():
            state.log("jira:disabled")
            state.next_action = "generate_answer"
            return

        graph_agent = None
        if graph_db.is_enabled():
            graph_agent = GraphAgent(graph_db)

        source_docs = [
            src for src in (state.doc_sources or []) if isinstance(src, dict)
        ]
        if not source_docs and state.history_turns:
            logger.info("DEBUG: source_docs empty, checking history...")
            for turn in reversed(state.history_turns):
                meta = getattr(turn, "metadata", {})
                if not meta and isinstance(turn, dict):
                    meta = turn.get("metadata", {})

                hist_sources = meta.get("sources")
                if hist_sources and isinstance(hist_sources, list):
                    source_docs = [s for s in hist_sources if isinstance(s, dict)]
                    if source_docs:
                        logger.info(
                            "DEBUG: Recovered %d sources from history metadata.",
                            len(source_docs),
                        )
                        break

        if not source_docs and state.history_text:
            logger.info("DEBUG: source_docs still empty, scanning history text...")
            pattern = r"[\w\-\.]+\.(?:pdf|docx|txt|md|csv|json)"
            matches = re.findall(pattern, state.history_text, re.IGNORECASE)
            for fname in set(matches):
                logger.info("DEBUG: Found candidate file in text: %s", fname)
                source_docs.append({"document_id": None, "path": fname})

        doc_context_label = None
        for src in source_docs:
            doc_path = src.get("path") or src.get("relative_path")
            if doc_path:
                try:
                    doc_context_label = build_kb_label(Path(doc_path))
                    break
                except Exception:
                    pass
            doc_id = str(src.get("document_id") or "").strip()
            if doc_id and is_supported_document_label(doc_id):
                doc_context_label = doc_id
                break

        jira_results: List[JiraIssueResult] = []
        for story in project_plan.user_stories:
            try:
                story_labels = list(
                    dict.fromkeys(
                        [
                            *(getattr(story, "labels", []) or []),
                            *([doc_context_label] if doc_context_label else []),
                        ]
                    )
                )
                story.labels = story_labels
                result = jira_client.create_user_story(
                    title=story.title,
                    description=story.description,
                    acceptance_criteria=story.acceptance_criteria,
                    business_value=getattr(story, "business_value", [])
                    or [story.benefit],
                    priority=story.priority or "Medium",
                    story_points=story.story_points,
                    labels=story_labels,
                    test_cases=(
                        story.test_cases if PROJECT_PLANNER_ENABLE_TEST_CASES else None
                    ),
                    project_key=getattr(story, "jira_project_key", None),
                )
                story.jira_issue_key = result.key
                telemetry.increment("jira.story_created")

                if graph_agent and result.key:
                    try:
                        # 1. Upsert Story
                        s_props = {
                            "role": story.role,
                            "goal": story.goal,
                            "benefit": story.benefit,
                            "priority": story.priority,
                            "labels": story_labels,
                            "acceptance_criteria": story.acceptance_criteria,
                        }
                        s_props = {k: v for k, v in s_props.items() if v}

                        graph_agent.upsert_story(
                            story_id=result.key,
                            summary=story.title,
                            status=result.status or "To Do",
                            points=story.story_points,
                            properties=s_props,
                        )

                        # 2. Link to Source Documents
                        logger.info(
                            f"DEBUG: sync_with_jira final source_docs count: {len(source_docs)}"
                        )
                        logger.info(
                            f"DEBUG: sync_with_jira final sources: {str(source_docs)}"
                        )

                        for src in source_docs[:3]:
                            doc_id = src.get("document_id")
                            doc_path = src.get("path")
                            logger.info(
                                f"DEBUG: Processing source - ID: {doc_id}, Path: {doc_path}"
                            )

                            ids_to_link = set()
                            if doc_id:
                                ids_to_link.add(str(doc_id))

                            if doc_path:
                                try:
                                    derived_ids = build_document_label_candidates(
                                        Path(doc_path)
                                    )
                                    ids_to_link.update(derived_ids)
                                    logger.info("DEBUG: Derived IDs: %s", derived_ids)
                                except Exception as e:
                                    logger.error(f"DEBUG: Error deriving ID: {e}")

                            logger.info(
                                f"DEBUG: Linking story {result.key} to IDs: {ids_to_link}"
                            )
                            for link_id in ids_to_link:
                                graph_agent.link_story_to_doc(result.key, link_id)

                        # 3. Handle Test Cases (if enabled and present)
                        test_cases_to_process = []
                        if story.test_cases:
                            test_cases_to_process.extend(story.test_cases)
                        elif hasattr(story, "scenarios") and story.scenarios:
                            test_cases_to_process.extend(story.scenarios)

                        if PROJECT_PLANNER_ENABLE_TEST_CASES and test_cases_to_process:
                            for tc in test_cases_to_process:
                                try:
                                    tc_title = getattr(tc, "title", "Test Case")
                                    tc_given = getattr(tc, "given", []) or []
                                    tc_when = getattr(tc, "when", []) or []
                                    tc_then = getattr(tc, "then", []) or []
                                    tc_prio = getattr(tc, "priority", story.priority)

                                    # Fallback for traditional TestCase
                                    if (
                                        not tc_when
                                        and hasattr(tc, "steps")
                                        and tc.steps
                                    ):
                                        tc_when = tc.steps
                                    if (
                                        not tc_then
                                        and hasattr(tc, "expected_result")
                                        and tc.expected_result
                                    ):
                                        tc_then = [tc.expected_result]

                                    tc_res = jira_client.create_test_case(
                                        story_key=result.key,
                                        scenario_title=tc_title,
                                        scenario_id=getattr(tc, "scenario_id", None)
                                        or getattr(tc, "id", None),
                                        given=tc_given,
                                        when=tc_when,
                                        then=tc_then,
                                        labels=story_labels,
                                        priority=tc_prio,
                                        project_key=getattr(
                                            story, "jira_project_key", None
                                        ),
                                    )

                                    if tc_res.key:
                                        # Upsert Test Case Node
                                        tc_props = {
                                            "priority": tc_prio,
                                            "given": tc_given,
                                            "when": tc_when,
                                            "then": tc_then,
                                            "labels": story_labels,
                                        }
                                        tc_props = {
                                            k: v for k, v in tc_props.items() if v
                                        }

                                        graph_agent.upsert_test_case(
                                            test_id=tc_res.key,
                                            test_type="Manual",
                                            summary=tc_title,
                                            properties=tc_props,
                                        )
                                        # Link Test -> Story
                                        graph_agent.link_test_to_story(
                                            tc_res.key, result.key
                                        )
                                except Exception as tc_exc:
                                    logger.warning(
                                        "Failed to create/link test case: %s", tc_exc
                                    )

                    except Exception:  # pragma: no cover
                        logger.warning("graph_agent update failed", exc_info=True)
            except Exception as exc:
                telemetry.increment("jira.story_failed")
                result = JiraIssueResult(
                    summary=story.title,
                    key=None,
                    url=None,
                    status=None,
                    issue_type=getattr(jira_client, "issue_type", None),
                    error=str(exc),
                )
            jira_results.append(result)

        state.jira_results = jira_results
        state.next_action = "generate_answer"


__all__ = ["BacklogPlanner"]
