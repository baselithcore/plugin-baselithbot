"""Verdict cache for agent findings. Key: (chunk_hash || rule_id || rule_version || model)."""

import hashlib
import json
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.tenant import current_tenant
from ..db.models import VerdictCache

_metrics = {"hits": 0, "misses": 0}


def cache_key(chunk_text: str, rule_id: str, rule_version: str = "0") -> str:
    chunk_hash = hashlib.sha256(chunk_text.encode("utf-8")).hexdigest()
    raw = f"{current_tenant()}|{chunk_hash}|{rule_id}|{rule_version}|{settings.llm_primary_model}"
    return hashlib.sha256(raw.encode()).hexdigest()


async def get_verdict(db: AsyncSession, key: str) -> dict[str, Any] | None:
    row = await db.get(VerdictCache, key)
    if row is None:
        _metrics["misses"] += 1
        return None
    _metrics["hits"] += 1
    row.hit_count += 1
    await db.commit()
    parsed: dict[str, Any] = json.loads(row.finding_json)
    return parsed


async def set_verdict(db: AsyncSession, key: str, finding: dict[str, Any]) -> None:
    db.add(
        VerdictCache(cache_key=key, finding_json=json.dumps(finding, sort_keys=True))
    )
    try:
        await db.commit()
    except Exception:
        await db.rollback()


def get_metrics() -> dict[str, Any]:
    total = _metrics["hits"] + _metrics["misses"]
    ratio = _metrics["hits"] / total if total else 0.0
    return {
        "hits": _metrics["hits"],
        "misses": _metrics["misses"],
        "total": total,
        "hit_ratio": round(ratio, 3),
    }


def reset_metrics() -> None:
    _metrics["hits"] = 0
    _metrics["misses"] = 0
