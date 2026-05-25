"""ClassifierAgent — assigns DocType before structuring (ADR-0011).

LLM zero-shot classification on a head sample of chunks. Emits doc_type +
confidence into state. Below LOW_CONFIDENCE_THRESHOLD → fallback to OTHER
with low_confidence flag (eligible for HITL review).
"""

from ..core.doc_taxonomy import (
    ALL_DOC_TYPES,
    LOW_CONFIDENCE_THRESHOLD,
    DocType,
    coerce_doc_type,
)
from ..core.logging import log
from ..schemas.state import CheckState
from ..services.llm import chat_json_resilient
from ._emit import emit_phase_progress

SYSTEM_PROMPT = """You classify enterprise documents for compliance review.

Pick exactly ONE doc_type from this closed set:
{types}

Definitions:
- contract: contracts, NDAs, MSAs, supplier/employment/DPA agreements with two parties.
- policy: internal policies, codes of conduct, regolamenti aziendali.
- procedure: SOPs, operational manuals, runbooks, step-by-step processes.
- dpia: DPIA / PIA, data protection impact assessments, privacy risk reports.
- audit_report: audit reports, certifications, attestations, assessment results.
- manual: end-user manuals, technical guides written for human readers.
- technical_spec: technical specifications, design docs, RFCs, requirement specs.
- regulatory_text: laws, regulations, standards (GDPR, ISO 27001 text, etc.).
- other: cannot confidently fit above.

HARD RULES:
1. STRICT JSON only. No prose. No markdown.
2. Output schema: {{"doc_type": <one of the closed set>, "confidence": <float 0..1>,
   "rationale": <short string, language={lang}>}}.
3. confidence reflects calibrated certainty. If unsure (<0.55), still pick best guess;
   downstream will downgrade to "other".
4. rationale: 1-2 sentences, cite a SPECIFIC textual cue from the sample.
"""

# Number of leading chunks to feed the classifier. Heuristic head sample.
HEAD_CHUNKS = 6
MAX_CHARS_PER_CHUNK = 800


async def run(state: CheckState) -> CheckState:
    await emit_phase_progress(state, "classifier")
    chunks = state.get("chunks", [])
    lang = state.get("lang", "it")
    doc_id = state.get("doc_id")

    if not chunks:
        log.info("classifier.skipped_empty", doc_id=doc_id)
        return _result(DocType.OTHER, 0.0, low_conf=True)

    sample = chunks[:HEAD_CHUNKS]
    payload = [
        {
            "id": c.id,
            "page": c.page,
            "text": (c.text or "")[:MAX_CHARS_PER_CHUNK],
        }
        for c in sample
    ]

    sys = SYSTEM_PROMPT.format(types=", ".join(ALL_DOC_TYPES), lang=lang)
    user = (
        "Classify the document type from this head sample.\n"
        f"Sample chunks: {payload}\n\n"
        'Output JSON: {"doc_type": "...", "confidence": 0.0, "rationale": "..."}'
    )

    try:
        out = await chat_json_resilient(system=sys, user=user, max_tokens=512)
    except Exception as exc:
        log.warning(
            "classifier.failed_soft",
            doc_id=doc_id,
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return _result(DocType.OTHER, 0.0, low_conf=True)

    raw_type = str(out.get("doc_type") or "")
    confidence = _safe_float(out.get("confidence"))
    rationale = str(out.get("rationale") or "")[:500]
    detected = coerce_doc_type(raw_type)

    low_conf = confidence < LOW_CONFIDENCE_THRESHOLD or detected is DocType.OTHER
    final = DocType.OTHER if confidence < LOW_CONFIDENCE_THRESHOLD else detected

    log.info(
        "classifier.done",
        doc_id=doc_id,
        detected=detected.value,
        final=final.value,
        confidence=confidence,
        low_confidence=low_conf,
        rationale_head=rationale[:120],
    )
    return _result(final, confidence, low_conf, rationale)


def _safe_float(v: object) -> float:
    try:
        f = float(v)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0.0
    if f < 0.0:
        return 0.0
    if f > 1.0:
        return 1.0
    return f


def _result(doc_type: DocType, confidence: float, low_conf: bool, rationale: str = "") -> CheckState:
    return {
        "doc_type": doc_type.value,
        "doc_type_confidence": confidence,
        "doc_type_low_confidence": low_conf,
        "doc_type_rationale": rationale,
    }
