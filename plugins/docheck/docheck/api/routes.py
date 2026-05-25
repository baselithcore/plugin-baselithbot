"""HTTP/WS API routes."""

import hashlib
import json as _json
import uuid
from pathlib import Path
from typing import Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    UploadFile,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import FileResponse, Response
from sqlalchemy import delete as sql_delete
from sqlalchemy import desc, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..agents import get_graph
from ..core.config import settings
from ..core.logging import log
from ..core.security import Principal
from ..db import get_session
from ..db.models import Document, DocumentChunk
from ..db.models import Report as ReportRow
from ..schemas.state import CheckState
from ..services import audit, builtin_policy, events, parser
from ..services.signing import public_key_hex, sign_report
from .deps import require

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, Any]:
    return {
        "status": "ok",
        "version": settings.version,
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_primary_model,
        "llm_base_url": settings.llm_base_url,
    }


@router.get("/info/pubkey")
async def pubkey() -> dict[str, str]:
    return {"algorithm": "ed25519", "public_key": public_key_hex()}


@router.get("/documents")
async def list_documents(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    q: str | None = Query(None),
    status: str | None = Query(None),
    principal: Principal = Depends(require("document", "read")),
    db: AsyncSession = Depends(get_session),
) -> Response:
    stmt = select(Document).where(Document.owner_id == principal.user_id)
    cnt_stmt = select(func.count(Document.id)).where(
        Document.owner_id == principal.user_id
    )
    if q:
        like = f"%{q.lower()}%"
        cond = or_(
            func.lower(Document.filename).like(like), func.lower(Document.id).like(like)
        )
        stmt = stmt.where(cond)
        cnt_stmt = cnt_stmt.where(cond)
    if status:
        statuses = [s.strip() for s in status.split(",") if s.strip()]
        if statuses:
            stmt = stmt.where(Document.status.in_(statuses))
            cnt_stmt = cnt_stmt.where(Document.status.in_(statuses))

    total = (await db.execute(cnt_stmt)).scalar_one()
    rows = (
        (
            await db.execute(
                stmt.order_by(desc(Document.uploaded_at)).limit(limit).offset(offset)
            )
        )
        .scalars()
        .all()
    )

    doc_ids = [d.id for d in rows]
    latest_map: dict[str, dict[str, Any]] = {}
    if doc_ids:
        latest_per_doc = (
            await db.execute(
                select(
                    ReportRow.doc_id,
                    func.max(ReportRow.signed_at).label("signed_at"),
                )
                .where(ReportRow.doc_id.in_(doc_ids))
                .group_by(ReportRow.doc_id)
            )
        ).all()
        keys = set(latest_per_doc)
        if keys:
            reports = (
                (
                    await db.execute(
                        select(ReportRow).where(ReportRow.doc_id.in_(doc_ids))
                    )
                )
                .scalars()
                .all()
            )
            for r in reports:
                if (r.doc_id, r.signed_at) in keys:
                    latest_map[r.doc_id] = {
                        "report_id": r.id,
                        "score": r.score,
                        "signed_at": r.signed_at.isoformat(),
                    }

    body = [
        {
            "id": d.id,
            "filename": d.filename,
            "mime_type": d.mime_type,
            "sha256": d.sha256,
            "size_bytes": d.size_bytes,
            "pages": d.pages,
            "lang": d.lang,
            "status": d.status,
            "doc_type": d.doc_type,
            "doc_type_confidence": d.doc_type_confidence,
            "uploaded_at": d.uploaded_at.isoformat(),
            "latest_report": latest_map.get(d.id),
        }
        for d in rows
    ]
    return Response(
        content=_json.dumps(body),
        media_type="application/json",
        headers={"X-Total-Count": str(total)},
    )


@router.get("/documents/{doc_id}")
async def get_document(
    doc_id: str,
    principal: Principal = Depends(require("document", "read")),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    d = await db.get(Document, doc_id)
    if not d or d.owner_id != principal.user_id:
        raise HTTPException(404, "Document not found")
    latest = (
        await db.execute(
            select(ReportRow)
            .where(ReportRow.doc_id == doc_id)
            .order_by(desc(ReportRow.signed_at))
            .limit(1)
        )
    ).scalar_one_or_none()
    return {
        "id": d.id,
        "filename": d.filename,
        "mime_type": d.mime_type,
        "sha256": d.sha256,
        "size_bytes": d.size_bytes,
        "pages": d.pages,
        "lang": d.lang,
        "status": d.status,
        "doc_type": d.doc_type,
        "doc_type_confidence": d.doc_type_confidence,
        "uploaded_at": d.uploaded_at.isoformat(),
        "latest_report": (
            {
                "report_id": latest.id,
                "score": latest.score,
                "signed_at": latest.signed_at.isoformat(),
            }
            if latest
            else None
        ),
    }


@router.get("/documents/{doc_id}/download")
async def download_document(
    doc_id: str,
    principal: Principal = Depends(require("document", "read")),
    db: AsyncSession = Depends(get_session),
) -> FileResponse:
    d = await db.get(Document, doc_id)
    if not d or d.owner_id != principal.user_id:
        raise HTTPException(404, "Document not found")
    storage_path = Path(d.storage_uri.removeprefix("file://"))
    if not storage_path.exists():
        raise HTTPException(410, "Stored file missing")
    return FileResponse(
        path=str(storage_path), media_type=d.mime_type, filename=d.filename
    )


@router.get("/documents/{doc_id}/reports")
async def list_document_reports(
    doc_id: str,
    principal: Principal = Depends(require("document", "read")),
    db: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    d = await db.get(Document, doc_id)
    if not d or d.owner_id != principal.user_id:
        raise HTTPException(404, "Document not found")
    rows = (
        (
            await db.execute(
                select(ReportRow)
                .where(ReportRow.doc_id == doc_id)
                .order_by(desc(ReportRow.signed_at))
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "report_id": r.id,
            "doc_id": r.doc_id,
            "score": r.score,
            "engine_version": r.engine_version,
            "model_id": r.model_id,
            "signed_at": r.signed_at.isoformat(),
        }
        for r in rows
    ]


@router.delete("/documents/{doc_id}")
async def delete_document(
    doc_id: str,
    principal: Principal = Depends(require("document", "write")),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    d = await db.get(Document, doc_id)
    if not d or d.owner_id != principal.user_id:
        raise HTTPException(404, "Document not found")

    sha = d.sha256
    storage_path = Path(d.storage_uri.removeprefix("file://"))

    await db.execute(sql_delete(ReportRow).where(ReportRow.doc_id == doc_id))
    await db.delete(d)
    await db.flush()

    siblings = (
        await db.execute(select(func.count(Document.id)).where(Document.sha256 == sha))
    ).scalar_one()
    if siblings == 0 and storage_path.exists():
        try:
            storage_path.unlink()
        except OSError as exc:
            log.warning("storage.unlink_failed", path=str(storage_path), error=str(exc))

    await audit.append_audit(
        db,
        action="delete",
        user_id=principal.user_id,
        resource=f"document:{doc_id}",
        payload={"sha256": sha, "filename": d.filename},
    )
    await db.commit()
    return {"ok": True, "id": doc_id}


@router.get("/documents/{doc_id}/chunks")
async def get_chunks(
    doc_id: str,
    _: Principal = Depends(require("document", "read")),
    db: AsyncSession = Depends(get_session),
) -> list[dict[str, Any]]:
    rows = (
        (
            await db.execute(
                select(DocumentChunk)
                .where(DocumentChunk.doc_id == doc_id)
                .order_by(DocumentChunk.ord)
            )
        )
        .scalars()
        .all()
    )
    return [
        {
            "id": c.id,
            "page": c.page,
            "line_start": c.line_start,
            "line_end": c.line_end,
            "bbox": c.bbox,
            "text": c.text,
        }
        for c in rows
    ]


@router.post("/documents")
async def upload_document(
    file: UploadFile = File(...),
    principal: Principal = Depends(require("document", "write")),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    if file.size and file.size > 50 * 1024 * 1024:
        raise HTTPException(413, "File too large (max 50MB)")

    settings.docs_dir.mkdir(parents=True, exist_ok=True)
    body = await file.read()
    sha = hashlib.sha256(body).hexdigest()
    storage_path: Path = settings.docs_dir / sha
    storage_path.write_bytes(body)

    doc_id = f"doc-{uuid.uuid4().hex[:12]}"
    doc = Document(
        id=doc_id,
        owner_id=principal.user_id,
        filename=file.filename or "unnamed",
        mime_type=file.content_type or "application/octet-stream",
        sha256=sha,
        size_bytes=len(body),
        storage_uri=f"file://{storage_path}",
        status="uploaded",
    )
    db.add(doc)
    await db.commit()

    await audit.append_audit(
        db,
        action="upload",
        user_id=principal.user_id,
        resource=f"document:{doc_id}",
        payload={"filename": file.filename, "sha256": sha, "size": len(body)},
    )

    return {"id": doc_id, "sha256": sha, "size": len(body)}


@router.post("/documents/{doc_id}/analyze")
async def analyze_document(
    doc_id: str,
    body: dict[str, Any] | None = None,
    principal: Principal = Depends(require("document", "read")),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    from ..db.models import Policy

    doc = await db.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "Document not found")

    body = body or {}
    requested_policies: list[str] = list(body.get("policies") or [])
    lang_override = body.get("lang")
    if lang_override is not None and not isinstance(lang_override, str):
        raise HTTPException(
            422, {"code": "invalid_lang", "message": "lang must be a string"}
        )
    # Auto-select all active policies for the tenant when caller passes none.
    if not requested_policies:
        active_rows = (
            (await db.execute(select(Policy).where(Policy.active == 1))).scalars().all()
        )
        requested_policies = sorted({p.id for p in active_rows})
    if not requested_policies:
        raise HTTPException(
            422,
            {
                "code": "no_active_policies",
                "message": "No active policies. Activate at least one policy before running an analysis.",
            },
        )
    # Built-in deterministic policy is always applied (glass-box: surface it
    # to consumers in `policies_applied` even when caller does not request it).
    if builtin_policy.BUILTIN_POLICY_ID not in requested_policies:
        requested_policies = [builtin_policy.BUILTIN_POLICY_ID, *requested_policies]

    storage_path = Path(doc.storage_uri.removeprefix("file://"))
    try:
        chunks = parser.parse(storage_path, doc.mime_type)
    except ValueError as exc:
        raise HTTPException(
            415,
            {
                "code": "unsupported_mime",
                "message": str(exc),
                "mime_type": doc.mime_type,
            },
        ) from exc
    except Exception as exc:
        log.error("analyze.parse_failed", doc_id=doc_id, error=str(exc))
        raise HTTPException(
            422,
            {"code": "parsing_failed", "message": f"Document parser failed: {exc}"},
        ) from exc
    if not chunks:
        raise HTTPException(
            422,
            {
                "code": "empty_document",
                "message": "Parser produced 0 chunks. Document may be empty, scanned without OCR, "
                "password-protected, or use an unsupported format.",
                "mime_type": doc.mime_type,
            },
        )

    # Persist chunks (idempotent: replace prior set for this doc) so the
    # viewer can render extracted text and link findings to evidence.
    await db.execute(sql_delete(DocumentChunk).where(DocumentChunk.doc_id == doc_id))
    for ord_idx, c in enumerate(chunks):
        bbox = ",".join(f"{v:.2f}" for v in c.bbox) if c.bbox else None
        db.add(
            DocumentChunk(
                id=c.id,
                doc_id=doc_id,
                ord=ord_idx,
                page=c.page,
                line_start=c.line_start,
                line_end=c.line_end,
                bbox=bbox,
                text=c.text,
                token_count=c.token_count,
            )
        )
    if doc.status == "uploaded":
        doc.status = "parsed"
    await db.flush()

    state: CheckState = {
        "doc_id": doc_id,
        "lang": (lang_override or doc.lang or "it"),
        "chunks": chunks,
        "structure": [],
        "selected_policies": requested_policies,
        "findings": [],
        "trace": [],
        "errors": [],
    }

    await events.publish(doc_id, {"type": "phase", "phase": "started"})
    graph = get_graph()
    try:
        final_state: CheckState = await graph.ainvoke(state)
    except Exception as exc:
        log.exception("analyze.graph_failed", doc_id=doc_id)
        await events.publish(
            doc_id,
            {"type": "phase", "phase": "error", "error": str(exc)[:300]},
        )
        raise HTTPException(
            500,
            {"code": "graph_failed", "message": f"Pipeline failed: {exc}"},
        ) from exc

    # ADR-0011: persist classifier output on Document.
    detected_doc_type = final_state.get("doc_type")
    if detected_doc_type:
        doc.doc_type = detected_doc_type
        doc.doc_type_confidence = final_state.get("doc_type_confidence")

    final_list_raw: Any = final_state.get("final_findings") or final_state.get(
        "findings", []
    )
    findings = [f.model_dump() for f in final_list_raw]
    engine_errors: list[str] = list(final_state.get("errors") or [])
    payload = {
        "report_id": f"r-{uuid.uuid4().hex[:12]}",
        "doc_id": doc_id,
        "score": final_state.get("score", 0),
        "by_severity": final_state.get("by_severity", {}),
        "findings": findings,
        "policies_applied": requested_policies,
        "chunks_evaluated": len(chunks),
        "engine_errors": engine_errors,
    }
    signature = sign_report(payload)

    db.add(
        ReportRow(
            id=payload["report_id"],
            doc_id=doc_id,
            user_id=principal.user_id,
            engine_version=settings.version,
            model_id=settings.llm_primary_model,
            embedding_model=settings.embedding_model,
            score=payload["score"],
            policies_applied=_json.dumps(requested_policies),
            payload=_json.dumps(payload, sort_keys=True),
            signature=signature,
        )
    )
    await db.commit()

    await audit.append_audit(
        db,
        action="analyze",
        user_id=principal.user_id,
        resource=f"document:{doc_id}",
        payload={"report_id": payload["report_id"], "score": payload["score"]},
    )

    await events.publish(doc_id, {"type": "report", "report_id": payload["report_id"]})
    await events.publish(doc_id, {"type": "phase", "phase": "done"})

    return {**payload, "signature": signature}


@router.websocket("/ws/analysis/{doc_id}")
async def ws_analysis(websocket: WebSocket, doc_id: str) -> None:
    """Streams events published by agents during pipeline execution."""
    await websocket.accept()
    try:
        async with events.subscribe(doc_id) as queue:
            await websocket.send_json(
                {"type": "phase", "phase": "subscribed", "doc_id": doc_id}
            )
            while True:
                event = await queue.get()
                await websocket.send_json(event)
                if event.get("type") == "phase" and event.get("phase") == "done":
                    break
    except WebSocketDisconnect:
        log.info("ws.disconnect", doc_id=doc_id)
