"""
ConfessGPT — system prompt loader and per-turn user prompt builder.

The system prompt is the heart of the agent: it embeds the CCC
references, the rite phases, the tone, and the absolute rules. It is
loaded once at plugin init and reused for every turn.
"""

from __future__ import annotations

from pathlib import Path

_PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "system_confessor.md"


def load_system_prompt() -> str:
    """Load the confessor system prompt from disk."""
    return _PROMPT_PATH.read_text(encoding="utf-8")


def build_turn_prompt(
    *,
    current_phase: str,
    contrition_detected: bool | None,
    amendment_purpose_detected: bool | None,
    explicit_refusal_of_repentance: bool,
    turn_count: int,
    penitent_utterance: str,
) -> str:
    """Build the per-turn user prompt for the confessor LLM.

    The session state is summarized briefly so the model knows where in
    the rite it stands without ever leaking earlier penitent content.
    Only the *current* utterance is included verbatim.
    """
    state_lines = [
        f"Fase corrente del rito: {current_phase}",
        f"Turno numero: {turn_count}",
        f"Contrizione rilevata: {_fmt_tri(contrition_detected)}",
        f"Proposito di emendamento rilevato: {_fmt_tri(amendment_purpose_detected)}",
        (
            "Rifiuto esplicito di pentirsi: "
            f"{'sì' if explicit_refusal_of_repentance else 'no'}"
        ),
    ]
    state_block = "\n".join(state_lines)
    penitent_block = penitent_utterance.strip() or "(silenzio — il penitente attende)"
    return (
        f"{state_block}\n\n"
        "Frase appena pronunciata dal penitente:\n"
        f"« {penitent_block} »\n\n"
        "Compi la prossima azione liturgica conforme alla fase. Aggiorna i "
        "flag di contrizione, proposito di emendamento e rifiuto esplicito "
        "in base a quanto il penitente ha appena detto. Restituisci "
        "esclusivamente il JSON dello schema."
    )


def _fmt_tri(value: bool | None) -> str:
    """Render a tri-state flag in Italian."""
    if value is True:
        return "sì"
    if value is False:
        return "no"
    return "non ancora valutato"
