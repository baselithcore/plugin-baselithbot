from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from agent_jira.cache import TTLCache
from agent_jira.telemetry import telemetry
from agent_jira.tenant_context import get_current_tenant_id

HistoryTurns = List[Dict[str, str]]
HistorySummary = str
SUMMARY_HEADER = "Riassunto conversazione:"
SUMMARY_DIVIDER = "\n\n---\n\n"


class ChatHistoryManager:
    def __init__(
        self,
        cache: Optional[TTLCache],
        *,
        max_turns: int,
        summary_enabled: bool = False,
        summary_max_turns: int = 8,
        summary_max_chars: int = 800,
    ) -> None:
        self._cache = cache
        self._max_turns = max_turns
        self._summary_enabled = summary_enabled
        self._summary_max_turns = max(0, summary_max_turns)
        self._summary_max_chars = max(120, summary_max_chars)

    @staticmethod
    def _scoped_key(conversation_id: str) -> str:
        """Genera una cache key con namespace tenant per isolare le conversazioni."""
        tenant_id = get_current_tenant_id()
        if tenant_id:
            return f"t:{tenant_id}:{conversation_id}"
        return conversation_id

    def load(self, conversation_id: Optional[str]) -> Tuple[HistoryTurns, str]:
        if not conversation_id or self._cache is None:
            return [], ""

        existing_turns, summary = self._load_payload(conversation_id)
        if not existing_turns and not summary:
            return [], ""

        trimmed = existing_turns[-self._max_turns :]
        sections: List[str] = []
        summary_clean = summary.strip()
        if summary_clean:
            sections.append(f"{SUMMARY_HEADER}\n{summary_clean}")
        if trimmed:
            history_lines = [
                f"Utente: {turn['query']}\nAssistente: {turn['answer']}"
                for turn in trimmed
            ]
            sections.append("\n\n".join(history_lines))

        history_text = SUMMARY_DIVIDER.join(part for part in sections if part).strip()
        return trimmed, history_text

    def append_turn(
        self,
        conversation_id: Optional[str],
        history_turns: HistoryTurns,
        user_query: str,
        answer: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        if not conversation_id or self._cache is None:
            return

        sanitized_query = (user_query or "").strip()
        sanitized_answer = (answer or "").strip()
        if not sanitized_query or not sanitized_answer:
            return

        existing_turns, existing_summary = self._load_payload(conversation_id)
        combined_turns = list(existing_turns)

        turn_data = {"query": sanitized_query, "answer": sanitized_answer}
        if metadata:
            turn_data.update(metadata)

        combined_turns.append(turn_data)
        telemetry.increment("history.turn_received")

        new_summary = existing_summary.strip()
        if self._summary_enabled and len(combined_turns) > self._max_turns:
            overflow_count = len(combined_turns) - self._max_turns
            overflow_turns = combined_turns[:overflow_count]
            recent_turns = combined_turns[overflow_count:]
            new_summary = self._merge_summary(existing_summary, overflow_turns)
            combined_turns = recent_turns
            telemetry.increment("history.summary_updated")
        else:
            combined_turns = combined_turns[-self._max_turns :]

        payload: Dict[str, Any] = {"turns": combined_turns}
        if new_summary:
            payload["summary"] = new_summary
        self._cache.set(self._scoped_key(conversation_id), payload)
        telemetry.increment("history.turn_stored")

    def _load_payload(
        self, conversation_id: str
    ) -> Tuple[HistoryTurns, HistorySummary]:
        if self._cache is None:
            return [], ""

        stored = self._cache.get(self._scoped_key(conversation_id))
        summary = ""
        turns: HistoryTurns = []

        if isinstance(stored, dict):
            summary = str(stored.get("summary") or "").strip()
            turns = self._sanitize_turns(stored.get("turns"))
        elif isinstance(stored, list):
            turns = self._sanitize_turns(stored)

        return turns, summary

    def _sanitize_turns(self, raw: Any) -> HistoryTurns:
        sanitized: HistoryTurns = []
        if not isinstance(raw, list):
            return sanitized
        for entry in raw:
            if not isinstance(entry, dict):
                continue
            past_query = (entry.get("query") or "").strip()
            past_answer = (entry.get("answer") or "").strip()
            if not past_query or not past_answer:
                continue

            clean_entry = {"query": past_query, "answer": past_answer}
            # Preserve metadata fields
            if "jira_issues" in entry:
                clean_entry["jira_issues"] = entry["jira_issues"]
            if "duration" in entry:
                clean_entry["duration"] = entry["duration"]

            sanitized.append(clean_entry)
        return sanitized

    def _merge_summary(
        self, previous_summary: str, overflow_turns: HistoryTurns
    ) -> str:
        if not overflow_turns:
            return previous_summary.strip()

        summary_lines: List[str] = [
            line.strip() for line in previous_summary.splitlines() if line.strip()
        ]

        for turn in overflow_turns:
            summary_lines.append(self._format_summary_line(turn))

        if summary_lines and self._summary_max_turns > 0:
            summary_lines = summary_lines[-self._summary_max_turns :]

        summary_text = "\n".join(summary_lines).strip()
        return self._truncate_summary(summary_text)

    def _format_summary_line(self, turn: Dict[str, str]) -> str:
        user_part = turn.get("query", "").strip()
        answer_part = turn.get("answer", "").strip()
        line = f"Utente: {user_part} → Assistente: {answer_part}"
        if len(line) > 240:
            line = f"{line[:237].rstrip()}..."
        return line

    def _truncate_summary(self, text: str) -> str:
        if len(text) <= self._summary_max_chars:
            return text

        truncated = text[: self._summary_max_chars].rstrip()
        if len(truncated) == self._summary_max_chars:
            truncated = truncated[:-1].rstrip()
        return f"{truncated}..."
