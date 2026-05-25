"""Internal helper: emit events to per-doc bus during pipeline execution."""

from typing import Any

from ..schemas.state import CheckState
from ..services import events


async def emit(state: CheckState, event: dict[str, Any]) -> None:
    doc_id = state.get("doc_id")
    if doc_id:
        await events.publish(doc_id, event)


async def emit_phase(state: CheckState, phase: str) -> None:
    await emit(state, {"type": "phase", "phase": phase})


async def emit_finding(state: CheckState, finding: Any) -> None:
    payload = finding.model_dump() if hasattr(finding, "model_dump") else finding
    await emit(state, {"type": "finding", "finding": payload})


async def emit_progress(
    state: CheckState, current: int, total: int, label: str | None = None
) -> None:
    await emit(
        state, {"type": "progress", "current": current, "total": total, "label": label}
    )


_PHASE_ORDER = ["classifier", "structurer", "legal", "technical", "pii", "synthesizer"]


async def emit_phase_progress(state: CheckState, phase: str) -> None:
    """Emit phase + cumulative progress percent."""
    await emit_phase(state, phase)
    if phase in _PHASE_ORDER:
        idx = _PHASE_ORDER.index(phase) + 1
        await emit_progress(state, idx, len(_PHASE_ORDER), phase)
