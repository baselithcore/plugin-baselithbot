"""Pure, dependency-free communicative-style extraction.

Turns a corpus of the owner's own messages into a :class:`StyleProfile`:
quantitative metrics (length, emoji/question/exclamation rates, formality) plus
a curated few-shot exemplar set. No LLM and no I/O — fully deterministic and
unit-testable, so it runs anywhere the plugin is imported.
"""

from __future__ import annotations

import re
from collections import Counter

from ..gateway.models import InboundMessage
from .models import StyleExemplar, StyleMetrics, StyleProfile

# Broad emoji ranges (symbols, pictographs, transport, flags, dingbats).
_EMOJI_RE = re.compile(
    "[\U0001f300-\U0001faff\U00002600-\U000027bf\U0001f000-\U0001f0ff]"
)
_WORD_RE = re.compile(r"[^\W\d_]+", re.UNICODE)
# Casual markers nudge formality down; their absence and longer words nudge up.
_CASUAL_MARKERS = {
    "lol",
    "haha",
    "ahah",
    "ahaha",
    "ok",
    "okk",
    "cmq",
    "tvb",
    "raga",
    "boh",
    "nope",
    "yep",
    "gonna",
    "wanna",
    "u",
    "ur",
    "thx",
}
_IT_TOKENS = {"che", "non", "per", "sono", "anche", "ciao", "grazie", "però"}
_EXEMPLAR_MIN_CHARS = 12
_EXEMPLAR_MAX_CHARS = 180
_MAX_EXEMPLARS = 8
_TOP_N = 8


def _formality(text: str, casual_hits: int, words: int) -> float:
    """Heuristic 0..1 formality score for a single message."""
    if not words:
        return 0.5
    avg_word_len = sum(len(w) for w in _WORD_RE.findall(text)) / max(words, 1)
    score = 0.5 + min(avg_word_len - 4.0, 3.0) * 0.08
    score -= casual_hits * 0.12
    if text and text == text.lower():  # never capitalised → more casual
        score -= 0.05
    return max(0.0, min(1.0, score))


def extract_style(owner_id: str, messages: list[InboundMessage]) -> StyleProfile:
    """Build a :class:`StyleProfile` from the owner's outbound messages.

    Args:
        owner_id: The owner the profile belongs to.
        messages: Messages authored by the owner (``from_me`` already filtered
            by the caller is fine; non-owner messages are ignored defensively).

    Returns:
        A profile flagged ``trained`` once enough non-empty samples are present.
    """
    texts = [m.text.strip() for m in messages if m.from_me and m.text.strip()]
    n = len(texts)
    if n == 0:
        return StyleProfile(owner_id=owner_id, sample_size=0, trained=False)

    total_chars = total_words = emoji_count = questions = exclamations = 0
    upper_tokens = total_tokens = formality_sum = 0
    emoji_counter: Counter[str] = Counter()
    expr_counter: Counter[str] = Counter()
    it_hits = 0

    for text in texts:
        words = _WORD_RE.findall(text)
        total_chars += len(text)
        total_words += len(words)
        emojis = _EMOJI_RE.findall(text)
        emoji_count += len(emojis)
        emoji_counter.update(emojis)
        if text.endswith("?"):
            questions += 1
        if text.endswith("!"):
            exclamations += 1
        tokens = text.split()
        total_tokens += len(tokens)
        upper_tokens += sum(1 for t in tokens if len(t) > 1 and t.isupper())
        lowered = {w.lower() for w in words}
        casual_hits = len(lowered & _CASUAL_MARKERS)
        expr_counter.update(w.lower() for w in words if len(w) >= 4)
        it_hits += len(lowered & _IT_TOKENS)
        formality_sum += _formality(text, casual_hits, len(words))

    metrics = StyleMetrics(
        avg_message_chars=round(total_chars / n, 2),
        avg_words_per_message=round(total_words / n, 2),
        emoji_rate=round(emoji_count / n, 3),
        question_rate=round(questions / n, 3),
        exclamation_rate=round(exclamations / n, 3),
        uppercase_ratio=round(upper_tokens / total_tokens, 3) if total_tokens else 0.0,
        formality=round(formality_sum / n, 3),
        top_emojis=[e for e, _ in emoji_counter.most_common(_TOP_N)],
        top_expressions=[w for w, _ in expr_counter.most_common(_TOP_N)],
        dominant_locale="it" if it_hits >= n * 0.3 else "en",
    )
    exemplars = [
        StyleExemplar(text=t)
        for t in texts
        if _EXEMPLAR_MIN_CHARS <= len(t) <= _EXEMPLAR_MAX_CHARS
    ][:_MAX_EXEMPLARS]

    return StyleProfile(
        owner_id=owner_id,
        sample_size=n,
        trained=True,
        metrics=metrics,
        exemplars=exemplars,
    )


__all__ = ["extract_style"]
