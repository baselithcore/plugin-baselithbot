from __future__ import annotations

import logging
from typing import Any, Dict, List, Mapping, Sequence

import httpx

from .exceptions import JiraClientError
from .models import JiraIssueResult
from .utils import coerce_http_error_message, extract_error_detail

logger = logging.getLogger(__name__)


class SearchOperations:
    def __init__(self, client: Any) -> None:
        self.client = client

    def list_projects(self, *, max_results: int = 200) -> List[Dict[str, str]]:
        """Recupera la lista di progetti Jira accessibili per l'utente."""
        if not self.client.enabled:
            raise JiraClientError("Integrazione Jira disabilitata o non configurata.")
        try:
            response = httpx.get(
                f"{self.client.base_url}/rest/api/3/project/search",
                params={"maxResults": max(1, max_results)},
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
            logger.exception("Errore recupero progetti: %s", detail or exc)
            raise JiraClientError(detail or coerce_http_error_message(exc)) from exc

        data = response.json()
        raw_projects = data.get("values") if isinstance(data, Mapping) else data
        projects: List[Dict[str, str]] = []
        for item in raw_projects or []:
            key = (item.get("key") or "").strip()
            name = (item.get("name") or "").strip()
            if key and name:
                projects.append({"key": key, "name": name})
        return projects

    def search_issues_by_label(
        self, label: str, *, max_results: int = 10
    ) -> list[JiraIssueResult]:
        if not self.client.enabled:
            return []
        return self.client.search_client.search_issues_by_label(
            label, max_results=max_results
        )

    def fetch_linked_issues(
        self, issue_keys: Sequence[str], max_links_per_issue: int = 20
    ) -> list[JiraIssueResult]:
        results: list[JiraIssueResult] = []
        seen: set[str] = set()
        for key in issue_keys:
            if not key:
                continue
            try:
                url = f"{self.client.base_url}/rest/api/3/issue/{key}"
                response = httpx.get(
                    url,
                    params={"fields": "issuelinks,summary,status,issuetype,labels"},
                    auth=self.client._auth,
                    timeout=self.client.timeout,
                )
                response.raise_for_status()
                payload = response.json()
                fields = payload.get("fields") or {}
                links = fields.get("issuelinks") or []
                for link in links[:max_links_per_issue]:
                    target = link.get("outwardIssue") or link.get("inwardIssue")
                    target_key = (
                        target.get("key") if isinstance(target, Mapping) else None
                    )
                    if not target_key or target_key in seen:
                        continue
                    tfields = target.get("fields") or {}
                    results.append(
                        JiraIssueResult(
                            summary=str(tfields.get("summary") or target_key),
                            key=target_key,
                            url=self.client._issue_url(target_key),
                            status=tfields.get("status", {}).get("name")
                            if isinstance(tfields.get("status"), dict)
                            else None,
                            issue_type=tfields.get("issuetype", {}).get("name")
                            if isinstance(tfields.get("issuetype"), dict)
                            else None,
                        )
                    )
                    seen.add(target_key)
            except Exception:
                logger.debug("Fetch links failed for %s", key, exc_info=True)
        return results
