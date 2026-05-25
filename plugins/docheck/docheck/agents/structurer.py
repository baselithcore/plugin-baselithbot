"""StructurerAgent — extracts hierarchical document structure via LLM.

Node-type taxonomy is selected per DocType (ADR-0011); the prompt is rendered
dynamically using `core.doc_taxonomy.node_types_for(doc_type)`.
"""

from ..core.doc_taxonomy import DocType, coerce_doc_type, node_types_for
from ..core.logging import log
from ..schemas.state import CheckState, StructureNode
from ..services.llm import chat_json_resilient
from ._emit import emit_phase_progress

SYSTEM_PROMPT = """You extract hierarchical structure from enterprise documents.

DOMAIN: any compliance-relevant document (contracts, internal policies, procedures,
DPIA, audit reports, manuals, technical specs, regulatory texts). Italian/EU first,
multilingual supported. Detected document type for THIS document: "{doc_type}".

NODE TYPES (use ONLY these strings, valid for doc_type "{doc_type}"):
{node_types_block}

GENERIC PATTERNS to recognize (where applicable):
- "Art. N" / "Articolo N" → article
- "N.N" / "comma N" → clause
- "Allegato A/B" / "Appendice" → section
- "Premesso che" / "Considerato che" → section
- numbered step ("1.", "Step 1") → step (procedures/manuals)
- "Control C-N" / "ID Control" → control (audit_report)
- "Processing activity", "Trattamento" → processing_activity (dpia)

HARD RULES:
1. STRICT JSON only. No prose. No markdown.
2. PRESERVE chunk spans verbatim (page, line_start, line_end from input).
3. parent_id MUST reference an `id` previously emitted (or null for roots).
4. Each node MUST list at least one chunk_id from input.
5. `type` MUST be one of the allowed strings listed above. Anything else is rejected.
6. If document language unclear, default to "{lang}".

Output language: {lang}.
"""


def _render_node_types(types: tuple[str, ...]) -> str:
    return "\n".join(f'- "{t}"' for t in types)


async def run(state: CheckState) -> CheckState:
    await emit_phase_progress(state, "structurer")
    chunks = state.get("chunks", [])
    if not chunks:
        return state

    doc_type = coerce_doc_type(state.get("doc_type") or DocType.OTHER.value)
    allowed_types = node_types_for(doc_type)

    chunks_payload = [
        {
            "id": c.id,
            "page": c.page,
            "line_start": c.line_start,
            "line_end": c.line_end,
            "text": c.text[:600],
        }
        for c in chunks
    ]

    allowed_types_csv = ", ".join(allowed_types)
    user = (
        "Extract hierarchical structure of this document.\n"
        f"Allowed node types for doc_type={doc_type.value}: {allowed_types_csv}.\n"
        "For each node return: {id, type, label, parent_id, page, line_start, line_end, chunk_ids[]}.\n\n"
        f"Chunks: {chunks_payload}\n\n"
        'Output: {"structure":[...]}'
    )
    sys = SYSTEM_PROMPT.format(
        lang=state.get("lang", "it"),
        doc_type=doc_type.value,
        node_types_block=_render_node_types(allowed_types),
    )

    doc_id = state.get("doc_id")
    try:
        out = await chat_json_resilient(system=sys, user=user, max_tokens=8192)
    except Exception as exc:
        log.warning(
            "structurer.failed_soft",
            doc_id=doc_id,
            chunks=len(chunks),
            lang=state.get("lang"),
            error_type=type(exc).__name__,
            error=str(exc),
        )
        return {"structure": []}

    nodes: list[StructureNode] = []
    invalid = 0
    allowed_set = set(allowed_types)
    for raw in out.get("structure", []):
        try:
            node = StructureNode(**raw)
        except Exception as exc:
            invalid += 1
            log.warning(
                "structurer.invalid_node", doc_id=doc_id, error=str(exc), raw=raw
            )
            continue
        if node.type not in allowed_set:
            invalid += 1
            log.warning(
                "structurer.rejected_node_type",
                doc_id=doc_id,
                doc_type=doc_type.value,
                node_type=node.type,
            )
            continue
        nodes.append(node)

    log.info(
        "structurer.done",
        doc_id=doc_id,
        doc_type=doc_type.value,
        nodes=len(nodes),
        invalid_nodes=invalid,
        chunks=len(chunks),
    )
    return {"structure": nodes}
