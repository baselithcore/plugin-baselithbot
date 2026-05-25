"""LLM-driven finding triage.

Adds a post-scanner pass that re-evaluates each finding against the
target context and the scanner-supplied evidence. Operates in batches
so the LLM round-trip cost is amortized across multiple findings.

Design invariants:

- **Fail-open**: every error path (LLM unavailable, JSON parse failure,
  schema mismatch) returns the input findings untouched. The
  deterministic scan flow is never blocked by an ML failure.
- **Auditability**: every verdict is appended to ``finding.evidence``
  under the ``triage_llm`` key — model id, verdict, confidence,
  rationale, optional severity override. The original severity is
  preserved as ``triage_llm.original_severity`` when overridden.
- **Bounded mutation**: severity is overridden only when the LLM
  confidence meets ``min_confidence_to_override``. False-positive drops
  follow the same rule and require ``drop_false_positives=True``.
- **No side effects**: this service does not touch the graph, the
  database, or the audit log. Callers wire those in.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Protocol

from core.observability.logging import get_logger
from plugins.red_agent.ml.prompts import (
    TRIAGE_SYSTEM_PROMPT,
    build_triage_user_prompt,
)
from plugins.red_agent.models import Finding, Severity, Target

logger = get_logger(__name__)


class _LLMLike(Protocol):
    """Subset of :class:`core.services.llm.service.LLMService` we depend on.

    Decouples triage from the concrete LLM service so tests can pass a
    minimal stub without instantiating the full provider stack.
    """

    async def generate_response(
        self,
        prompt: str,
        model: str | None = None,
        json: bool = False,
        system_prompt: str | None = None,
    ) -> str: ...


@dataclass(slots=True)
class TriageVerdict:
    """Structured verdict from the LLM for a single finding."""

    finding_id: str
    verdict: str
    severity: Severity | None
    confidence: float
    rationale: str
    remediation: str

    def as_evidence(self, model: str) -> dict[str, Any]:
        """Serialize for storage under ``Finding.evidence['triage_llm']``."""
        return {
            "model": model,
            "verdict": self.verdict,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "severity_proposed": self.severity.value if self.severity else None,
            "remediation_proposed": self.remediation or None,
        }


class LLMTriageService:
    """Optional LLM enrichment pass over a list of :class:`Finding`."""

    _VERDICTS = frozenset(
        {"confirmed", "likely_true", "false_positive", "insufficient_evidence"}
    )

    def __init__(
        self,
        *,
        llm: _LLMLike | None,
        model: str,
        enabled: bool,
        batch_size: int = 5,
        drop_false_positives: bool = True,
        min_confidence_to_override: float = 0.8,
    ) -> None:
        self._llm = llm
        self._model = model
        self._enabled = enabled and llm is not None
        self._batch_size = max(1, batch_size)
        self._drop_false_positives = drop_false_positives
        self._min_confidence = min_confidence_to_override

    @property
    def enabled(self) -> bool:
        return self._enabled

    async def triage(self, findings: list[Finding], target: Target) -> list[Finding]:
        """Re-evaluate ``findings`` and return the (possibly mutated) list."""
        if not self._enabled or not findings:
            return findings

        # Skip findings that already carry a synthetic scanner-failure marker
        # — they are diagnostics, not vulnerabilities. Triaging them wastes
        # tokens and risks the LLM "validating" a scanner crash.
        triageable = [f for f in findings if not _is_scanner_error(f)]
        passthrough = [f for f in findings if _is_scanner_error(f)]
        if not triageable:
            return findings

        verdicts: dict[str, TriageVerdict] = {}
        for batch in _chunked(triageable, self._batch_size):
            batch_verdicts = await self._triage_batch(batch, target)
            verdicts.update(batch_verdicts)

        return passthrough + self._apply_verdicts(triageable, verdicts)

    async def _triage_batch(
        self, batch: list[Finding], target: Target
    ) -> dict[str, TriageVerdict]:
        try:
            payload = json.dumps(
                [_summarize_finding(f) for f in batch],
                default=str,
            )
            user_prompt = build_triage_user_prompt(payload, target.value)
            assert self._llm is not None  # narrowed by self._enabled
            raw = await self._llm.generate_response(
                prompt=user_prompt,
                model=self._model,
                json=True,
                system_prompt=TRIAGE_SYSTEM_PROMPT,
            )
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.triage.llm_call_failed",
                extra={"err": str(e), "batch_size": len(batch)},
            )
            return {}

        return self._parse_verdicts(raw, expected_ids={str(f.id) for f in batch})

    def _parse_verdicts(
        self, raw: str, expected_ids: set[str]
    ) -> dict[str, TriageVerdict]:
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(
                "red_agent.triage.parse_failed", extra={"raw_head": raw[:200]}
            )
            return {}

        triages = data.get("triages") if isinstance(data, dict) else None
        if not isinstance(triages, list):
            logger.warning("red_agent.triage.schema_mismatch")
            return {}

        out: dict[str, TriageVerdict] = {}
        for entry in triages:
            verdict = self._coerce_verdict(entry, expected_ids)
            if verdict is not None:
                out[verdict.finding_id] = verdict
        return out

    def _coerce_verdict(
        self, entry: Any, expected_ids: set[str]
    ) -> TriageVerdict | None:
        if not isinstance(entry, dict):
            return None
        fid = str(entry.get("finding_id") or "")
        if not fid or fid not in expected_ids:
            return None
        verdict_str = str(entry.get("verdict") or "").lower().strip()
        if verdict_str not in self._VERDICTS:
            return None
        severity = _coerce_severity(entry.get("severity"))
        try:
            confidence = float(entry.get("confidence", 0.0))
        except (TypeError, ValueError):
            confidence = 0.0
        confidence = max(0.0, min(1.0, confidence))
        rationale = str(entry.get("rationale") or "")[:1000]
        remediation = str(entry.get("remediation") or "")[:2000]
        return TriageVerdict(
            finding_id=fid,
            verdict=verdict_str,
            severity=severity,
            confidence=confidence,
            rationale=rationale,
            remediation=remediation,
        )

    def _apply_verdicts(
        self,
        findings: list[Finding],
        verdicts: dict[str, TriageVerdict],
    ) -> list[Finding]:
        kept: list[Finding] = []
        for f in findings:
            v = verdicts.get(str(f.id))
            if v is None:
                kept.append(f)
                continue

            if (
                v.verdict == "false_positive"
                and self._drop_false_positives
                and v.confidence >= self._min_confidence
            ):
                logger.info(
                    "red_agent.triage.drop_false_positive",
                    extra={
                        "finding_id": str(f.id),
                        "scanner": f.scanner,
                        "confidence": v.confidence,
                    },
                )
                continue

            mutated = _annotate_finding(f, v, self._model, self._min_confidence)
            kept.append(mutated)
        return kept


def _summarize_finding(f: Finding) -> dict[str, Any]:
    """Compact view of a finding sent to the LLM.

    Strips raw scanner blobs (kept in the persisted finding for forensic
    use) so the prompt fits within a small context window even for big
    nuclei runs. The fields below are the ones the LLM actually needs to
    classify the finding.
    """
    evidence_summary: dict[str, Any] = {}
    if isinstance(f.evidence, dict):
        for key in ("matched", "extracted_results", "matcher_name", "confirmed"):
            if key in f.evidence:
                evidence_summary[key] = f.evidence[key]
    return {
        "finding_id": str(f.id),
        "scanner": f.scanner,
        "title": f.title,
        "description": f.description[:500],
        "severity": f.severity.value,
        "cvss_score": f.cvss_score,
        "cwe": f.cwe,
        "cve": f.cve,
        "endpoint": f.endpoint,
        "port": f.port,
        "service": f.service,
        "evidence": evidence_summary,
    }


def _annotate_finding(
    f: Finding, v: TriageVerdict, model: str, min_confidence: float
) -> Finding:
    new_evidence = dict(f.evidence) if isinstance(f.evidence, dict) else {}
    triage_payload = v.as_evidence(model)

    new_severity = f.severity
    if (
        v.severity is not None
        and v.severity != f.severity
        and v.confidence >= min_confidence
    ):
        triage_payload["original_severity"] = f.severity.value
        new_severity = v.severity

    new_evidence["triage_llm"] = triage_payload

    update: dict[str, Any] = {"evidence": new_evidence, "severity": new_severity}
    if not f.remediation and v.remediation and v.confidence >= min_confidence:
        update["remediation"] = v.remediation
    return f.model_copy(update=update)


def _is_scanner_error(f: Finding) -> bool:
    return isinstance(f.evidence, dict) and bool(f.evidence.get("scanner_failure"))


def _coerce_severity(value: Any) -> Severity | None:
    if not isinstance(value, str):
        return None
    try:
        return Severity(value.lower().strip())
    except ValueError:
        return None


def _chunked(items: list[Finding], size: int) -> list[list[Finding]]:
    return [items[i : i + size] for i in range(0, len(items), size)]
