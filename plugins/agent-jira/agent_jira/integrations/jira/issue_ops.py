from __future__ import annotations

import logging
import random
import time
from typing import Any, Mapping, Optional, Sequence, Union

import httpx

from .exceptions import JiraClientError
from .models import JiraIssueResult
from .payloads import build_user_story_payload
from .utils import coerce_http_error_message, extract_error_detail

logger = logging.getLogger(__name__)


class IssueOperations:
    def __init__(self, client: Any) -> None:
        self.client = client

    def create_user_story(
        self,
        *,
        title: str,
        description: str,
        acceptance_criteria: Sequence[str],
        business_value: Sequence[str],
        priority: Any,
        story_points: Optional[int],
        labels: Sequence[str],
        test_cases: Optional[Sequence[Union[Any, Mapping[str, Any]]]] = None,
        project_key: Optional[str] = None,
    ) -> JiraIssueResult:
        if not self.client.enabled:
            raise JiraClientError("Integrazione Jira disabilitata o non configurata.")

        effective_project_key = (project_key or self.client.project_key or "").strip()
        if not effective_project_key:
            raise JiraClientError("Specificare un project key Jira valido.")

        allowed_issue_types = self.client._allowed_issue_types(effective_project_key)
        effective_issue_type = self.client.issue_type
        if allowed_issue_types:
            pick = self.client._pick_issue_type(
                self.client.issue_type, allowed_issue_types, self.client.issue_type
            )
            norm_req = (self.client.issue_type or "").strip().lower()
            norm_pick = (pick or "").strip().lower()
            if pick and (
                norm_req == norm_pick
                or norm_pick.startswith(norm_req)
                or norm_req.startswith(norm_pick)
            ):
                effective_issue_type = pick
            elif pick:
                allowed_readable = ", ".join(allowed_issue_types)
                raise JiraClientError(
                    f"Issue type '{self.client.issue_type}' non disponibile sul progetto {effective_project_key}. "
                    f"Tipi ammessi: {allowed_readable}."
                )

        payload = build_user_story_payload(
            project_key=effective_project_key,
            issue_type=effective_issue_type,
            title=title,
            description=description,
            acceptance_criteria=acceptance_criteria,
            business_value=business_value,
            priority=priority,
            story_points=story_points,
            labels=labels,
            default_labels=self.client.default_labels,
            story_points_field=None,
            kb_label_field=self.client.kb_label_field,
            test_cases=test_cases,
            default_priority_name=self.client.default_priority_name,
            priority_mapping=self.client.priority_mapping,
        )

        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                response = httpx.post(
                    self.client._issue_endpoint,
                    json=payload,
                    auth=self.client._auth,
                    timeout=self.client.timeout,
                )
                response.raise_for_status()
                break
            except httpx.HTTPStatusError as exc:
                detail = extract_error_detail(exc.response)
                logger.exception("Errore Jira: %s", detail or exc)
                raise JiraClientError(detail or coerce_http_error_message(exc)) from exc
            except httpx.HTTPError as exc:
                if attempt < max_attempts - 1:
                    time.sleep(0.2 * (2**attempt) + random.random() * 0.1)
                    continue
                raise JiraClientError(coerce_http_error_message(exc)) from exc

        data = response.json()
        issue_key = data.get("key")
        return JiraIssueResult(
            summary=title,
            key=issue_key,
            url=self.client._issue_url(issue_key),
            status=self.client._fetch_issue_status(issue_key),
            issue_type=effective_issue_type,
            error=None,
        )
