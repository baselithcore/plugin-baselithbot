from __future__ import annotations

from typing import Any, Dict, List, Mapping, Sequence

from fastapi import HTTPException, Query, status

from agent_jira.agents.graph_agent import GraphAgent
from agent_jira.graphdb import graph_db
from agent_jira.project_manager import Scenario, UserStory
from agent_jira.ui.jira import coerce_project_plan
from agent_jira.config import JIRA_PROJECT_KEY, PROJECT_PLANNER_ENABLE_TEST_CASES

from . import router


def _get_jira_client():
    import importlib

    from agent_jira.integrations.jira.tenant_resolver import get_tenant_jira_client

    ui_services = importlib.import_module("app.ui.services")
    global_client = getattr(ui_services.get_chat_service(), "jira_client", None)

    # Prova il client tenant-specific, poi fallback al globale
    client = get_tenant_jira_client(fallback_client=global_client)
    if client is None or not client.is_ready():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Integrazione Jira non configurata o disabilitata.",
        )
    return client


@router.get("/jira/projects")
def jira_projects() -> Dict[str, object]:
    client = _get_jira_client()
    try:
        projects = client.list_projects()
    except Exception as exc:  # pragma: no cover - dipende da Jira
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    # Resolve default & allowed from tenant settings (fallback to env)
    default_pk = JIRA_PROJECT_KEY
    allowed_pks: list[str] = [JIRA_PROJECT_KEY] if JIRA_PROJECT_KEY else []
    try:
        from agent_jira.routers.console.jira_settings import _get_tenant_jira_settings
        from agent_jira.tenant_context import get_current_tenant_id as _tid

        tid = _tid()
        if tid:
            ts = _get_tenant_jira_settings(tid)
            if ts:
                default_pk = (
                    ts.get("default_project_key") or ts.get("project_key") or default_pk
                )
                allowed_pks = ts.get("allowed_project_keys") or allowed_pks
    except Exception:
        pass

    return {
        "projects": projects,
        "default_project_key": default_pk,
        "allowed_project_keys": allowed_pks,
    }


@router.get("/jira/search")
def jira_search_by_label(label: List[str] = Query(...)) -> Dict[str, object]:
    """
    Cerca issue Jira per label.
    """
    from agent_jira.ui.jira import get_jira_results_for_label

    labels = list(
        dict.fromkeys(
            item.strip() for item in label if isinstance(item, str) and item.strip()
        )
    )
    if not labels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Label richiesta."
        )

    try:
        results: List[Dict[str, Any]] = []
        seen_keys: set[str] = set()
        for current_label in labels:
            for item in get_jira_results_for_label(current_label, limit=50):
                issue_key = str(item.get("key") or item.get("summary") or "").strip()
                if not issue_key or issue_key in seen_keys:
                    continue
                seen_keys.add(issue_key)
                results.append(item)
        return {"status": "ok", "results": results}
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail=str(exc)
        ) from exc


@router.post("/jira/sync")
def sync_jira(payload: Dict[str, Any]) -> Dict[str, object]:
    client = _get_jira_client()
    graph_agent = GraphAgent(graph_db)
    story_payload = payload.get("story")
    story_index = payload.get("story_index")
    plan = payload.get("plan")
    kb_payload = payload.get("kb") or {}
    metadata = payload.get("metadata") or {}
    kb_label_override = (
        payload.get("kb_label") or kb_payload.get("label") or metadata.get("kb_label")
    )
    category_label_override = payload.get("category") or metadata.get("category")
    # Fallback per retro-compatibilità solo se non specificato
    if kb_label_override and not category_label_override:
        category_label_override = "knowledge-base"

    if story_payload:
        if not isinstance(story_payload, Mapping):
            raise HTTPException(
                status_code=400, detail="Payload user story non valido."
            )
        try:
            stories = [UserStory.from_payload(story_payload)]
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    else:
        if not plan:
            raise HTTPException(
                status_code=400,
                detail="Nessun project plan disponibile per la sincronizzazione.",
            )
        try:
            plan_obj = coerce_project_plan(plan)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        stories = list(plan_obj.user_stories)

        if story_index is not None:
            try:
                idx = int(str(story_index))
            except (TypeError, ValueError) as exc:
                raise HTTPException(
                    status_code=400, detail="Indice user story non valido."
                ) from exc

            if idx < 0 or idx >= len(stories):
                raise HTTPException(
                    status_code=404,
                    detail="User story non trovata nel project plan.",
                )
            stories = [stories[idx]]

    results: List[Dict[str, Any]] = []
    errors = False
    for story in stories:
        try:
            if kb_label_override:
                labels = list(getattr(story, "labels", []) or [])
                labels = [
                    lbl
                    for lbl in labels
                    if not (
                        isinstance(lbl, str)
                        and lbl.lower().startswith(("analysis", "analysis-"))
                    )
                ]
                labels.append(kb_label_override)
                if category_label_override:
                    labels.append(category_label_override)
                story.labels = list(dict.fromkeys(label for label in labels if label))

            description_for_jira = (
                f"Come {story.role} voglio {story.goal} cosi da {story.benefit}."
            )
            result = client.create_user_story(
                title=story.title,
                description=description_for_jira,
                acceptance_criteria=story.acceptance_criteria,
                business_value=getattr(story, "business_value", []) or [story.benefit],
                priority=story.priority or "Medium",
                story_points=story.story_points,
                labels=story.labels,
                test_cases=story.test_cases
                if PROJECT_PLANNER_ENABLE_TEST_CASES
                else None,
                project_key=story.jira_project_key or None,
            )
            # Graph Update
            try:
                if result.key:
                    # Enrich properties
                    s_props = {
                        "role": story.role,
                        "goal": story.goal,
                        "benefit": story.benefit,
                        "priority": story.priority,
                        "labels": story.labels,
                    }
                    s_props = {k: v for k, v in s_props.items() if v}

                    graph_agent.upsert_story(
                        story_id=result.key,
                        summary=story.title,
                        status="To Do",
                        points=story.story_points,
                        properties=s_props,
                    )
                    if kb_label_override and kb_label_override != "analysis":
                        graph_agent.link_story_to_doc(result.key, kb_label_override)
            except Exception:
                pass

            results.append(result.to_dict())
        except Exception as exc:  # pragma: no cover - dipende da Jira
            errors = True
            results.append(
                {
                    "summary": story.title,
                    "key": None,
                    "url": None,
                    "status": None,
                    "error": str(exc),
                }
            )

    status_value = "ok" if not errors else "partial"
    return {"status": status_value, "results": results}


@router.post("/jira/testcases")
def sync_jira_testcases(payload: Dict[str, Any]) -> Dict[str, object]:
    client = _get_jira_client()
    graph_agent = GraphAgent(graph_db)

    story_key = payload.get("story_key") or payload.get("storyKey")
    if not story_key or not isinstance(story_key, str):
        raise HTTPException(
            status_code=400, detail="Specificare la user story Jira (story_key)."
        )

    project_key = payload.get("project_key")
    if not project_key and "-" in story_key:
        project_key = story_key.split("-", 1)[0]
    issue_type_override = payload.get("issue_type")
    kb_label_override = payload.get("kb_label")
    category_label_override = payload.get("category")

    scenarios_payload = payload.get("scenarios") or []
    if not isinstance(scenarios_payload, Sequence):
        raise HTTPException(status_code=400, detail="Scenari BDD non validi.")

    errors = False
    results: List[Dict[str, Any]] = []
    for entry in scenarios_payload:
        if not isinstance(entry, Mapping):
            continue
        try:
            scenario = Scenario.from_payload(entry)
            result = client.create_test_case(
                story_key=story_key,
                scenario_title=scenario.title,
                scenario_id=scenario.scenario_id or None,
                given=scenario.given,
                when=scenario.when,
                then=scenario.then,
                labels=list(
                    filter(
                        None,
                        ["bdd-scenario", kb_label_override, category_label_override],
                    )
                ),
                priority=scenario.priority or "Medium",
                project_key=project_key,
                issue_type=issue_type_override,
            )
            # Graph Update
            try:
                if result.key:
                    # Enrich properties
                    tc_props = {
                        "priority": scenario.priority,
                        "given": scenario.given,
                        "when": scenario.when,
                        "then": scenario.then,
                        "labels": list(
                            filter(
                                None,
                                [kb_label_override, category_label_override],
                            )
                        ),
                    }
                    tc_props = {k: v for k, v in tc_props.items() if v}

                    graph_agent.upsert_test_case(
                        test_id=result.key,
                        test_type="Manual",
                        summary=scenario.title,
                        properties=tc_props,
                    )
                    if story_key:
                        graph_agent.link_test_to_story(result.key, story_key)
            except Exception:
                pass

            results.append(result.to_dict())
        except Exception as exc:  # pragma: no cover - dipende da Jira
            errors = True
            results.append(
                {
                    "summary": getattr(entry, "title", None) or "Test case",
                    "key": None,
                    "url": None,
                    "status": None,
                    "error": str(exc),
                }
            )

    status_value = "ok" if not errors else "partial"
    return {"status": status_value, "results": results}
