"""Append-only audit log with Ed25519-signed hash chain."""

import hashlib
import json
from pathlib import Path
from typing import Any

from nacl.signing import SigningKey, VerifyKey
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.config import settings
from ..core.logging import log
from ..core.tenant import current_tenant
from ..db.models import AuditLog

GENESIS_HASH = "0" * 64


def _canonical(payload: dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load_signing_key() -> SigningKey:
    p: Path = settings.audit_signing_key_path
    if not p.exists():
        sk = SigningKey.generate()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(sk.encode())
        p.chmod(0o600)
        log.warning("audit.signing_key.generated", path=str(p))
    return SigningKey(p.read_bytes())


_signing_key = _load_signing_key()


async def append_audit(
    db: AsyncSession,
    *,
    action: str,
    user_id: str | None,
    resource: str | None,
    payload: dict[str, Any] | None = None,
) -> AuditLog:
    """Append immutable audit record. Returns persisted row."""
    payload_bytes = _canonical(payload or {})
    payload_hash = _sha256(payload_bytes)

    tenant_id = current_tenant()
    last = (
        await db.execute(select(AuditLog).where(AuditLog.tenant_id == tenant_id).order_by(desc(AuditLog.seq)).limit(1))
    ).scalar_one_or_none()
    prev_hash = last.entry_hash if last else GENESIS_HASH

    row_canonical = {
        "tenant_id": tenant_id,
        "user_id": user_id,
        "action": action,
        "resource": resource,
        "payload_hash": payload_hash,
        "prev_hash": prev_hash,
    }
    entry_hash = _sha256(prev_hash.encode() + _canonical(row_canonical))
    signature = _signing_key.sign(entry_hash.encode()).signature.hex()

    record = AuditLog(
        tenant_id=tenant_id,
        user_id=user_id,
        action=action,
        resource=resource,
        payload_hash=payload_hash,
        prev_hash=prev_hash,
        entry_hash=entry_hash,
        signature=signature,
    )
    db.add(record)
    await db.commit()
    await db.refresh(record)
    return record


async def verify_chain(db: AsyncSession) -> tuple[bool, int | None]:
    """Verify chain integrity for current tenant. Returns (ok, broken_seq?)."""
    verify_key: VerifyKey = _signing_key.verify_key
    tenant_id = current_tenant()
    rows = (
        (await db.execute(select(AuditLog).where(AuditLog.tenant_id == tenant_id).order_by(AuditLog.seq)))
        .scalars()
        .all()
    )
    prev = GENESIS_HASH
    for r in rows:
        recomputed = _sha256(
            prev.encode()
            + _canonical(
                {
                    "tenant_id": tenant_id,
                    "user_id": r.user_id,
                    "action": r.action,
                    "resource": r.resource,
                    "payload_hash": r.payload_hash,
                    "prev_hash": prev,
                }
            )
        )
        if recomputed != r.entry_hash or r.prev_hash != prev:
            return False, r.seq
        try:
            verify_key.verify(r.entry_hash.encode(), bytes.fromhex(r.signature))
        except Exception:
            return False, r.seq
        prev = r.entry_hash
    return True, None
