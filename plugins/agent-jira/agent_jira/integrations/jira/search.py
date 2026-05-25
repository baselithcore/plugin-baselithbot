import logging
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import httpx

from .models import JiraIssueResult
from .utils import build_kb_label_clause, coerce_http_error_message

logger = logging.getLogger(__name__)


class JiraSearchClient:
    def __init__(
        self,
        *,
        base_url: str,
        auth: Tuple[str, str],
        timeout: float,
        kb_label_field: Optional[str],
    ) -> None:
        self.base_url = base_url
        self.auth = auth
        self.timeout = timeout
        self.kb_label_field = kb_label_field

    def search_issues_by_label(
        self, label: str, *, max_results: int = 10
    ) -> List[JiraIssueResult]:
        if not label:
            return []
        clause = build_kb_label_clause(label, self.kb_label_field)
        jql = f"{clause} ORDER BY updated DESC"
        max_results = max(1, min(max_results, 50))

        attempts = [
            (
                "search/jql GET",
                self._call,
                {
                    "method": "get",
                    "path": "/rest/api/3/search/jql",
                    "params": {
                        "jql": jql,
                        "startAt": 0,
                        "maxResults": max_results,
                        "fields": "summary,status,labels,issuetype",
                    },
                },
            ),
            (
                "search/jql POST",
                self._call,
                {
                    "method": "post",
                    "path": "/rest/api/3/search/jql",
                    "json": {
                        "queries": [
                            {
                                "query": {"type": "JQL", "value": jql},
                            }
                        ],
                        "fields": {
                            "include": ["summary", "status", "issuetype"],
                            "exclude": [],
                        },
                        "pagination": {"startAt": 0, "maxResults": max_results},
                    },
                },
            ),
            (
                "search GET",
                self._call,
                {
                    "method": "get",
                    "path": "/rest/api/3/search",
                    "params": {
                        "jql": jql,
                        "startAt": 0,
                        "maxResults": max_results,
                        "fields": "summary,status,issuetype",
                    },
                },
            ),
            (
                "search POST",
                self._call,
                {
                    "method": "post",
                    "path": "/rest/api/3/search",
                    "json": {
                        "jql": jql,
                        "startAt": 0,
                        "maxResults": max_results,
                        "fields": ["summary", "status", "issuetype"],
                    },
                },
            ),
        ]

        data: Optional[Dict[str, Any]] = None
        for label_name, func, kwargs in attempts:
            try:
                logger.debug(
                    "Jira search attempt %s jql=%s params=%s", label_name, jql, kwargs
                )
                data = func(**kwargs)
                if data is not None:
                    logger.debug(
                        "Jira search %s returned keys=%s total=%s",
                        label_name,
                        list(data.keys()),
                        data.get("total") if isinstance(data, Mapping) else None,
                    )
                    break
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "Ricerca Jira fallita (%s) per etichetta %s: %s",
                    label_name,
                    label,
                    coerce_http_error_message(exc),
                )
            except httpx.HTTPError:
                logger.warning(
                    "Ricerca Jira fallita (%s) per etichetta %s",
                    label_name,
                    label,
                )

        if data is None:
            return []
        issues_payload = self._collect_issue_payloads(data)
        logger.debug(
            "Ricerca Jira completata per label %s: %d issue raccolte",
            label,
            len(issues_payload),
        )
        return [self._to_issue_result(issue) for issue in issues_payload]

    def _call(
        self,
        *,
        method: str,
        path: str,
        params: Optional[Mapping[str, Any]] = None,
        json: Optional[Mapping[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        url = f"{self.base_url}{path}"
        response = httpx.request(
            method=method,
            url=url,
            params=params,
            json=json,
            auth=self.auth,
            timeout=self.timeout,
        )
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _collect_issue_payloads(data: Mapping[str, Any]) -> List[Mapping[str, Any]]:
        result_sets = data.get("results")
        issues_payload: List[Mapping[str, Any]] = []
        if isinstance(result_sets, Sequence):
            for entry in result_sets:
                if isinstance(entry, Mapping):
                    issues = entry.get("issues")
                    if isinstance(issues, Sequence):
                        issues_payload.extend(
                            issue for issue in issues if isinstance(issue, Mapping)
                        )
        if not issues_payload and isinstance(data.get("issues"), Sequence):
            issues_payload = [
                issue for issue in data.get("issues", []) if isinstance(issue, Mapping)
            ]
        return issues_payload

    def _to_issue_result(self, issue: Mapping[str, Any]) -> JiraIssueResult:
        key = issue.get("key")
        fields = issue.get("fields") or {}
        summary = str(fields.get("summary") or "").strip() or key or "User story"
        status_field = fields.get("status")
        status_name: Optional[str] = None
        if isinstance(status_field, Mapping):
            raw_status = status_field.get("name")
            if isinstance(raw_status, str) and raw_status.strip():
                status_name = raw_status.strip()
        issuetype_field = fields.get("issuetype")
        issue_type: Optional[str] = None
        if isinstance(issuetype_field, Mapping):
            raw_type = issuetype_field.get("name")
            if isinstance(raw_type, str) and raw_type.strip():
                issue_type = raw_type.strip()
        issue_url = self._issue_url(key)
        return JiraIssueResult(
            summary=summary,
            key=key,
            url=issue_url,
            status=status_name,
            issue_type=issue_type,
            error=None,
        )

    def _issue_url(self, key: Optional[str]) -> Optional[str]:
        if not key:
            return None
        return f"{self.base_url}/browse/{key}"


__all__ = ["JiraSearchClient"]
