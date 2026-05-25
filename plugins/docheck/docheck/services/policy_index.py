"""Policy rule vector index sync.

Single source of truth for keeping the ChromaDB `policy_rules` collection
aligned with the SQL `policy_rules` table. CRUD callers MUST go through here
to avoid the silent retrieval drift documented in the audit.

Glass Box pillar: rule excerpts in the vector store are stored verbatim and
returned verbatim in metadata, so the legal agent can sub-string check LLM
output against the retrieved excerpt.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.logging import log
from ..db.models import Policy, PolicyRule
from .embedding import embed, get_or_create_collection, text_hash

COLLECTION = "policy_rules"


def _coll() -> Any:
    return get_or_create_collection(COLLECTION)


def _rule_metadata(rule: PolicyRule, policy: Policy | None) -> dict[str, Any]:
    return {
        "rule_id": rule.id,
        "policy_id": rule.policy_id,
        "version": rule.policy_version,
        "rule_type": rule.rule_type,
        "severity": rule.severity,
        "excerpt": rule.excerpt,
        "matcher": rule.matcher or "",
        "scope": policy.scope if policy else "custom",
        "title": policy.title if policy else rule.id,
        "lang": policy.lang if policy else "it",
        "active": int(policy.active) if policy else 0,
        "applicable_doc_types": (policy.applicable_doc_types or "") if policy else "",
    }


class PolicyIndexError(RuntimeError):
    """Vector store failed to sync. Caller decides whether to abort or degrade."""


async def upsert_rule(db: AsyncSession, rule: PolicyRule) -> None:
    policy = (
        await db.execute(
            select(Policy).where(
                Policy.id == rule.policy_id,
                Policy.version == rule.policy_version,
            )
        )
    ).scalar_one_or_none()
    try:
        vec = embed([rule.excerpt])[0]
        _coll().upsert(
            ids=[rule.id],
            documents=[rule.excerpt],
            metadatas=[_rule_metadata(rule, policy)],
            embeddings=[vec],
        )
        rule.embed_ref = text_hash(rule.excerpt)
    except Exception as exc:
        log.error("policy_index.upsert_failed", rule_id=rule.id, error=str(exc))
        raise PolicyIndexError(
            f"vector index sync failed for rule {rule.id}: {exc}"
        ) from exc


async def upsert_many(db: AsyncSession, rules: list[PolicyRule]) -> int:
    if not rules:
        return 0
    pids = {(r.policy_id, r.policy_version) for r in rules}
    policies: dict[tuple[str, str], Policy] = {}
    for pid, ver in pids:
        p = (
            await db.execute(
                select(Policy).where(Policy.id == pid, Policy.version == ver)
            )
        ).scalar_one_or_none()
        if p:
            policies[(pid, ver)] = p
    try:
        vecs = embed([r.excerpt for r in rules])
        _coll().upsert(
            ids=[r.id for r in rules],
            documents=[r.excerpt for r in rules],
            metadatas=[
                _rule_metadata(r, policies.get((r.policy_id, r.policy_version)))
                for r in rules
            ],
            embeddings=vecs,
        )
        for r in rules:
            r.embed_ref = text_hash(r.excerpt)
        return len(rules)
    except Exception as exc:
        log.error("policy_index.upsert_many_failed", count=len(rules), error=str(exc))
        raise PolicyIndexError(
            f"vector index sync failed for {len(rules)} rule(s): {exc}"
        ) from exc


def delete_rule(rule_id: str) -> None:
    try:
        _coll()._store.delete(COLLECTION, [rule_id])
    except Exception as exc:
        log.warning("policy_index.delete_failed", rule_id=rule_id, error=str(exc))


def delete_policy_rules(rule_ids: list[str]) -> None:
    if not rule_ids:
        return
    try:
        _coll()._store.delete(COLLECTION, rule_ids)
    except Exception as exc:
        log.warning(
            "policy_index.delete_many_failed", count=len(rule_ids), error=str(exc)
        )


async def reindex_all(db: AsyncSession) -> int:
    rules = (await db.execute(select(PolicyRule))).scalars().all()
    return await upsert_many(db, list(rules))
