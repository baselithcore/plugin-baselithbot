"""Per-finding actions: triage decision (accept/reject/mute) + grounded Q&A."""

import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.logging import log
from ..core.security import Principal
from ..db import get_session
from ..db.models import FindingDecision, Report
from ..services import audit, llm
from .deps import require

router = APIRouter()


class DecisionIn(BaseModel):
    decision: str = Field(pattern="^(accepted|rejected|muted)$")
    note: str | None = None


class AskIn(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


def _payload_finding(report_payload: dict[str, Any], finding_id: str) -> dict[str, Any] | None:
    for f in report_payload.get("findings", []):
        if f.get("id") == finding_id:
            result: dict[str, Any] = f
            return result
    return None


async def _load_report(db: AsyncSession, report_id: str, user_id: str) -> Report:
    rep = await db.get(Report, report_id)
    if rep is None or rep.user_id != user_id:
        raise HTTPException(404, "Report not found")
    return rep


@router.get("/reports/{report_id}")
async def get_report(
    report_id: str,
    principal: Principal = Depends(require("document", "read")),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    """Return full persisted report payload (findings + signature) by report_id.

    Enables the UI to re-open a historical scan from the Documents tab and
    rehydrate the workspace view (findings, evidence, score) without re-running
    the pipeline.
    """
    rep = await _load_report(db, report_id, principal.user_id)
    payload = json.loads(rep.payload)
    if not isinstance(payload, dict):
        raise HTTPException(500, "Invalid report payload")
    payload["signature"] = rep.signature
    res: dict[str, Any] = payload
    return res


@router.get("/reports/{report_id}/findings/{finding_id}/decision")
async def get_decision(
    report_id: str,
    finding_id: str,
    principal: Principal = Depends(require("document", "read")),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    await _load_report(db, report_id, principal.user_id)
    row = await db.get(FindingDecision, (report_id, finding_id))
    if row is None:
        return {"decision": None}
    return {
        "decision": row.decision,
        "note": row.note,
        "user_id": row.user_id,
        "decided_at": row.decided_at.isoformat(),
    }


@router.post("/reports/{report_id}/findings/{finding_id}/decision")
async def set_decision(
    report_id: str,
    finding_id: str,
    body: DecisionIn,
    principal: Principal = Depends(require("document", "write")),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    rep = await _load_report(db, report_id, principal.user_id)
    payload = json.loads(rep.payload)
    if _payload_finding(payload, finding_id) is None:
        raise HTTPException(404, "Finding not found in report")

    existing = await db.get(FindingDecision, (report_id, finding_id))
    if existing is None:
        db.add(
            FindingDecision(
                report_id=report_id,
                finding_id=finding_id,
                decision=body.decision,
                note=body.note,
                user_id=principal.user_id,
            )
        )
    else:
        existing.decision = body.decision
        existing.note = body.note
        existing.user_id = principal.user_id
    await db.commit()

    await audit.append_audit(
        db,
        action="finding.decision",
        user_id=principal.user_id,
        resource=f"finding:{report_id}:{finding_id}",
        payload={"decision": body.decision, "note": body.note},
    )

    return {"ok": True, "decision": body.decision}


@router.get("/reports/{report_id}/decisions")
async def list_decisions(
    report_id: str,
    principal: Principal = Depends(require("document", "read")),
    db: AsyncSession = Depends(get_session),
) -> dict[str, dict[str, Any]]:
    await _load_report(db, report_id, principal.user_id)
    rows = (await db.execute(select(FindingDecision).where(FindingDecision.report_id == report_id))).scalars().all()
    return {
        r.finding_id: {
            "decision": r.decision,
            "note": r.note,
            "decided_at": r.decided_at.isoformat(),
        }
        for r in rows
    }


_ASK_SYSTEM = (
    "You are a glass-box compliance assistant. Answer briefly (max 6 sentences) "
    "using ONLY the provided finding context: explanation, evidence excerpt, policy excerpt, "
    "reasoning chain. If the question is outside this scope or the context lacks the answer, "
    'say so explicitly. Respond strictly as JSON: {"answer": "...", "grounded": true|false}. '
    "Match the question's language."
)


@router.post("/reports/{report_id}/findings/{finding_id}/ask")
async def ask_finding(
    report_id: str,
    finding_id: str,
    body: AskIn,
    principal: Principal = Depends(require("document", "read")),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    rep = await _load_report(db, report_id, principal.user_id)
    payload = json.loads(rep.payload)
    finding = _payload_finding(payload, finding_id)
    if finding is None:
        raise HTTPException(404, "Finding not found in report")

    context = {
        "rule_id": finding.get("rule_id"),
        "severity": finding.get("severity"),
        "explanation": finding.get("explanation"),
        "suggestion": finding.get("suggestion"),
        "evidence_excerpt": (finding.get("evidence") or {}).get("text"),
        "policy_id": (finding.get("policy_ref") or {}).get("policy_id"),
        "policy_excerpt": (finding.get("policy_ref") or {}).get("excerpt"),
        "reasoning": finding.get("reasoning"),
    }
    user_prompt = (
        "Question:\n"
        + body.question.strip()
        + "\n\nFinding context (JSON):\n"
        + json.dumps(context, ensure_ascii=False)
    )

    try:
        result = await llm.chat_json_resilient(
            system=_ASK_SYSTEM,
            user=user_prompt,
            max_tokens=1024,
            temperature=0.1,
        )
    except Exception as exc:
        log.warning(
            "finding.ask.llm_failed",
            report_id=report_id,
            finding_id=finding_id,
            error=str(exc)[:300],
        )
        # Failover: never strand the user with a 502 — return a graceful,
        # non-grounded message that explains the model is unavailable.
        return {
            "answer": (
                "Il modello locale non è disponibile o ha restituito una risposta "
                "non valida. Riprova tra qualche istante o consulta direttamente "
                "l'estratto policy e l'evidenza nel pannello di contesto."
            ),
            "grounded": False,
        }

    answer = str(result.get("answer", "")).strip()
    grounded = bool(result.get("grounded", False))

    await audit.append_audit(
        db,
        action="finding.ask",
        user_id=principal.user_id,
        resource=f"finding:{report_id}:{finding_id}",
        payload={"question_hash": str(hash(body.question))},
    )

    return {"answer": answer, "grounded": grounded}


_ASK_STREAM_SYSTEM = (
    "You are a glass-box compliance assistant. Answer briefly (max 6 sentences) "
    "using ONLY the provided finding context: explanation, evidence excerpt, policy excerpt, "
    "reasoning chain. If the question is outside this scope or the context lacks the answer, "
    "say so explicitly. Reply in plain text (no JSON, no markdown headers). "
    "Match the question's language."
)


def _heuristic_grounded(answer: str, context: dict[str, Any]) -> bool:
    """Lightweight grounding check: any non-trivial substring from policy or
    evidence excerpt appears in the answer. Cheap, no extra LLM call.
    """
    if not answer or len(answer) < 10:
        return False
    a = answer.lower()
    for key in ("policy_excerpt", "evidence_excerpt", "explanation"):
        src = (context.get(key) or "").lower()
        if not src:
            continue
        # match any 12+ char window from the source.
        for token in src.split():
            if len(token) >= 12 and token in a:
                return True
        # fallback: split into 18-char windows.
        for i in range(0, max(0, len(src) - 18), 18):
            chunk = src[i : i + 18].strip()
            if len(chunk) >= 12 and chunk in a:
                return True
    rule_id = (context.get("rule_id") or "").lower()
    return bool(rule_id and rule_id in a)


@router.post("/reports/{report_id}/findings/{finding_id}/ask/stream")
async def ask_finding_stream(
    report_id: str,
    finding_id: str,
    body: AskIn,
    principal: Principal = Depends(require("document", "read")),
    db: AsyncSession = Depends(get_session),
) -> StreamingResponse:
    """NDJSON stream of LLM tokens for the finding Q&A.

    Frame format (one JSON object per line):
      {"type":"token","text":"..."}
      {"type":"done","grounded":true,"answer":"<full text>"}
      {"type":"error","message":"..."}
    """
    rep = await _load_report(db, report_id, principal.user_id)
    payload = json.loads(rep.payload)
    finding = _payload_finding(payload, finding_id)
    if finding is None:
        raise HTTPException(404, "Finding not found in report")

    context = {
        "rule_id": finding.get("rule_id"),
        "severity": finding.get("severity"),
        "explanation": finding.get("explanation"),
        "suggestion": finding.get("suggestion"),
        "evidence_excerpt": (finding.get("evidence") or {}).get("text"),
        "policy_id": (finding.get("policy_ref") or {}).get("policy_id"),
        "policy_excerpt": (finding.get("policy_ref") or {}).get("excerpt"),
        "reasoning": finding.get("reasoning"),
    }
    user_prompt = (
        "Question:\n"
        + body.question.strip()
        + "\n\nFinding context (JSON):\n"
        + json.dumps(context, ensure_ascii=False)
    )
    question_hash = str(hash(body.question))

    async def gen() -> Any:
        accum: list[str] = []
        try:
            async for delta in llm.chat_text_stream(
                system=_ASK_STREAM_SYSTEM,
                user=user_prompt,
                max_tokens=1024,
                temperature=0.1,
            ):
                accum.append(delta)
                yield (json.dumps({"type": "token", "text": delta}, ensure_ascii=False) + "\n")
        except Exception as exc:
            log.warning(
                "finding.ask_stream.llm_failed",
                report_id=report_id,
                finding_id=finding_id,
                error=str(exc)[:300],
            )
            yield (
                json.dumps(
                    {
                        "type": "error",
                        "message": "Modello locale non disponibile. Riprova o consulta il pannello di contesto.",
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
            return

        full = "".join(accum).strip()
        grounded = _heuristic_grounded(full, context)
        # Audit log on completion (best-effort; not fatal if it fails).
        try:
            await audit.append_audit(
                db,
                action="finding.ask",
                user_id=principal.user_id,
                resource=f"finding:{report_id}:{finding_id}",
                payload={"question_hash": question_hash, "stream": True},
            )
        except Exception:
            log.warning("finding.ask_stream.audit_failed", report_id=report_id)
        yield (
            json.dumps(
                {"type": "done", "grounded": grounded, "answer": full},
                ensure_ascii=False,
            )
            + "\n"
        )

    return StreamingResponse(
        gen(),
        media_type="application/x-ndjson",
        headers={"Cache-Control": "no-cache, no-transform", "X-Accel-Buffering": "no"},
    )
