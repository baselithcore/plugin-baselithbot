"""Report executive summary endpoint with deterministic failover."""

import json
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.logging import log
from ..core.security import Principal
from ..db import get_session
from ..services import audit, llm
from .deps import require
from .findings import _load_report

router = APIRouter()


Locale = Literal["it", "en", "fr"]
SUPPORTED_LOCALES: set[str] = {"it", "en", "fr"}
_LOCALE_NAME: dict[str, str] = {"it": "Italian", "en": "English", "fr": "French"}


def _summary_system(locale: str) -> str:
    lang = _LOCALE_NAME.get(locale, "Italian")
    return (
        "You are a senior compliance reviewer. Produce an executive judgment of the scan "
        "GROUNDED in the supplied report context — never invent findings, scores, or policies "
        "not present in the input.\n\n"
        "REQUIREMENTS:\n"
        "1. Reference applied policies by id/title; if multiple policies were applied, "
        "   acknowledge the breadth of coverage.\n"
        "2. Differentiate the assessment by ACTUAL findings: cite specific rule_ids and "
        "   chunks. Do NOT produce boilerplate that ignores the input.\n"
        "3. `top_risks` MUST cite the specific findings (rule_id + brief impact), not generic "
        "   compliance themes.\n"
        "4. `next_steps` MUST be actionable and tied to the reported findings or coverage gaps.\n"
        "5. If `findings_total == 0`, headline=verdict reflects clean scan; risks=[] and "
        "   next_steps focus on monitoring/expansion of policy coverage.\n"
        "6. Verdict choice:\n"
        "   - critical: any FAIL severity present\n"
        "   - attention: only WARN/INFO severities, score < 90\n"
        "   - compliant: zero FAIL/WARN, score >= 90\n\n"
        'Respond STRICT JSON ONLY: {"verdict": "compliant|attention|critical", '
        '"headline": "one short sentence reflecting actual findings", '
        '"assessment": "2-4 sentences citing specific rules/policies", '
        '"top_risks": ["risk tied to rule_id ...", "..."], '
        '"next_steps": ["actionable step ...", "..."]}. '
        f"Write `headline`, `assessment`, `top_risks`, `next_steps` in {lang} ({locale}). "
        "Keep the `verdict` keyword and rule_ids/policy_ids unchanged."
    )


_DET_MSG: dict[str, dict[str, str]] = {
    "it": {
        "headline_critical": "{fail} rilievi bloccanti — richiesta remediation prima dell'approvazione.",
        "headline_attention": "{warn} avviso/i rilevati — revisione consigliata.",
        "headline_compliant": "Nessun rilievo bloccante rispetto alle policy applicate.",
        "assessment": (
            "Scan ha valutato {chunks} chunk contro {npol} policy producendo {total} "
            "rilievi (FAIL={fail}, WARN={warn}). Riepilogo deterministico (verdetto LLM non disponibile)."
        ),
        "risk_fmt": "{rule} ({sev}): {expl}",
        "step_fmt": "Risolvere regola {rule} a pagina {page}.",
        "step_default": "Rivedere i WARN e confermare la copertura delle policy applicate.",
    },
    "en": {
        "headline_critical": "{fail} blocking finding(s) — remediation required before sign-off.",
        "headline_attention": "{warn} warning(s) detected — review recommended.",
        "headline_compliant": "No blocking issues detected across applied policies.",
        "assessment": (
            "Scan evaluated {chunks} chunk(s) against {npol} policy/policies and produced {total} "
            "finding(s) (FAIL={fail}, WARN={warn}). Deterministic summary (LLM verdict unavailable)."
        ),
        "risk_fmt": "{rule} ({sev}): {expl}",
        "step_fmt": "Address rule {rule} on page {page}.",
        "step_default": "Review WARN findings and confirm scope of applied policies.",
    },
    "fr": {
        "headline_critical": "{fail} constat(s) bloquant(s) — remédiation requise avant validation.",
        "headline_attention": "{warn} avertissement(s) détecté(s) — révision recommandée.",
        "headline_compliant": "Aucun problème bloquant détecté pour les politiques appliquées.",
        "assessment": (
            "Le scan a évalué {chunks} segment(s) face à {npol} politique(s) et produit {total} "
            "constat(s) (FAIL={fail}, WARN={warn}). Résumé déterministe (verdict LLM indisponible)."
        ),
        "risk_fmt": "{rule} ({sev}) : {expl}",
        "step_fmt": "Traiter la règle {rule} en page {page}.",
        "step_default": "Examiner les WARN et confirmer la portée des politiques appliquées.",
    },
}


def _deterministic_summary(context: dict[str, Any], top: list[dict[str, Any]], locale: str = "it") -> dict[str, Any]:
    """Failover summary built from severity counts when LLM/JSON fails.

    Per CLAUDE.md §5: glass-box requires never showing 'verdict unavailable'
    when the underlying data is sufficient to compute a deterministic verdict.
    """
    msg = _DET_MSG.get(locale, _DET_MSG["it"])
    by_sev = context.get("by_severity") or {}
    fail = int(by_sev.get("FAIL", 0) or 0)
    warn = int(by_sev.get("WARN", 0) or 0)
    score = context.get("score") or 0
    total = int(context.get("findings_total") or 0)

    if fail > 0:
        verdict = "critical"
        headline = msg["headline_critical"].format(fail=fail)
    elif warn > 0 or (isinstance(score, int | float) and score < 90):
        verdict = "attention"
        headline = msg["headline_attention"].format(warn=warn)
    else:
        verdict = "compliant"
        headline = msg["headline_compliant"]

    policies = context.get("policies_applied") or []
    chunks = context.get("chunks_evaluated") or 0
    assessment = msg["assessment"].format(chunks=chunks, npol=len(policies), total=total, fail=fail, warn=warn)
    top_risks = [
        msg["risk_fmt"].format(
            rule=f.get("rule_id"),
            sev=f.get("severity"),
            expl=(f.get("explanation") or "")[:160],
        )
        for f in top
        if f.get("severity") in {"FAIL", "WARN"}
    ][:5]
    next_steps = [
        msg["step_fmt"].format(rule=f.get("rule_id"), page=f.get("page")) for f in top if f.get("severity") == "FAIL"
    ][:5] or [msg["step_default"]]

    return {
        "verdict": verdict,
        "headline": headline,
        "assessment": assessment,
        "top_risks": top_risks,
        "next_steps": next_steps,
    }


@router.post("/reports/{report_id}/summary")
async def report_summary(
    report_id: str,
    locale: str = Query("it", pattern="^(it|en|fr)$"),
    principal: Principal = Depends(require("document", "read")),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    if locale not in SUPPORTED_LOCALES:
        locale = "it"
    rep = await _load_report(db, report_id, principal.user_id)
    payload = json.loads(rep.payload)

    findings = payload.get("findings", []) or []
    sev_rank = {"FAIL": 0, "WARN": 1, "INFO": 2, "PASS": 3}
    findings_sorted = sorted(
        findings,
        key=lambda f: (
            sev_rank.get(f.get("severity", "INFO"), 9),
            -float(f.get("confidence") or 0),
        ),
    )
    top: list[dict[str, Any]] = []
    for f in findings_sorted[:8]:
        top.append(
            {
                "severity": f.get("severity"),
                "rule_id": f.get("rule_id"),
                "policy_id": (f.get("policy_ref") or {}).get("policy_id"),
                "policy_title": (f.get("policy_ref") or {}).get("title"),
                "policy_excerpt": (f.get("policy_ref") or {}).get("excerpt"),
                "chunk_id": (f.get("evidence") or {}).get("chunk_id"),
                "page": (f.get("evidence") or {}).get("page"),
                "explanation": f.get("explanation"),
                "suggestion": f.get("suggestion"),
                "confidence": f.get("confidence"),
            }
        )

    by_policy: dict[str, dict[str, Any]] = {}
    for f in findings:
        pid = (f.get("policy_ref") or {}).get("policy_id") or "unknown"
        slot = by_policy.setdefault(
            pid,
            {
                "policy_id": pid,
                "title": (f.get("policy_ref") or {}).get("title"),
                "FAIL": 0,
                "WARN": 0,
                "INFO": 0,
                "PASS": 0,
                "rule_ids": set(),
            },
        )
        sev = f.get("severity") or "INFO"
        slot[sev] = slot.get(sev, 0) + 1
        slot["rule_ids"].add(f.get("rule_id"))
    by_policy_serialized = [{**v, "rule_ids": sorted(x for x in v["rule_ids"] if x)} for v in by_policy.values()]

    context = {
        "score": payload.get("score"),
        "by_severity": payload.get("by_severity", {}),
        "policies_applied": payload.get("policies_applied", []),
        "by_policy": by_policy_serialized,
        "chunks_evaluated": payload.get("chunks_evaluated"),
        "findings_total": len(findings),
        "top_findings": top,
    }

    user_prompt = "Report context (JSON):\n" + json.dumps(context, ensure_ascii=False)

    fallback_used = False
    try:
        result = await llm.chat_json_resilient(
            system=_summary_system(locale),
            user=user_prompt,
            max_tokens=2000,
            temperature=0.0,
        )
    except Exception as exc:
        log.warning("report.summary.llm_failed", report_id=report_id, error=str(exc)[:300])
        result = _deterministic_summary(context, top, locale)
        fallback_used = True

    verdict = str(result.get("verdict", "")).strip().lower() or "attention"
    if verdict not in {"compliant", "attention", "critical"}:
        verdict = "attention"
    headline = str(result.get("headline", "")).strip()
    assessment = str(result.get("assessment", "")).strip()
    top_risks = [str(x) for x in (result.get("top_risks") or []) if str(x).strip()]
    next_steps = [str(x) for x in (result.get("next_steps") or []) if str(x).strip()]

    await audit.append_audit(
        db,
        action="report.summary",
        user_id=principal.user_id,
        resource=f"report:{report_id}",
        payload={"verdict": verdict, "locale": locale},
    )

    return {
        "report_id": report_id,
        "verdict": verdict,
        "headline": headline,
        "assessment": assessment,
        "top_risks": top_risks,
        "next_steps": next_steps,
        "score": payload.get("score"),
        "fallback": fallback_used,
    }
