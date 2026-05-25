"""SynthesizerAgent — dedup, score, summary. Runs after parallel fan-in."""

from collections import defaultdict
from typing import Any

from ..schemas.finding import Finding
from ..schemas.state import CheckState
from ._emit import emit_phase_progress


def _dedup(findings: list[Finding]) -> list[Finding]:
    keep: dict[tuple[str, str], Finding] = {}
    for f in findings:
        key = (f.evidence.chunk_id, f.rule_id)
        existing = keep.get(key)
        if existing is None or f.confidence > existing.confidence:
            keep[key] = f
    return list(keep.values())


def _score(findings: list[Finding]) -> int:
    fail = sum(1 for f in findings if f.severity == "FAIL")
    warn = sum(1 for f in findings if f.severity == "WARN")
    return max(0, 100 - fail * 8 - warn * 3)


def _by_severity(findings: list[Finding]) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for f in findings:
        out[f.severity] += 1
    return dict(out)


async def run(state: CheckState) -> dict[str, Any]:
    """Synthesize: deduplicate concurrently-emitted findings, compute score.

    With parallel fan-out, agents emit findings via reducer-add concat.
    Synthesizer reads the merged list and produces the canonical output.
    """
    await emit_phase_progress(state, "synthesizer")
    raw = state.get("findings", [])
    deduped = _dedup(raw)
    return {
        "final_findings": deduped,
        "score": _score(deduped),
        "by_severity": _by_severity(deduped),
    }
