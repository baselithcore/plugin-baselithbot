from __future__ import annotations

import logging
from typing import Any, Optional, Sequence

import httpx

from .adf import build_bdd_scenario_adf
from .exceptions import JiraClientError
from .models import JiraIssueResult
from .utils import coerce_http_error_message, extract_error_detail, sanitize_priority

logger = logging.getLogger(__name__)


class TestOperations:
    def __init__(self, client: Any) -> None:
        self.client = client

    def create_test_case(
        self,
        *,
        story_key: str,
        scenario_title: str,
        scenario_id: Optional[str],
        given: Sequence[str],
        when: Sequence[str],
        then: Sequence[str],
        labels: Sequence[str],
        priority: Any,
        issue_type: Optional[str] = None,
        project_key: Optional[str] = None,
    ) -> JiraIssueResult:
        if not self.client.enabled:
            raise JiraClientError("Integrazione Jira disabilitata o non configurata.")
        effective_project_key = (project_key or self.client.project_key or "").strip()
        if not effective_project_key:
            raise JiraClientError("Specificare un project key Jira valido.")

        desired_issue_type = (
            issue_type or self.client.test_case_issue_type
        ).strip() or "Test Case"
        effective_issue_type = desired_issue_type
        allowed_issue_types = self.client._allowed_issue_types(effective_project_key)
        if allowed_issue_types:
            pick = self.client._pick_issue_type(
                desired_issue_type, allowed_issue_types, desired_issue_type
            )
            if pick:
                effective_issue_type = pick

        story_kb_label = (
            self.client._fetch_issue_kb_label(story_key)
            if self.client.kb_label_field
            else None
        )

        description_adf = build_bdd_scenario_adf(
            scenario_title=scenario_title,
            scenario_id=scenario_id,
            given=given,
            when=when,
            then=then,
            priority=priority,
        )

        payload = {
            "fields": {
                "project": {"key": effective_project_key},
                "summary": scenario_title[:254],
                "issuetype": {"name": effective_issue_type},
                "description": description_adf,
                "priority": {
                    "name": sanitize_priority(
                        priority,
                        default_priority_name=self.client.default_priority_name,
                        priority_mapping=self.client.priority_mapping,
                    )
                },
                "labels": list(
                    dict.fromkeys(
                        [
                            *self.client.default_labels,
                            *labels,
                            "bdd-test",
                            *([story_kb_label] if story_kb_label else []),
                        ]
                    )
                ),
            }
        }

        try:
            response = httpx.post(
                self.client._issue_endpoint,
                json=payload,
                auth=self.client._auth,
                timeout=self.client.timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            detail = (
                extract_error_detail(exc.response)
                if isinstance(exc, httpx.HTTPStatusError)
                else None
            )
            logger.exception("Errore Jira create test: %s", detail or exc)
            raise JiraClientError(detail or coerce_http_error_message(exc)) from exc

        data = response.json()
        issue_key = data.get("key")
        if issue_key:
            self.client._link_issue(test_key=issue_key, story_key=story_key)

        return JiraIssueResult(
            summary=scenario_title,
            key=issue_key,
            url=self.client._issue_url(issue_key),
            status=self.client._fetch_issue_status(issue_key) if issue_key else None,
            issue_type=effective_issue_type,
            error=None,
        )
