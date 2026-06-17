"""Governance mixin for :class:`BopService`: versioning + audit trail.

Split out of the service body to keep each file well under the size cap and to
group the compliance concern (immutable version snapshots + append-only audit
events) behind one cohesive seam. The mixin only touches ``self._store`` (the
shared :class:`ProcessStore`) and the tenant/actor context, so it composes
cleanly with the rest of the service.
"""

from __future__ import annotations

from .audit import build_version, content_hash, make_event
from .models import ProcessGraph
from .store import ProcessStore
from .tenancy import current_actor, current_tenant
from .versioning_models import AuditAction, AuditEvent, ProcessVersion


class GovernanceMixin:
    """Versioning + audit behaviour mixed into the BOP service."""

    _store: ProcessStore

    # -- Reads -------------------------------------------------------------

    async def list_versions(self, process_id: str) -> list[ProcessVersion]:
        """List a process's immutable version snapshots, newest first."""
        return await self._store.list_versions(current_tenant(), process_id)

    async def get_version(self, process_id: str, version: int) -> ProcessVersion | None:
        """Fetch one numbered version snapshot of a process."""
        return await self._store.get_version(current_tenant(), process_id, version)

    async def list_audit(
        self, process_id: str | None = None, limit: int = 100
    ) -> list[AuditEvent]:
        """List recent audit events, newest first, optionally per process."""
        return await self._store.list_audit(current_tenant(), process_id, limit)

    # -- Recording helpers -------------------------------------------------

    async def _record_save(
        self, tenant: str, process: ProcessGraph, action: AuditAction
    ) -> None:
        """Mint a new immutable version on content change, then audit the save."""
        previous = await self._store.latest_version(tenant, process.id)
        if previous is None or previous.content_hash != content_hash(process):
            await self._store.add_version(
                tenant, build_version(process, previous, current_actor())
            )
        await self._audit(tenant, action, "process", process.id, process.id, "")

    async def _audit(
        self,
        tenant: str,
        action: AuditAction,
        target_type: str,
        target_id: str,
        process_id: str,
        detail: str = "",
    ) -> None:
        """Append a single audit event for a state-changing action."""
        await self._store.add_audit(
            tenant,
            make_event(
                tenant,
                current_actor(),
                action,
                target_type,
                target_id,
                process_id,
                detail,
            ),
        )


__all__ = ["GovernanceMixin"]
