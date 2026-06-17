"""Prompt assembly that injects the owner's style and memory into a reply.

Builds a system prompt that instructs the LLM to *be* the owner — constrained by
the quantitative style metrics, primed with few-shot exemplars of the owner's
own writing, and grounded in the salient facts retrieved from long-term memory.
Pure string assembly; no I/O, so it is fully unit-testable.
"""

from __future__ import annotations

from ..gateway.models import InboundMessage
from ..models import SalientFact
from ..style.models import StyleProfile


def _style_directives(profile: StyleProfile) -> str:
    """Render the style metrics as concrete, followable writing directives."""
    m = profile.metrics
    register = (
        "formal and polished"
        if m.formality >= 0.6
        else "casual and relaxed"
        if m.formality <= 0.4
        else "neutral, conversational"
    )
    lines = [
        f"- Register: write in a {register} tone.",
        f"- Length: keep replies around {int(m.avg_words_per_message)} words "
        f"(~{int(m.avg_message_chars)} characters); be concise.",
    ]
    if m.emoji_rate >= 0.3:
        emojis = " ".join(m.top_emojis[:5]) or "🙂"
        lines.append(f"- Emojis: use them naturally, e.g. {emojis}.")
    else:
        lines.append("- Emojis: use sparingly or not at all.")
    if m.top_expressions:
        lines.append(
            "- Vocabulary: favour the owner's habitual words: "
            + ", ".join(m.top_expressions[:6])
            + "."
        )
    lines.append(
        f"- Language: reply in {m.dominant_locale.upper()} unless the "
        "contact clearly writes in another language."
    )
    return "\n".join(lines)


def build_system_prompt(
    owner_name: str, profile: StyleProfile | None, facts: list[SalientFact]
) -> str:
    """Assemble the persona system prompt for a reply generation."""
    sections = [
        f"You are the digital twin of {owner_name}. Reply to an incoming "
        f"WhatsApp message AS {owner_name}, in the first person, so the contact "
        "cannot tell it was not written by them. Never reveal you are an AI.",
    ]
    if profile and profile.trained:
        sections.append(
            "## Writing style (mimic precisely)\n" + _style_directives(profile)
        )
        if profile.exemplars:
            examples = "\n".join(f"  • {ex.text}" for ex in profile.exemplars[:6])
            sections.append("## Authentic samples of how they write\n" + examples)
    else:
        sections.append(
            "## Writing style\nNo style profile yet — write naturally, concise, "
            "friendly, and human."
        )
    if facts:
        memory = "\n".join(f"  • {f.text}" for f in facts)
        sections.append(
            "## What you know about this contact (use only if relevant)\n" + memory
        )
    sections.append(
        "## Rules\n- Output ONLY the reply text, nothing else.\n"
        "- Do not invent facts not given above.\n"
        "- If a reply would be inappropriate or you are unsure, reply with an "
        "empty string."
    )
    return "\n\n".join(sections)


def build_user_prompt(message: InboundMessage, history: list[InboundMessage]) -> str:
    """Render the recent conversation plus the message to answer."""
    lines = ["## Recent conversation"]
    for msg in history[-8:]:
        who = "You" if msg.from_me else (msg.contact_name or "Them")
        lines.append(f"{who}: {msg.text}")
    lines.append("")
    lines.append(f"## Message to reply to\n{message.text}")
    lines.append("\nWrite your reply now:")
    return "\n".join(lines)


__all__ = ["build_system_prompt", "build_user_prompt"]
