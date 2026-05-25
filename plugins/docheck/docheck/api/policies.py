"""Policy CRUD + activation + YAML import/export endpoints.

Thin HTTP layer; logic lives in `services/policies.py`.
"""

from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, Response, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.security import Principal
from ..db import get_session
from ..services import audit, builtin_policy, policy_ingest, policy_suggest
from ..services import policies as policy_svc
from .deps import require


def _guard_system(pid: str) -> None:
    """Block all write operations on the system (built-in) policy."""
    if builtin_policy.is_system_policy(pid):
        raise HTTPException(status_code=403, detail="Built-in policy is read-only")


router = APIRouter()


class PolicyOut(BaseModel):
    id: str
    version: str
    title: str
    scope: str
    lang: str
    active: bool
    rule_count: int
    system: bool = False


class CoverageGap(BaseModel):
    label: str
    excerpt: str
    severity_hint: str


class CoverageReport(BaseModel):
    """ADR-0014: post-ingest signal for non-expert operators.

    `coverage_ratio` is a stima, not an exact metric — surface it as such
    in the UI. `gaps` are detected obligations whose excerpt does not
    appear in any extracted rule (capped at 20 entries).
    """

    extracted_count: int
    detected_count: int
    coverage_ratio: float
    gaps: list[CoverageGap]


class IngestPolicyOut(PolicyOut):
    """Response model for the two ingest endpoints. Additive over PolicyOut."""

    coverage: CoverageReport | None = None


class RuleOut(BaseModel):
    id: str
    policy_id: str
    policy_version: str
    rule_type: str
    severity: str
    excerpt: str
    matcher: str | None = None
    system: bool = False
    enabled: bool = True
    title: str | None = None
    default_confidence: float | None = None


class RulePayload(BaseModel):
    id: str | None = None
    rule_type: str
    severity: str
    excerpt: str = Field(min_length=1)
    matcher: str | None = None


class PolicyCreatePayload(BaseModel):
    id: str = Field(min_length=2, max_length=64)
    version: str = Field(min_length=1, max_length=32)
    title: str = Field(min_length=1, max_length=200)
    scope: str
    lang: str = Field(default="it", min_length=2, max_length=8)
    active: bool = False
    rules: list[RulePayload] = Field(default_factory=list)


class PolicyPatchPayload(BaseModel):
    title: str | None = None
    scope: str | None = None
    lang: str | None = None


class RulePatchPayload(BaseModel):
    rule_type: str | None = None
    severity: str | None = None
    excerpt: str | None = None
    matcher: str | None = None


class ClonePayload(BaseModel):
    new_version: str = Field(min_length=1, max_length=32)


class ActivePayload(BaseModel):
    active: bool


# ---------- Read ----------


@router.get("/policies", response_model=list[PolicyOut])
async def list_policies(
    _: Principal = Depends(require("policy", "read")),
    db: AsyncSession = Depends(get_session),
) -> list[Any]:
    db_policies = await policy_svc.list_all(db)
    return [builtin_policy.policy_entry(), *db_policies]


@router.get("/policies/{policy_id}/rules", response_model=list[RuleOut])
async def list_rules(
    policy_id: str,
    version: str | None = Query(default=None),
    _: Principal = Depends(require("policy", "read")),
    db: AsyncSession = Depends(get_session),
) -> list[Any]:
    if builtin_policy.is_system_policy(policy_id):
        return builtin_policy.rule_entries()
    return await policy_svc.list_rules(db, policy_id, version)


@router.get("/policies/{policy_id}/{version}/export.yaml")
async def export_yaml(
    policy_id: str,
    version: str,
    _: Principal = Depends(require("policy", "read")),
    db: AsyncSession = Depends(get_session),
) -> Response:
    body = await policy_svc.export_yaml(db, pid=policy_id, version=version)
    return Response(
        content=body,
        media_type="application/x-yaml",
        headers={
            "Content-Disposition": f'attachment; filename="{policy_id}-{version}.yaml"'
        },
    )


# ---------- Write: policy lifecycle ----------


@router.post("/policies", response_model=PolicyOut, status_code=201)
async def create_policy(
    body: PolicyCreatePayload,
    principal: Principal = Depends(require("policy", "write")),
    db: AsyncSession = Depends(get_session),
) -> Any:
    _guard_system(body.id)
    out = await policy_svc.create_policy(
        db,
        pid=body.id,
        version=body.version,
        title=body.title,
        scope=body.scope,
        lang=body.lang,
        active=body.active,
        rules=[r.model_dump() for r in body.rules],
        created_by=principal.user_id,
    )
    await audit.append_audit(
        db,
        action="policy.create",
        user_id=principal.user_id,
        resource=f"policy:{body.id}@{body.version}",
        payload={"scope": body.scope, "rules": len(body.rules)},
    )
    return out


@router.patch("/policies/{policy_id}/{version}", response_model=PolicyOut)
async def update_policy(
    policy_id: str,
    version: str,
    body: PolicyPatchPayload,
    principal: Principal = Depends(require("policy", "write")),
    db: AsyncSession = Depends(get_session),
) -> Any:
    _guard_system(policy_id)
    patch = body.model_dump(exclude_unset=True)
    out = await policy_svc.update_policy(
        db, pid=policy_id, version=version, patch=patch
    )
    await db.commit()
    await audit.append_audit(
        db,
        action="policy.update",
        user_id=principal.user_id,
        resource=f"policy:{policy_id}@{version}",
        payload=patch,
    )
    return out


@router.post("/policies/{policy_id}/{version}/active")
async def set_active(
    policy_id: str,
    version: str,
    body: ActivePayload,
    principal: Principal = Depends(require("policy", "write")),
    db: AsyncSession = Depends(get_session),
) -> dict[str, Any]:
    _guard_system(policy_id)
    out = await policy_svc.set_active(
        db, pid=policy_id, version=version, active=body.active
    )
    await db.commit()
    await audit.append_audit(
        db,
        action="policy.activate" if body.active else "policy.deactivate",
        user_id=principal.user_id,
        resource=f"policy:{policy_id}@{version}",
        payload={"active": body.active},
    )
    return out


@router.post(
    "/policies/{policy_id}/{version}/clone", response_model=PolicyOut, status_code=201
)
async def clone_policy(
    policy_id: str,
    version: str,
    body: ClonePayload,
    principal: Principal = Depends(require("policy", "write")),
    db: AsyncSession = Depends(get_session),
) -> Any:
    _guard_system(policy_id)
    out = await policy_svc.clone_policy(
        db,
        pid=policy_id,
        version=version,
        new_version=body.new_version,
        created_by=principal.user_id,
    )
    await db.commit()
    await audit.append_audit(
        db,
        action="policy.clone",
        user_id=principal.user_id,
        resource=f"policy:{policy_id}@{body.new_version}",
        payload={"source_version": version},
    )
    return out


@router.delete("/policies/{policy_id}/{version}", status_code=204)
async def delete_policy(
    policy_id: str,
    version: str,
    force: bool = False,
    principal: Principal = Depends(require("policy", "admin")),
    db: AsyncSession = Depends(get_session),
) -> Response:
    _guard_system(policy_id)
    await policy_svc.delete_policy(db, pid=policy_id, version=version, force=force)
    await db.commit()
    await audit.append_audit(
        db,
        action="policy.delete",
        user_id=principal.user_id,
        resource=f"policy:{policy_id}@{version}",
        payload={"force": force},
    )
    return Response(status_code=204)


# ---------- Write: rule lifecycle ----------


@router.post(
    "/policies/{policy_id}/{version}/rules", response_model=RuleOut, status_code=201
)
async def add_rule(
    policy_id: str,
    version: str,
    body: RulePayload,
    principal: Principal = Depends(require("policy", "write")),
    db: AsyncSession = Depends(get_session),
) -> Any:
    _guard_system(policy_id)
    out = await policy_svc.add_rule(
        db,
        pid=policy_id,
        version=version,
        payload=body.model_dump(exclude_none=True),
    )
    await db.commit()
    await audit.append_audit(
        db,
        action="policy.rule.add",
        user_id=principal.user_id,
        resource=f"policy:{policy_id}@{version}",
        payload={"rule_id": out["id"]},
    )
    return out


@router.patch("/policies/{policy_id}/{version}/rules/{rule_id}", response_model=RuleOut)
async def update_rule(
    policy_id: str,
    version: str,
    rule_id: str,
    body: RulePatchPayload,
    principal: Principal = Depends(require("policy", "write")),
    db: AsyncSession = Depends(get_session),
) -> Any:
    _guard_system(policy_id)
    patch = body.model_dump(exclude_unset=True)
    out = await policy_svc.update_rule(
        db,
        pid=policy_id,
        version=version,
        rule_id=rule_id,
        patch=patch,
    )
    await db.commit()
    await audit.append_audit(
        db,
        action="policy.rule.update",
        user_id=principal.user_id,
        resource=f"policy:{policy_id}@{version}",
        payload={"rule_id": rule_id, "patch": list(patch.keys())},
    )
    return out


@router.delete("/policies/{policy_id}/{version}/rules/{rule_id}", status_code=204)
async def delete_rule(
    policy_id: str,
    version: str,
    rule_id: str,
    principal: Principal = Depends(require("policy", "write")),
    db: AsyncSession = Depends(get_session),
) -> Response:
    _guard_system(policy_id)
    await policy_svc.delete_rule(db, pid=policy_id, version=version, rule_id=rule_id)
    await db.commit()
    await audit.append_audit(
        db,
        action="policy.rule.delete",
        user_id=principal.user_id,
        resource=f"policy:{policy_id}@{version}",
        payload={"rule_id": rule_id},
    )
    return Response(status_code=204)


# ---------- YAML import ----------


@router.post("/policies/import", response_model=PolicyOut, status_code=201)
async def import_yaml(
    file: UploadFile = File(...),
    principal: Principal = Depends(require("policy", "write")),
    db: AsyncSession = Depends(get_session),
) -> Any:
    if file.size and file.size > 1 * 1024 * 1024:
        raise HTTPException(413, "Policy YAML too large (max 1MB)")
    body = await file.read()
    out = await policy_svc.import_yaml(db, content=body, created_by=principal.user_id)
    _guard_system(out["id"])
    await db.commit()
    await audit.append_audit(
        db,
        action="policy.import",
        user_id=principal.user_id,
        resource=f"policy:{out['id']}@{out['version']}",
        payload={"filename": file.filename, "rules": out["rule_count"]},
    )
    return out


# ---------- LLM-assisted ingestion (URL / document) ----------


class IngestUrlPayload(BaseModel):
    url: str = Field(min_length=8, max_length=2048)


@router.post("/policies/ingest/url", response_model=IngestPolicyOut, status_code=201)
async def ingest_from_url(
    body: IngestUrlPayload,
    principal: Principal = Depends(require("policy", "write")),
    db: AsyncSession = Depends(get_session),
) -> Any:
    out = await policy_ingest.ingest_from_url(
        db,
        url=body.url,
        created_by=principal.user_id,
    )
    await db.commit()
    await audit.append_audit(
        db,
        action="policy.ingest.url",
        user_id=principal.user_id,
        resource=f"policy:{out['id']}@{out['version']}",
        payload={"url": body.url, "rules": out["rule_count"]},
    )
    return out


@router.post(
    "/policies/ingest/document", response_model=IngestPolicyOut, status_code=201
)
async def ingest_from_document(
    file: UploadFile = File(...),
    principal: Principal = Depends(require("policy", "write")),
    db: AsyncSession = Depends(get_session),
) -> Any:
    if file.size and file.size > 25 * 1024 * 1024:
        raise HTTPException(413, "Document too large (max 25MB)")
    body = await file.read()
    out = await policy_ingest.ingest_from_document(
        db,
        filename=file.filename or "policy.bin",
        mime_type=file.content_type or "application/octet-stream",
        content=body,
        created_by=principal.user_id,
    )
    await db.commit()
    await audit.append_audit(
        db,
        action="policy.ingest.document",
        user_id=principal.user_id,
        resource=f"policy:{out['id']}@{out['version']}",
        payload={"filename": file.filename, "rules": out["rule_count"]},
    )
    return out


# ---------- Suggest-more rules loop (ADR-0015) ----------


class SuggestRulesPayload(BaseModel):
    """Exactly one of `source_url` / `source_text` must be provided."""

    source_url: str | None = Field(default=None, min_length=8, max_length=2048)
    source_text: str | None = Field(default=None, max_length=200_000)


class SuggestedRule(BaseModel):
    rule_type: str
    severity: str
    excerpt: str
    matcher: str | None = None
    rationale: str | None = None


class SuggestRulesOut(BaseModel):
    suggestions: list[SuggestedRule]


@router.post(
    "/policies/{policy_id}/{version}/suggest-rules",
    response_model=SuggestRulesOut,
)
async def suggest_rules(
    policy_id: str,
    version: str,
    body: SuggestRulesPayload,
    principal: Principal = Depends(require("policy", "write")),
    db: AsyncSession = Depends(get_session),
) -> Any:
    _guard_system(policy_id)
    if bool(body.source_url) == bool(body.source_text):
        raise HTTPException(400, "Provide exactly one of source_url or source_text")
    if body.source_url:
        suggestions = await policy_suggest.suggest_from_url(
            db, pid=policy_id, version=version, url=body.source_url
        )
    else:
        assert body.source_text is not None  # guarded by xor check above
        suggestions = await policy_suggest.suggest_more(
            db, pid=policy_id, version=version, source_text=body.source_text
        )
    await audit.append_audit(
        db,
        action="policy.suggest.requested",
        user_id=principal.user_id,
        resource=f"policy:{policy_id}@{version}",
        payload={
            "source": "url" if body.source_url else "text",
            "candidates": len(suggestions),
        },
    )
    return {"suggestions": suggestions}


@router.post(
    "/policies/{policy_id}/{version}/suggest-rules/document",
    response_model=SuggestRulesOut,
)
async def suggest_rules_from_document(
    policy_id: str,
    version: str,
    file: UploadFile = File(...),
    principal: Principal = Depends(require("policy", "write")),
    db: AsyncSession = Depends(get_session),
) -> Any:
    _guard_system(policy_id)
    if file.size and file.size > 25 * 1024 * 1024:
        raise HTTPException(413, "Document too large (max 25MB)")
    content = await file.read()
    suggestions = await policy_suggest.suggest_from_document(
        db,
        pid=policy_id,
        version=version,
        filename=file.filename or "policy.bin",
        mime_type=file.content_type or "application/octet-stream",
        content=content,
    )
    await audit.append_audit(
        db,
        action="policy.suggest.requested",
        user_id=principal.user_id,
        resource=f"policy:{policy_id}@{version}",
        payload={
            "source": "document",
            "filename": file.filename,
            "candidates": len(suggestions),
        },
    )
    return {"suggestions": suggestions}
