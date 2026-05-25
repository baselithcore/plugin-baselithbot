from __future__ import annotations

import logging
from dataclasses import dataclass, field, fields
from typing import Any, Callable, Mapping, Optional, Sequence

from sentence_transformers import CrossEncoder, SentenceTransformer

from agent_jira.cache import RedisTTLCache, TTLCache, create_redis_client
from agent_jira.chat.history import ChatHistoryManager
from agent_jira.integrations.jira import JiraClient
from agent_jira.nlp_models import get_embedder, get_reranker
from agent_jira.project_manager import ProjectPlanner
from agent_jira.tenant_context import get_tenant_cache_prefix
from agent_jira.test_case_generator import TestCaseGenerator
from agent_jira.config import (
    CACHE_BACKEND,
    CACHE_REDIS_PREFIX,
    CACHE_REDIS_URL,
    CHAT_MEMORY_ENABLED,
    CHAT_MEMORY_MAX_SESSIONS,
    CHAT_MEMORY_MAX_TURNS,
    CHAT_MEMORY_SUMMARY_ENABLED,
    CHAT_MEMORY_SUMMARY_MAX_CHARS,
    CHAT_MEMORY_SUMMARY_MAX_TURNS,
    CHAT_MEMORY_TTL,
    CHAT_RERANK_CACHE_ENABLED,
    CHAT_RERANK_CACHE_MAXSIZE,
    CHAT_RERANK_CACHE_TTL,
    CHAT_RESPONSE_CACHE_ENABLED,
    CHAT_RESPONSE_CACHE_MAXSIZE,
    CHAT_RESPONSE_CACHE_TTL,
    EMBEDDER_MODEL,
    ENABLE_JIRA_AUTOMATION,
    ENABLE_PROJECT_MANAGER_MODE,
    JIRA_API_TOKEN,
    JIRA_BASE_URL,
    JIRA_DEFAULT_LABELS,
    JIRA_DEFAULT_PRIORITY_NAME,
    JIRA_EMAIL,
    JIRA_ISSUE_TYPE,
    JIRA_KB_LABEL_FIELD,
    JIRA_PRIORITY_MAPPING,
    JIRA_PROJECT_KEY,
    JIRA_REQUEST_TIMEOUT,
    JIRA_STORY_POINTS_FIELD,
    JIRA_TESTCASE_ISSUE_TYPE,
    PROJECT_PLANNER_ENABLE_TEST_CASES,
    PROJECT_PLANNER_MAX_STORIES,
    PROJECT_PLANNER_MAX_TEST_CASES,
    PROJECT_PLANNER_MIN_SCENARIOS,
    RERANKER_MODEL,
)

logger = logging.getLogger(__name__)
_redis_client = None


@dataclass
class ChatDependencies:
    embedder: SentenceTransformer
    reranker: CrossEncoder
    response_cache: Optional[TTLCache]
    rerank_cache: Optional[TTLCache]
    history_manager: ChatHistoryManager
    newline: str
    double_newline: str
    section_separator: str
    project_planner: Optional[ProjectPlanner]
    jira_client: Optional[JiraClient]


def _get_redis_client():
    global _redis_client
    if _redis_client is None:
        _redis_client = create_redis_client(CACHE_REDIS_URL)
    return _redis_client


def _build_cache(maxsize: int, ttl: float, *, namespace: str) -> TTLCache:
    if CACHE_BACKEND == "redis":
        client = _get_redis_client()
        prefix = get_tenant_cache_prefix(f"{CACHE_REDIS_PREFIX}:{namespace}")
        return RedisTTLCache(client, prefix=prefix, default_ttl=ttl)
    return TTLCache(maxsize=maxsize, ttl=ttl)


@dataclass
class ChatDependencyConfig:
    embedder_model: str = EMBEDDER_MODEL
    reranker_model: str = RERANKER_MODEL
    response_cache_enabled: bool = CHAT_RESPONSE_CACHE_ENABLED
    response_cache_maxsize: int = CHAT_RESPONSE_CACHE_MAXSIZE
    response_cache_ttl: float = CHAT_RESPONSE_CACHE_TTL
    rerank_cache_enabled: bool = CHAT_RERANK_CACHE_ENABLED
    rerank_cache_maxsize: int = CHAT_RERANK_CACHE_MAXSIZE
    rerank_cache_ttl: float = CHAT_RERANK_CACHE_TTL
    history_enabled: bool = CHAT_MEMORY_ENABLED
    history_ttl: float = CHAT_MEMORY_TTL
    history_max_turns: int = CHAT_MEMORY_MAX_TURNS
    history_max_sessions: int = CHAT_MEMORY_MAX_SESSIONS
    summary_enabled: bool = CHAT_MEMORY_SUMMARY_ENABLED
    summary_max_turns: int = CHAT_MEMORY_SUMMARY_MAX_TURNS
    summary_max_chars: int = CHAT_MEMORY_SUMMARY_MAX_CHARS
    newline: str = "\n"
    double_newline: Optional[str] = None
    section_separator: Optional[str] = None
    project_planner_enabled: bool = ENABLE_PROJECT_MANAGER_MODE
    project_planner_include_test_cases: bool = PROJECT_PLANNER_ENABLE_TEST_CASES
    project_planner_max_stories: int = PROJECT_PLANNER_MAX_STORIES
    project_planner_max_test_cases: int = PROJECT_PLANNER_MAX_TEST_CASES
    project_planner_min_scenarios: int = PROJECT_PLANNER_MIN_SCENARIOS
    project_planner_factory: Optional[
        Callable[["ChatDependencyConfig"], Optional[ProjectPlanner]]
    ] = None
    test_case_generator_factory: Optional[
        Callable[["ChatDependencyConfig"], Optional[TestCaseGenerator]]
    ] = None
    jira_automation_enabled: bool = ENABLE_JIRA_AUTOMATION
    jira_base_url: Optional[str] = JIRA_BASE_URL
    jira_email: Optional[str] = JIRA_EMAIL
    jira_api_token: Optional[str] = JIRA_API_TOKEN
    jira_project_key: Optional[str] = JIRA_PROJECT_KEY
    jira_issue_type: str = JIRA_ISSUE_TYPE
    jira_testcase_issue_type: str = JIRA_TESTCASE_ISSUE_TYPE
    jira_default_labels: Sequence[str] = field(
        default_factory=lambda: list(JIRA_DEFAULT_LABELS)
    )
    jira_story_points_field: Optional[str] = JIRA_STORY_POINTS_FIELD
    jira_kb_label_field: Optional[str] = JIRA_KB_LABEL_FIELD
    jira_request_timeout: float = JIRA_REQUEST_TIMEOUT
    jira_default_priority_name: str = JIRA_DEFAULT_PRIORITY_NAME
    jira_priority_mapping: Mapping[str, str] = field(
        default_factory=lambda: dict(JIRA_PRIORITY_MAPPING)
    )
    jira_client_factory: Optional[
        Callable[["ChatDependencyConfig"], Optional[JiraClient]]
    ] = None
    embedder_factory: Optional[Callable[[str], Any]] = None
    reranker_factory: Optional[Callable[[str], Any]] = None
    response_cache_factory: Optional[Callable[[int, float], TTLCache]] = None
    rerank_cache_factory: Optional[Callable[[int, float], TTLCache]] = None
    history_cache_factory: Optional[Callable[[int, float], TTLCache]] = None
    history_manager_factory: Optional[
        Callable[[Optional[TTLCache], "ChatDependencyConfig"], ChatHistoryManager]
    ] = None

    @classmethod
    def from_mapping(cls, mapping: Mapping[str, Any]) -> "ChatDependencyConfig":
        allowed = {field.name for field in fields(cls)}
        filtered = {key: value for key, value in mapping.items() if key in allowed}
        return cls(**filtered)

    def copy_with_overrides(self, **overrides: Any) -> "ChatDependencyConfig":
        data = {field.name: getattr(self, field.name) for field in fields(self)}
        data.update({key: value for key, value in overrides.items() if key in data})
        return ChatDependencyConfig(**data)


def create_default_dependencies(
    config: Optional[ChatDependencyConfig] = None,
) -> ChatDependencies:
    cfg = config or ChatDependencyConfig()

    embedder_factory = cfg.embedder_factory or get_embedder
    embedder = embedder_factory(cfg.embedder_model)

    reranker_factory = cfg.reranker_factory or get_reranker
    reranker = reranker_factory(cfg.reranker_model)

    response_cache = None
    if cfg.response_cache_enabled:
        response_cache_factory = cfg.response_cache_factory or (
            lambda maxsize, ttl: _build_cache(maxsize, ttl, namespace="response")
        )
        response_cache = response_cache_factory(
            cfg.response_cache_maxsize, cfg.response_cache_ttl
        )

    rerank_cache = None
    if cfg.rerank_cache_enabled:
        rerank_cache_factory = cfg.rerank_cache_factory or (
            lambda maxsize, ttl: _build_cache(maxsize, ttl, namespace="rerank")
        )
        rerank_cache = rerank_cache_factory(
            cfg.rerank_cache_maxsize, cfg.rerank_cache_ttl
        )

    history_cache = None
    if cfg.history_enabled:
        history_cache_factory = cfg.history_cache_factory or (
            lambda maxsize, ttl: _build_cache(maxsize, ttl, namespace="history")
        )
        history_cache = history_cache_factory(cfg.history_max_sessions, cfg.history_ttl)

    if cfg.history_manager_factory is not None:
        history_manager = cfg.history_manager_factory(history_cache, cfg)
    else:
        history_manager = ChatHistoryManager(
            history_cache,
            max_turns=cfg.history_max_turns,
            summary_enabled=cfg.summary_enabled,
            summary_max_turns=cfg.summary_max_turns,
            summary_max_chars=cfg.summary_max_chars,
        )

    newline = cfg.newline
    double_newline = (
        cfg.double_newline if cfg.double_newline is not None else newline * 2
    )
    section_separator = (
        cfg.section_separator
        if cfg.section_separator is not None
        else f"{double_newline}---{double_newline}"
    )

    test_case_generator: Optional[TestCaseGenerator] = None
    if cfg.project_planner_include_test_cases:
        if cfg.test_case_generator_factory is not None:
            test_case_generator = cfg.test_case_generator_factory(cfg)
        else:
            test_case_generator = TestCaseGenerator(
                max_cases_per_story=cfg.project_planner_max_test_cases
            )

    if cfg.project_planner_factory is not None:
        project_planner = cfg.project_planner_factory(cfg)
    elif cfg.project_planner_enabled:
        project_planner = ProjectPlanner(
            max_user_stories=cfg.project_planner_max_stories,
            min_scenarios=cfg.project_planner_min_scenarios,
            include_test_cases=cfg.project_planner_include_test_cases,
            test_case_generator=test_case_generator,
        )
    else:
        project_planner = None

    jira_client: Optional[JiraClient]
    if cfg.jira_client_factory is not None:
        jira_client = cfg.jira_client_factory(cfg)
    elif (
        cfg.jira_automation_enabled
        and cfg.jira_base_url
        and cfg.jira_email
        and cfg.jira_api_token
        and cfg.jira_project_key
    ):
        jira_client = JiraClient(
            base_url=cfg.jira_base_url,
            email=cfg.jira_email,
            api_token=cfg.jira_api_token,
            project_key=cfg.jira_project_key,
            issue_type=cfg.jira_issue_type,
            test_case_issue_type=cfg.jira_testcase_issue_type,
            default_labels=cfg.jira_default_labels,
            story_points_field=cfg.jira_story_points_field,
            kb_label_field=cfg.jira_kb_label_field,
            timeout=cfg.jira_request_timeout,
            enabled=True,
            default_priority_name=cfg.jira_default_priority_name,
            priority_mapping=cfg.jira_priority_mapping,
        )
    else:
        if cfg.jira_automation_enabled:
            logger.warning(
                "Jira automation abilitata ma configurazione incompleta: nessun ticket verrà creato."
            )
        jira_client = None

    return ChatDependencies(
        embedder=embedder,
        reranker=reranker,
        response_cache=response_cache,
        rerank_cache=rerank_cache,
        history_manager=history_manager,
        newline=newline,
        double_newline=double_newline,
        section_separator=section_separator,
        project_planner=project_planner,
        jira_client=jira_client,
    )


__all__ = [
    "ChatDependencies",
    "ChatDependencyConfig",
    "create_default_dependencies",
]
