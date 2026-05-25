"""Policy & rule business logic: CRUD, clone, activate, YAML import/export.

Kept separate from `api/policies.py` so the HTTP layer stays thin and the LOC budget holds.
"""

from __future__ import annotations

import io
import re
import uuid
from typing import Any

import yaml
from fastapi import HTTPException, status
from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.models import Policy, PolicyRule, Report
from . import policy_index

VALID_SCOPES = {"global_default", "eu", "world", "custom"}
VALID_RULE_TYPES = {"presence", "absence", "format", "numeric_limit", "semantic"}
VALID_SEVERITIES = {"fail", "warn", "info"}

_ID_RE = re.compile(r"^[a-z0-9_.-]{2,64}$")
_VERSION_RE = re.compile(r"^[a-zA-Z0-9._-]{1,32}$")


def _validate_id(pid: str, field: str = "id") -> None:
    if not _ID_RE.match(pid):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid {field}: {pid}")


def _validate_version(v: str) -> None:
    if not _VERSION_RE.match(v):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid version: {v}")


def _validate_scope(scope: str) -> None:
    if scope not in VALID_SCOPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid scope: {scope}")


def _validate_rule_payload(p: dict[str, Any]) -> None:
    if p.get("rule_type") not in VALID_RULE_TYPES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid rule_type: {p.get('rule_type')}")
    if p.get("severity") not in VALID_SEVERITIES:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid severity: {p.get('severity')}")
    if not (p.get("excerpt") or "").strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "excerpt required")


async def _get_policy_or_404(db: AsyncSession, pid: str, version: str) -> Policy:
    p = (await db.execute(select(Policy).where(Policy.id == pid, Policy.version == version))).scalar_one_or_none()
    if not p:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Policy not found")
    return p


async def _rule_count(db: AsyncSession, pid: str, version: str) -> int:
    return int(
        (
            await db.execute(
                select(func.count(PolicyRule.id)).where(
                    PolicyRule.policy_id == pid,
                    PolicyRule.policy_version == version,
                )
            )
        ).scalar_one()
    )


async def list_all(db: AsyncSession) -> list[dict[str, Any]]:
    rows = (await db.execute(select(Policy).order_by(Policy.id, Policy.version))).scalars().all()
    out: list[dict[str, Any]] = []
    for p in rows:
        out.append(
            {
                "id": p.id,
                "version": p.version,
                "title": p.title,
                "scope": p.scope,
                "lang": p.lang,
                "active": bool(p.active),
                "rule_count": await _rule_count(db, p.id, p.version),
            }
        )
    return out


async def list_rules(db: AsyncSession, pid: str, version: str | None) -> list[dict[str, Any]]:
    stmt = select(PolicyRule).where(PolicyRule.policy_id == pid)
    if version:
        stmt = stmt.where(PolicyRule.policy_version == version)
    rows = (await db.execute(stmt.order_by(PolicyRule.id))).scalars().all()
    return [
        {
            "id": r.id,
            "policy_id": r.policy_id,
            "policy_version": r.policy_version,
            "rule_type": r.rule_type,
            "severity": r.severity,
            "excerpt": r.excerpt,
            "matcher": r.matcher,
        }
        for r in rows
    ]


async def create_policy(
    db: AsyncSession,
    *,
    pid: str,
    version: str,
    title: str,
    scope: str,
    lang: str,
    active: bool,
    rules: list[dict[str, Any]],
    created_by: str,
) -> dict[str, Any]:
    _validate_id(pid)
    _validate_version(version)
    _validate_scope(scope)
    if not (title or "").strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "title required")
    existing = (
        await db.execute(select(Policy).where(Policy.id == pid, Policy.version == version))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Policy {pid}@{version} already exists")

    db.add(
        Policy(
            id=pid,
            version=version,
            title=title.strip(),
            scope=scope,
            lang=lang or "it",
            active=1 if active else 0,
            created_by=created_by,
        )
    )
    for r in rules or []:
        await add_rule(db, pid=pid, version=version, payload=r, _autoflush=False)
    await db.flush()
    new_rules = (
        (
            await db.execute(
                select(PolicyRule).where(
                    PolicyRule.policy_id == pid,
                    PolicyRule.policy_version == version,
                )
            )
        )
        .scalars()
        .all()
    )
    await policy_index.upsert_many(db, list(new_rules))
    return {
        "id": pid,
        "version": version,
        "title": title.strip(),
        "scope": scope,
        "lang": lang or "it",
        "active": bool(active),
        "rule_count": len(rules or []),
    }


async def update_policy(db: AsyncSession, *, pid: str, version: str, patch: dict[str, Any]) -> dict[str, Any]:
    p = await _get_policy_or_404(db, pid, version)
    if "title" in patch:
        title = (patch["title"] or "").strip()
        if not title:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "title required")
        p.title = title
    if "scope" in patch:
        _validate_scope(patch["scope"])
        p.scope = patch["scope"]
    if "lang" in patch:
        p.lang = patch["lang"] or p.lang
    await db.flush()
    return {
        "id": p.id,
        "version": p.version,
        "title": p.title,
        "scope": p.scope,
        "lang": p.lang,
        "active": bool(p.active),
        "rule_count": await _rule_count(db, p.id, p.version),
    }


async def set_active(db: AsyncSession, *, pid: str, version: str, active: bool) -> dict[str, Any]:
    p = await _get_policy_or_404(db, pid, version)
    p.active = 1 if active else 0
    await db.flush()
    rules = (
        (await db.execute(select(PolicyRule).where(PolicyRule.policy_id == pid, PolicyRule.policy_version == version)))
        .scalars()
        .all()
    )
    await policy_index.upsert_many(db, list(rules))
    return {"id": p.id, "version": p.version, "active": bool(p.active)}


async def delete_policy(db: AsyncSession, *, pid: str, version: str, force: bool = False) -> None:
    p = await _get_policy_or_404(db, pid, version)
    # Block delete if any signed report references this policy version,
    # unless the caller explicitly forces (audit log preserves history).
    if not force:
        refs = (
            await db.execute(select(func.count(Report.id)).where(Report.policies_applied.like(f'%"{pid}"%')))
        ).scalar_one()
        if refs > 0:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"Policy {pid}@{version} referenced by {refs} report(s); pass force=true to override.",
            )
    rule_ids = [
        rid
        for (rid,) in (
            await db.execute(
                select(PolicyRule.id).where(
                    PolicyRule.policy_id == pid,
                    PolicyRule.policy_version == version,
                )
            )
        ).all()
    ]
    await db.execute(sql_delete(PolicyRule).where(PolicyRule.policy_id == pid, PolicyRule.policy_version == version))
    await db.delete(p)
    await db.flush()
    policy_index.delete_policy_rules(rule_ids)


async def clone_policy(
    db: AsyncSession, *, pid: str, version: str, new_version: str, created_by: str
) -> dict[str, Any]:
    _validate_version(new_version)
    src = await _get_policy_or_404(db, pid, version)
    existing = (
        await db.execute(select(Policy).where(Policy.id == pid, Policy.version == new_version))
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, f"{pid}@{new_version} exists")

    db.add(
        Policy(
            id=pid,
            version=new_version,
            title=src.title,
            scope=src.scope,
            lang=src.lang,
            source_uri=src.source_uri,
            active=0,
            created_by=created_by,
        )
    )
    src_rules = (
        (await db.execute(select(PolicyRule).where(PolicyRule.policy_id == pid, PolicyRule.policy_version == version)))
        .scalars()
        .all()
    )
    cloned: list[PolicyRule] = []
    for r in src_rules:
        new_rule = PolicyRule(
            id=f"{r.id}-c{uuid.uuid4().hex[:6]}",
            policy_id=pid,
            policy_version=new_version,
            rule_type=r.rule_type,
            severity=r.severity,
            excerpt=r.excerpt,
            matcher=r.matcher,
        )
        db.add(new_rule)
        cloned.append(new_rule)
    await db.flush()
    await policy_index.upsert_many(db, cloned)
    return {
        "id": pid,
        "version": new_version,
        "title": src.title,
        "scope": src.scope,
        "lang": src.lang,
        "active": False,
        "rule_count": len(src_rules),
    }


async def add_rule(
    db: AsyncSession, *, pid: str, version: str, payload: dict[str, Any], _autoflush: bool = True
) -> dict[str, Any]:
    if _autoflush:
        await _get_policy_or_404(db, pid, version)
    _validate_rule_payload(payload)
    rid = (payload.get("id") or "").strip() or f"rule-{uuid.uuid4().hex[:10]}"
    _validate_id(rid, field="rule id")
    exists = (await db.execute(select(PolicyRule).where(PolicyRule.id == rid))).scalar_one_or_none()
    if exists:
        raise HTTPException(status.HTTP_409_CONFLICT, f"Rule id {rid} exists")
    row = PolicyRule(
        id=rid,
        policy_id=pid,
        policy_version=version,
        rule_type=payload["rule_type"],
        severity=payload["severity"],
        excerpt=payload["excerpt"].strip(),
        matcher=(payload.get("matcher") or None),
    )
    db.add(row)
    if _autoflush:
        await db.flush()
        await policy_index.upsert_rule(db, row)
    return {
        "id": row.id,
        "policy_id": row.policy_id,
        "policy_version": row.policy_version,
        "rule_type": row.rule_type,
        "severity": row.severity,
        "excerpt": row.excerpt,
        "matcher": row.matcher,
    }


async def update_rule(
    db: AsyncSession, *, pid: str, version: str, rule_id: str, patch: dict[str, Any]
) -> dict[str, Any]:
    r = (
        await db.execute(
            select(PolicyRule).where(
                PolicyRule.id == rule_id,
                PolicyRule.policy_id == pid,
                PolicyRule.policy_version == version,
            )
        )
    ).scalar_one_or_none()
    if not r:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
    if "rule_type" in patch:
        if patch["rule_type"] not in VALID_RULE_TYPES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid rule_type")
        r.rule_type = patch["rule_type"]
    if "severity" in patch:
        if patch["severity"] not in VALID_SEVERITIES:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid severity")
        r.severity = patch["severity"]
    if "excerpt" in patch:
        excerpt = (patch["excerpt"] or "").strip()
        if not excerpt:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "excerpt required")
        r.excerpt = excerpt
    if "matcher" in patch:
        r.matcher = patch["matcher"] or None
    await db.flush()
    await policy_index.upsert_rule(db, r)
    return {
        "id": r.id,
        "policy_id": r.policy_id,
        "policy_version": r.policy_version,
        "rule_type": r.rule_type,
        "severity": r.severity,
        "excerpt": r.excerpt,
        "matcher": r.matcher,
    }


async def delete_rule(db: AsyncSession, *, pid: str, version: str, rule_id: str) -> None:
    r = (
        await db.execute(
            select(PolicyRule).where(
                PolicyRule.id == rule_id,
                PolicyRule.policy_id == pid,
                PolicyRule.policy_version == version,
            )
        )
    ).scalar_one_or_none()
    if not r:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
    rid = r.id
    await db.delete(r)
    await db.flush()
    policy_index.delete_rule(rid)


async def export_yaml(db: AsyncSession, *, pid: str, version: str) -> str:
    p = await _get_policy_or_404(db, pid, version)
    rules = await list_rules(db, pid, version)
    doc = {
        "id": p.id,
        "version": p.version,
        "title": p.title,
        "scope": p.scope,
        "lang": p.lang,
        "active": bool(p.active),
        "rules": [
            {
                "id": r["id"],
                "rule_type": r["rule_type"],
                "severity": r["severity"],
                "excerpt": r["excerpt"],
                **({"matcher": r["matcher"]} if r["matcher"] else {}),
            }
            for r in rules
        ],
    }
    out: str = yaml.safe_dump(doc, sort_keys=False, allow_unicode=True)
    return out


async def import_yaml(
    db: AsyncSession,
    *,
    content: bytes | str,
    created_by: str,
    override_active: bool | None = None,
) -> dict[str, Any]:
    try:
        data = yaml.safe_load(io.BytesIO(content)) if isinstance(content, bytes) else yaml.safe_load(content)
    except yaml.YAMLError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Invalid YAML: {exc}") from exc
    if not isinstance(data, dict):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Root must be a mapping")
    pid = str(data.get("id") or "").strip()
    version = str(data.get("version") or "").strip()
    title = str(data.get("title") or "").strip()
    scope = str(data.get("scope") or "custom").strip()
    lang = str(data.get("lang") or "it").strip()
    active = bool(data.get("active", False)) if override_active is None else bool(override_active)
    rules = data.get("rules") or []
    if not isinstance(rules, list):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "`rules` must be a list")
    # Rule ids are unique PKs across the table; on import we regenerate
    # them to avoid collisions with rules already in the catalog.
    sanitized_rules: list[dict[str, Any]] = []
    for r in rules:
        if not isinstance(r, dict):
            continue
        rcopy = dict(r)
        rcopy.pop("id", None)
        sanitized_rules.append(rcopy)
    return await create_policy(
        db,
        pid=pid,
        version=version,
        title=title,
        scope=scope,
        lang=lang,
        active=active,
        rules=sanitized_rules,
        created_by=created_by,
    )
