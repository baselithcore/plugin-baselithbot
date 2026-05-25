import concurrent.futures
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from agent_jira.integrations.jira import JiraIssueResult
from agent_jira.kb_labels import build_document_label_candidates
from agent_jira.project_manager import ProjectPlan
from agent_jira.telemetry import telemetry
from agent_jira.config import PROJECT_PLANNER_ENABLE_TEST_CASES

logger = logging.getLogger(__name__)


def _process_single_story(
    story, jira_client, project_key, kb_label
) -> tuple[dict, dict | None]:
    """
    Creates the Jira ticket only. Returns result + graph data payload.
    """
    graph_payload = {
        "story": None,
        "test_cases": [],
        "story_doc_links": [],
        "test_story_links": [],
    }

    try:
        # Use story-level key if present, otherwise fallback to agent-level key
        effective_key = getattr(story, "jira_project_key", None) or project_key
        story_labels = list(
            dict.fromkeys(
                [
                    *(getattr(story, "labels", []) or []),
                    *([kb_label] if kb_label else []),
                ]
            )
        )
        story.labels = story_labels

        result = jira_client.create_user_story(
            title=story.title,
            description=story.description,
            acceptance_criteria=story.acceptance_criteria,
            business_value=getattr(story, "business_value", []) or [story.benefit],
            priority=story.priority or "Medium",
            story_points=story.story_points,
            labels=story_labels,
            test_cases=(
                story.test_cases if PROJECT_PLANNER_ENABLE_TEST_CASES else None
            ),
            project_key=effective_key,
        )
        story.jira_issue_key = result.key
        telemetry.increment("jira.story_created")
        logger.debug("JiraAgent.sync: story created. Key: %s", result.key)

        # Prepare GraphDB Payload (In-Memory)
        story_props = {
            "role": story.role,
            "goal": story.goal,
            "benefit": story.benefit,
            "priority": story.priority,
            "jira_project": story.jira_project_key,
            "labels": story_labels,
            "business_value": getattr(story, "business_value", None),
            "jira_url": result.url,
        }
        # Remove empty
        story_props = {k: v for k, v in story_props.items() if v}

        graph_payload["story"] = {
            "id": result.key,
            "summary": story.title,
            "status": result.status or "To Do",
            "points": story.story_points,
            "properties": story_props,
        }

        # 2. Test Cases and Links
        test_cases_to_process = []
        if story.test_cases:
            test_cases_to_process.extend(story.test_cases)
        elif hasattr(story, "scenarios") and story.scenarios:
            # Fallback to BDD scenarios if traditional test cases are missing
            test_cases_to_process.extend(story.scenarios)

        if test_cases_to_process:
            for idx, tc in enumerate(test_cases_to_process, 1):
                tc_id = None
                try:
                    tc_title = getattr(tc, "title", "Test Case")
                    tc_given = getattr(tc, "given", []) or []
                    tc_when = getattr(tc, "when", []) or []
                    tc_then = getattr(tc, "then", []) or []
                    tc_prio = getattr(tc, "priority", story.priority)

                    # If it's a traditional TestCase with steps/expected but no Gherkin
                    if not tc_when and hasattr(tc, "steps") and tc.steps:
                        tc_when = tc.steps
                    if (
                        not tc_then
                        and hasattr(tc, "expected_result")
                        and tc.expected_result
                    ):
                        tc_then = [tc.expected_result]

                    if PROJECT_PLANNER_ENABLE_TEST_CASES:
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
                            project_key=effective_key,
                        )
                        if tc_res.key:
                            tc_id = tc_res.key
                except Exception as tc_exc:
                    logger.warning(
                        "Failed to create Jira test case for story %s: %s",
                        result.key,
                        tc_exc,
                    )

                if not tc_id:
                    # Keep test coverage in the graph even when Jira testcase creation is disabled
                    # or when the Jira call fails.
                    tc_id = f"{result.key}-TC-{idx}"

                tc_props = {
                    "priority": tc_prio,
                    "given": tc_given,
                    "when": tc_when,
                    "then": tc_then,
                    "labels": story_labels,
                }
                tc_props = {k: v for k, v in tc_props.items() if v}

                graph_payload["test_cases"].append(
                    {
                        "id": tc_id,
                        "type": "Manual",
                        "summary": tc_title,
                        "properties": tc_props,
                    }
                )
                graph_payload["test_story_links"].append(
                    {"test_id": tc_id, "story_id": result.key}
                )

        return result.to_dict(), graph_payload

    except Exception as exc:
        telemetry.increment("jira.story_failed")
        logger.error(
            "JiraAgent.sync: story creation failed for '%s'",
            story.title,
            exc_info=True,
        )
        err_res = JiraIssueResult(
            summary=story.title,
            key=None,
            url=None,
            status=None,
            issue_type=getattr(jira_client, "issue_type", None),
            error=str(exc),
        )
        return err_res.to_dict(), None


def sync_backlog_to_jira(
    backlog: Dict[str, Any],
    jira_client,
    graph_agent=None,
    doc_sources: Optional[List[Dict[str, Any]]] = None,
    kb_label: Optional[str] = None,
    project_key: Optional[str] = None,
    create_intelligent_relationships_callback=None,
) -> List[Dict[str, Any]]:
    """
    Sincronizza il backlog su Jira e GraphDB.
    """
    try:
        plan = ProjectPlan.from_payload(backlog)
    except Exception as exc:
        logger.error("JiraAgent.sync: invalid backlog payload.", exc_info=True)
        return [{"error": f"Invalid backlog payload: {exc}"}]

    if not plan.user_stories:
        return []

    logger.info(
        "JiraAgent.sync: syncing %d stories (parallel).", len(plan.user_stories)
    )

    results = []
    batch_stories = []
    batch_tests = []
    batch_story_doc_links = []
    batch_test_story_links = []

    max_workers = 5
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_story = {
            executor.submit(
                _process_single_story, story, jira_client, project_key, kb_label
            ): story
            for story in plan.user_stories
        }
        for future in concurrent.futures.as_completed(future_to_story):
            try:
                res_dict, g_payload = future.result()
                results.append(res_dict)

                if g_payload:
                    if g_payload["story"]:
                        batch_stories.append(g_payload["story"])
                        if doc_sources:
                            for src in doc_sources:
                                candidates_ids = set()
                                doc_id = src.get("document_id")
                                if doc_id:
                                    candidates_ids.add(str(doc_id))
                                doc_path = src.get("path") or src.get("relative_path")
                                if doc_path:
                                    try:
                                        candidates_ids.update(
                                            build_document_label_candidates(
                                                Path(doc_path)
                                            )
                                        )
                                    except Exception as e:
                                        logger.error(
                                            f"Failed to derive IDs from path '{doc_path}': {e}"
                                        )
                                for link_id in candidates_ids:
                                    batch_story_doc_links.append(
                                        {
                                            "story_id": g_payload["story"]["id"],
                                            "doc_id": link_id,
                                        }
                                    )
                    if g_payload["test_cases"]:
                        batch_tests.extend(g_payload["test_cases"])
                    if g_payload["test_story_links"]:
                        batch_test_story_links.extend(g_payload["test_story_links"])
            except Exception:
                logger.error(
                    "JiraAgent.sync: concurrent execution error", exc_info=True
                )

    if graph_agent and batch_stories:
        logger.info("JiraAgent.sync: performing batch Graph updates.")
        try:
            graph_agent.upsert_stories_batch(batch_stories)
            if batch_tests:
                graph_agent.upsert_test_cases_batch(batch_tests)
            if batch_story_doc_links:
                graph_agent.link_stories_docs_batch(batch_story_doc_links)
            if batch_test_story_links:
                graph_agent.link_tests_stories_batch(batch_test_story_links)

            if create_intelligent_relationships_callback:
                create_intelligent_relationships_callback(plan.user_stories)
        except Exception:
            logger.error("JiraAgent.sync: batch graph sync failed", exc_info=True)

    return results
