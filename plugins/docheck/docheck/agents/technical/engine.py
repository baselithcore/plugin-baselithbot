"""TechnicalComplianceAgent graph node.

Orchestrates DocCheck_Builtin deterministic rules. Glass Box: every Finding
returned carries a multi-step reasoning chain produced by the rule itself.
"""

from __future__ import annotations

from ...core.doc_taxonomy import agent_applies
from ...core.logging import log
from ...schemas.finding import Finding
from ...schemas.state import CheckState
from .._emit import emit_finding, emit_phase_progress
from .rules import all_rules


async def run(state: CheckState) -> CheckState:
    await emit_phase_progress(state, "technical")
    doc_type = state.get("doc_type") or "other"
    if not agent_applies("technical", doc_type):
        log.info(
            "technical.skipped_by_doc_type",
            doc_id=state.get("doc_id"),
            doc_type=doc_type,
        )
        return {"findings": []}

    chunks = state.get("chunks", [])
    rules = all_rules()
    findings: list[Finding] = []
    counts: dict[str, int] = {r.spec.rule_id: 0 for r in rules}

    for chunk in chunks:
        for rule in rules:
            try:
                produced = rule.evaluate(chunk)
            except Exception as exc:
                log.warning(
                    "technical.rule_failed",
                    rule_id=rule.spec.rule_id,
                    chunk_id=chunk.id,
                    error=str(exc)[:200],
                )
                continue
            for f in produced:
                findings.append(f)
                counts[rule.spec.rule_id] = counts.get(rule.spec.rule_id, 0) + 1
                await emit_finding(state, f)

    log.info("technical.done", findings=len(findings), per_rule=counts)
    return {"findings": findings}
