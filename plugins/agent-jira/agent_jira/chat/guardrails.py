from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Optional

from agent_jira.config import (
    CHAT_GUARDRAILS_BLOCK_KEYWORDS,
    CHAT_GUARDRAILS_BLOCK_MESSAGE,
    CHAT_GUARDRAILS_ENABLED,
    CHAT_GUARDRAILS_OUT_OF_SCOPE_MESSAGE,
    CHAT_GUARDRAILS_OUT_OF_SCOPE_PATTERNS,
)

_DEFAULT_BLOCK_KEYWORDS: List[str] = [
    "password",
    "credenziali",
    "numero di carta",
    "phishing",
    "malware",
    "sql injection",
    "drop table",
    "exploit",
]

_DEFAULT_OUT_OF_SCOPE_PATTERNS: List[str] = [
    r"\bbarzelletta\b",
    r"\bmeteo\b",
    r"\bnotizie?\b",
    r"\bfilm\b",
    r"\bchi\s+ha\s+inventato\b",
    r"\bche\s+cosa\s+significa\b",
]


def _normalize_keywords(values: Iterable[str]) -> List[str]:
    normalized: List[str] = []
    for value in values:
        value_clean = (value or "").strip().lower()
        if value_clean:
            normalized.append(value_clean)
    return normalized


def _compile_patterns(expressions: Iterable[str]) -> List[re.Pattern[str]]:
    compiled: List[re.Pattern[str]] = []
    for expression in expressions:
        pattern = (expression or "").strip()
        if not pattern:
            continue
        try:
            compiled.append(re.compile(pattern, flags=re.IGNORECASE))
        except re.error:
            continue
    return compiled


_BLOCK_KEYWORDS = _normalize_keywords(
    CHAT_GUARDRAILS_BLOCK_KEYWORDS or _DEFAULT_BLOCK_KEYWORDS
)
_OUT_OF_SCOPE_PATTERNS = _compile_patterns(
    CHAT_GUARDRAILS_OUT_OF_SCOPE_PATTERNS or _DEFAULT_OUT_OF_SCOPE_PATTERNS
)


@dataclass
class GuardrailDecision:
    action: str = "allow"
    reason: Optional[str] = None
    response: Optional[str] = None
    matched: Optional[str] = None


def evaluate_guardrails(query: str) -> GuardrailDecision:
    if not CHAT_GUARDRAILS_ENABLED:
        return GuardrailDecision()

    text = (query or "").strip()
    if not text:
        return GuardrailDecision()

    text_lower = text.lower()

    for keyword in _BLOCK_KEYWORDS:
        if keyword and keyword in text_lower:
            return GuardrailDecision(
                action="block",
                reason="blocked_keyword",
                response=CHAT_GUARDRAILS_BLOCK_MESSAGE,
                matched=keyword,
            )

    for pattern in _OUT_OF_SCOPE_PATTERNS:
        if pattern.search(text):
            return GuardrailDecision(
                action="fallback",
                reason="out_of_scope",
                response=CHAT_GUARDRAILS_OUT_OF_SCOPE_MESSAGE,
                matched=pattern.pattern,
            )

    return GuardrailDecision()


__all__ = ["GuardrailDecision", "evaluate_guardrails"]
