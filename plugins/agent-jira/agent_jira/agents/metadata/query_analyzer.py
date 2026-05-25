from __future__ import annotations

import re
from typing import List, Optional

from .models import QueryMetadata


class QueryAnalyzer:
    """Analyzes user queries to extract intent and metadata."""

    PRIORITY_KEYWORDS = {
        "urgent": ["urgente", "urgent", "asap", "immediato", "critico"],
        "high": ["importante", "important", "priorità alta", "high priority"],
        "medium": ["normale", "normal", "medio", "medium"],
        "low": ["bassa priorità", "low priority", "opzionale", "optional"],
    }

    REQUEST_TYPES = {
        "stories": ["storie", "stories", "user story", "user stories"],
        "tests": ["test", "test case", "testing"],
        "analysis": ["analizza", "analyze", "analisi", "analysis"],
        "requirements": ["requisiti", "requirements", "specs"],
    }

    def analyze_query(self, query: str) -> QueryMetadata:
        """
        Analyze user query to extract metadata.
        """
        metadata = QueryMetadata()
        metadata.priority = self._extract_priority(query)
        metadata.request_type = self._extract_request_type(query)
        metadata.feature_module = self._extract_feature_module(query)
        metadata.quantity = self._extract_quantity(query)
        metadata.mentioned_stakeholders = self._extract_stakeholders(query)
        return metadata

    def _extract_priority(self, query: str) -> Optional[str]:
        query_lower = query.lower()
        for priority, keywords in self.PRIORITY_KEYWORDS.items():
            if any(kw in query_lower for kw in keywords):
                return priority
        return None

    def _extract_request_type(self, query: str) -> Optional[str]:
        query_lower = query.lower()
        for req_type, keywords in self.REQUEST_TYPES.items():
            if any(kw in query_lower for kw in keywords):
                return req_type
        return None

    def _extract_feature_module(self, query: str) -> Optional[str]:
        patterns = [
            r"(?:per il |for the |del |of the )?(?:modulo|module|feature)\s+(?:di\s+)?([a-z]+(?:\s+[a-z]+)?)",
            r"(?:sistema|system)\s+(?:di\s+)?([a-z]+(?:\s+[a-z]+)?)",
        ]
        for pattern in patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _extract_quantity(self, query: str) -> Optional[int]:
        match = re.search(
            r"(\d+)\s*(?:user\s*)?(?:storie|stories|story|test)", query, re.IGNORECASE
        )
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                pass
        return None

    def _extract_stakeholders(self, query: str) -> List[str]:
        names = re.findall(r"\b([A-Z][a-z]+\s+[A-Z][a-z]+)\b", query)
        return names
