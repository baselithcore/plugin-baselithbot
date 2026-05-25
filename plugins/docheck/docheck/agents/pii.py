"""PIIDetectorAgent — regex pre-filter + LLM verifier ensemble."""

import uuid
from typing import Any

from ..core.doc_taxonomy import agent_applies
from ..core.logging import log
from ..schemas.finding import Citation, Finding, PolicyRef, ReasoningStep
from ..schemas.state import CheckState, Chunk
from ..services.llm import chat_json_resilient
from ._emit import emit_finding, emit_phase_progress
from .technical import PATTERNS

VERIFIER_SYSTEM = """PII verification stage. Confirm or reject candidates.
Reject when context indicates: example, placeholder, fictional, public registry data.
Italian PII patterns include codice fiscale, partita IVA, IBAN IT.
Output JSON only."""


async def run(state: CheckState) -> CheckState:
    await emit_phase_progress(state, "pii")
    doc_type = state.get("doc_type") or "other"
    if not agent_applies("pii", doc_type):
        log.info(
            "pii.skipped_by_doc_type", doc_id=state.get("doc_id"), doc_type=doc_type
        )
        return {"findings": []}
    chunks = state.get("chunks", [])
    findings: list[Finding] = []
    candidates = []

    spans: dict[tuple[str, str], tuple[int, int]] = {}
    for chunk in chunks:
        for pii_type, pat in PATTERNS.items():
            if pii_type == "iso_date":
                continue
            for m in pat.finditer(chunk.text):
                start = max(0, m.start() - 60)
                end = min(len(chunk.text), m.end() + 60)
                key = (chunk.id, pii_type)
                spans.setdefault(key, (m.start(), m.end()))
                candidates.append(
                    {
                        "type": pii_type,
                        "value": m.group(0),
                        "chunk_id": chunk.id,
                        "line": chunk.line_start,
                        "context": chunk.text[start:end],
                    }
                )

    if not candidates:
        return {"findings": []}

    user = f'Candidates: {candidates}\n\nReturn {{"verified":[...],"rejected":[...]}}'
    try:
        out = await chat_json_resilient(
            system=VERIFIER_SYSTEM, user=user, max_tokens=4096
        )
    except Exception as exc:
        log.warning("pii_agent.failed_soft", error=str(exc))
        return {"findings": []}

    chunk_index = {c.id: c for c in chunks}
    for v in out.get("verified", []):
        chunk_opt = chunk_index.get(v.get("chunk_id"))
        if chunk_opt is None:
            continue
        chunk = chunk_opt
        f = Finding(
            id=f"f-{uuid.uuid4().hex[:8]}",
            severity="FAIL",
            rule_id=f"PII-{v.get('pii_type', 'unknown').upper()}",
            policy_ref=PolicyRef(
                id="GDPR-Art-5",
                policy_id="IT_GDPR_2026",
                version="3.0.0",
                title="Minimizzazione dati personali",
                excerpt="I dati personali devono essere adeguati, pertinenti e limitati a quanto necessario.",
            ),
            evidence=_build_citation(chunk, v, spans),
            explanation=f"Rilevato dato personale ({v.get('pii_type')}) non mascherato: {v.get('value_masked', '***')}",
            suggestion="Rimuovere o pseudonimizzare il dato personale.",
            confidence=float(v.get("confidence", 0.9)),
            reasoning=[
                ReasoningStep(
                    step=1,
                    agent="PIIDetectorAgent",
                    action="regex_match",
                    output={"type": v.get("pii_type")},
                ),
                ReasoningStep(
                    step=2,
                    agent="PIIDetectorAgent",
                    action="llm_verify",
                    output={"reason": v.get("reason", "")},
                ),
            ],
        )
        findings.append(f)
        await emit_finding(state, f)

    return {"findings": findings}


def _build_citation(
    chunk: Chunk, v: dict[str, Any], spans: dict[tuple[str, str], tuple[int, int]]
) -> Citation:
    pii_type = v.get("pii_type") or v.get("type") or ""
    span = spans.get((chunk.id, pii_type))
    match_start, match_end, snippet = None, None, None
    if span is not None:
        match_start, match_end = span
        pad_lo = max(0, match_start - 80)
        pad_hi = min(len(chunk.text), match_end + 80)
        snippet = chunk.text[pad_lo:pad_hi]
    return Citation(
        chunk_id=chunk.id,
        page=chunk.page,
        line_start=v.get("line", chunk.line_start),
        line_end=chunk.line_end,
        bbox=chunk.bbox,
        text=chunk.text,
        match_start=match_start,
        match_end=match_end,
        snippet=snippet,
    )
