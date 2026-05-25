"""RAG result dataclass."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from llm_wiki.agents.code_block_guard import CodeBlockReport
from llm_wiki.agents.groundedness import GroundednessReport
from llm_wiki.agents.intent_classifier import IntentReport
from llm_wiki.agents.numeric_guard import NumericGuardReport


@dataclass
class RAGResult:
    answer: str
    sources: list[dict[str, Any]]
    context: str
    hits: list[dict[str, Any]]
    memories: list[dict[str, Any]]
    history_used: int = 0
    intent_report: IntentReport | None = None
    groundedness_report: GroundednessReport | None = None
    code_block_report: CodeBlockReport | None = None
    numeric_guard_report: NumericGuardReport | None = None
