"""Domain models for BOP process versioning and the audit trail.

Two append-only concepts underpin enterprise governance:

* :class:`ProcessVersion` — an immutable snapshot of a :class:`ProcessGraph`
  captured whenever its content changes, numbered monotonically per process,
  with a human-readable diff summary and the acting principal.
* :class:`AuditEvent` — an append-only record of every state-changing action
  (who did what, to which target, when), so the system can answer "who approved
  this change and on what basis" long after the fact.

Both are transport-agnostic Pydantic models, mirroring :mod:`.models`.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from .models import ProcessGraph


def _utcnow() -> datetime:
    """Return a timezone-aware UTC timestamp (no naive clocks)."""
    return datetime.now(timezone.utc)


class AuditAction(str, Enum):
    """The catalogue of audited, state-changing actions."""

    PROCESS_REGISTER = "process_register"
    PROCESS_IMPORT = "process_import"
    PROCESS_MINE = "process_mine"
    PROCESS_DELETE = "process_delete"
    PROPOSAL_APPROVE = "proposal_approve"
    PROPOSAL_REJECT = "proposal_reject"
    RULE_CREATE = "rule_create"
    RULE_DELETE = "rule_delete"
    OPTIMIZE_RUN = "optimize_run"
    PROCESS_APPLY = "process_apply"
    PROCESS_ROLLBACK = "process_rollback"
    SLA_CREATE = "sla_create"
    SLA_DELETE = "sla_delete"
    RESOURCE_CREATE = "resource_create"
    RESOURCE_UPDATE = "resource_update"
    RESOURCE_DELETE = "resource_delete"
    RESOURCE_ASSIGN = "resource_assign"
    RESOURCE_UNASSIGN = "resource_unassign"


class ProcessVersion(BaseModel):
    """An immutable, numbered snapshot of a process graph."""

    process_id: str = Field(..., description="Process this version belongs to.")
    version: int = Field(..., ge=1, description="Monotonic version number (1-based).")
    content_hash: str = Field(..., description="Stable hash of the graph content.")
    graph: ProcessGraph = Field(..., description="The full snapshot at this version.")
    summary: str = Field(default="", description="Human-readable diff vs the prior.")
    actor: str = Field(default="anonymous", description="Principal that produced it.")
    created_at: datetime = Field(default_factory=_utcnow)


class AuditEvent(BaseModel):
    """An append-only record of a single state-changing action."""

    id: str = Field(..., description="Event identifier.")
    tenant_id: str = Field(..., description="Owning tenant.")
    actor: str = Field(default="anonymous", description="Principal that acted.")
    action: AuditAction = Field(..., description="What was done.")
    target_type: str = Field(..., description="Kind of target: process/proposal/rule.")
    target_id: str = Field(default="", description="Identifier of the target.")
    process_id: str = Field(
        default="", description="Owning process, for per-process audit queries."
    )
    detail: str = Field(default="", description="Human-readable context.")
    created_at: datetime = Field(default_factory=_utcnow)


__all__ = ["AuditAction", "ProcessVersion", "AuditEvent"]
