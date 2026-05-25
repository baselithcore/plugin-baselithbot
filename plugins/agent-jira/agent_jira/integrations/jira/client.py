from __future__ import annotations

import logging
from typing import Dict, List, Mapping, Optional, Sequence

import httpx

from .issue_ops import IssueOperations
from .models import JiraIssueResult
from .search import JiraSearchClient
from .search_ops import SearchOperations
from .test_ops import TestOperations
from .utils import extract_kb_label

logger = logging.getLogger(__name__)


class JiraClient:
    """Client for Jira Cloud REST API. Slim orchestrator."""

    def __init__(
        self,
        *,
        base_url: str,
        email: str,
        api_token: str,
        project_key: str,
        issue_type: str = "Story",
        test_case_issue_type: str = "Test Case",
        default_labels: Optional[Sequence[str]] = None,
        story_points_field: Optional[str] = None,
        kb_label_field: Optional[str] = None,
        timeout: float = 15.0,
        enabled: bool = True,
        default_priority_name: str = "Medium",
        priority_mapping: Optional[Mapping[str, str]] = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.email = email
        self.api_token = api_token
        self.project_key = project_key
        self.issue_type = issue_type
        self.test_case_issue_type = test_case_issue_type or "Test Case"
        self.default_labels = list(default_labels or [])
        self.story_points_field = story_points_field
        self.kb_label_field = (kb_label_field or "").strip() or None
        self.timeout = timeout
        self.enabled = enabled and all(
            [self.base_url, self.email, self.api_token, self.project_key]
        )
        self.default_priority_name = default_priority_name or "Medium"
        self.priority_mapping = {
            k.strip().lower(): v.strip()
            for k, v in (priority_mapping or {}).items()
            if k and v
        }
        self._auth = (self.email, self.api_token)
        self._issue_endpoint = f"{self.base_url}/rest/api/3/issue"
        self.search_client = JiraSearchClient(
            base_url=self.base_url,
            auth=self._auth,
            timeout=self.timeout,
            kb_label_field=self.kb_label_field,
        )
        self._issue_types_cache: Dict[str, List[str]] = {}

        # Operations
        self._issue_ops = IssueOperations(self)
        self._test_ops = TestOperations(self)
        self._search_ops = SearchOperations(self)

    # --- Core Methods ---
    def is_ready(self) -> bool:
        return self.enabled

    def check_connection(self) -> bool:
        if not self.enabled:
            return False
        try:
            httpx.get(
                f"{self.base_url}/rest/api/3/myself", auth=self._auth, timeout=5.0
            ).raise_for_status()
            return True
        except Exception:
            return False

    # --- Delegated Operations ---
    def create_user_story(self, **kwargs) -> JiraIssueResult:
        return self._issue_ops.create_user_story(**kwargs)

    def create_test_case(self, **kwargs) -> JiraIssueResult:
        return self._test_ops.create_test_case(**kwargs)

    def list_projects(self, **kwargs) -> List[Dict[str, str]]:
        return self._search_ops.list_projects(**kwargs)

    def search_issues_by_label(self, **kwargs) -> list[JiraIssueResult]:
        return self._search_ops.search_issues_by_label(**kwargs)

    def fetch_linked_issues(self, **kwargs) -> list[JiraIssueResult]:
        return self._search_ops.fetch_linked_issues(**kwargs)

    # --- Internal Helpers ---
    def _pick_issue_type(
        self, requested: str, allowed: Sequence[str], default_fallback: str
    ) -> str:
        if not allowed:
            return requested or default_fallback
        req_norm = (
            (requested or "")
            .strip()
            .lower()
            .replace(" ", "")
            .replace("-", "")
            .replace("_", "")
        )
        for name in allowed:
            norm = (
                name.strip().lower().replace(" ", "").replace("-", "").replace("_", "")
            )
            if (
                norm == req_norm
                or norm.startswith(req_norm)
                or req_norm.startswith(norm)
            ):
                return name
        return allowed[0]

    def _allowed_issue_types(self, project_key: str) -> List[str]:
        key = project_key.strip().upper()
        if not key:
            return []
        if key in self._issue_types_cache:
            return self._issue_types_cache[key]
        try:
            resp = httpx.get(
                f"{self.base_url}/rest/api/3/issue/createmeta",
                params={"projectKeys": key, "expand": "projects.issuetypes"},
                auth=self._auth,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            projects = resp.json().get("projects") or []
            names = [
                it.get("name")
                for ps in projects
                if ps.get("key") == key
                for it in ps.get("issuetypes") or []
            ]
            self._issue_types_cache[key] = names
            return names
        except Exception:
            return []

    def _issue_url(self, key: Optional[str]) -> Optional[str]:
        return f"{self.base_url}/browse/{key}" if key else None

    def _fetch_issue_status(self, key: Optional[str]) -> Optional[str]:
        if not key:
            return None
        try:
            resp = httpx.get(
                f"{self.base_url}/rest/api/3/issue/{key}",
                params={"fields": "status"},
                auth=self._auth,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            st = resp.json().get("fields", {}).get("status", {})
            return st.get("name") or st.get("displayName")
        except Exception:
            return None

    def _fetch_issue_kb_label(self, key: str) -> Optional[str]:
        try:
            resp = httpx.get(
                f"{self.base_url}/rest/api/3/issue/{key}",
                params={
                    "fields": "labels"
                    + (f",{self.kb_label_field}" if self.kb_label_field else "")
                },
                auth=self._auth,
                timeout=self.timeout,
            )
            resp.raise_for_status()
            f = resp.json().get("fields", {})
            if self.kb_label_field and f.get(self.kb_label_field):
                return f[self.kb_label_field][0]
            return extract_kb_label(f.get("labels") or [])
        except Exception:
            return None

    def _link_issue(self, *, test_key: str, story_key: str) -> None:
        try:
            httpx.post(
                f"{self.base_url}/rest/api/3/issueLink",
                json={
                    "type": {"name": "Relates"},
                    "outwardIssue": {"key": test_key},
                    "inwardIssue": {"key": story_key},
                },
                auth=self._auth,
                timeout=self.timeout,
            ).raise_for_status()
        except Exception:
            pass
