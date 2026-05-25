from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class JiraIssueResult:
    summary: str
    key: Optional[str] = None
    url: Optional[str] = None
    status: Optional[str] = None
    issue_type: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "summary": self.summary,
            "key": self.key,
            "url": self.url,
            "status": self.status,
            "issue_type": self.issue_type,
            "error": self.error,
        }


__all__ = ["JiraIssueResult"]
