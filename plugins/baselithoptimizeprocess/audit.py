"""Pure helpers for process versioning and audit-event construction.

No I/O and no global state: given a process graph (and optionally its previous
version) these functions compute a stable content hash, a readable diff summary,
the next :class:`ProcessVersion`, and :class:`AuditEvent` records. The service
layer composes them with the store, keeping its own body thin.
"""

from __future__ import annotations

import hashlib
import json
import uuid

from .models import ProcessGraph
from .versioning_models import AuditAction, AuditEvent, ProcessVersion


def content_hash(process: ProcessGraph) -> str:
    """Stable SHA-256 over a process's *structural* content.

    Timestamps are excluded so re-saving an unchanged graph does not mint a new
    version; only node/edge/KPI/identity changes move the hash.
    """
    nodes = sorted(process.nodes, key=lambda n: n.id)
    edges = sorted(process.edges, key=lambda e: (e.source, e.target, e.condition))
    kpis = sorted(process.kpis, key=lambda k: k.id)
    payload = {
        "id": process.id,
        "name": process.name,
        "description": process.description,
        "currency": process.currency,
        "annual_case_volume": process.annual_case_volume,
        "nodes": [
            {
                "id": n.id,
                "name": n.name,
                "kind": n.kind.value,
                "role": n.role,
                "resource_id": n.resource_id,
                "cost": n.cost.model_dump() if n.cost else None,
            }
            for n in nodes
        ],
        "edges": [{"s": e.source, "t": e.target, "c": e.condition} for e in edges],
        "kpis": [
            {"id": k.id, "target": k.target, "dir": k.direction.value} for k in kpis
        ],
    }
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def diff_summary(previous: ProcessGraph | None, current: ProcessGraph) -> str:
    """Render a concise change summary of ``current`` versus ``previous``."""
    if previous is None:
        return (
            f"initial version: {len(current.nodes)} steps, "
            f"{len(current.edges)} transitions, {len(current.kpis)} KPIs"
        )
    parts: list[str] = []
    parts.append(_delta("steps", len(previous.nodes), len(current.nodes)))
    parts.append(_delta("transitions", len(previous.edges), len(current.edges)))
    parts.append(_delta("KPIs", len(previous.kpis), len(current.kpis)))
    changed = [p for p in parts if p]
    return "; ".join(changed) if changed else "metadata changed"


def _delta(label: str, before: int, after: int) -> str:
    """Format a single +/- count change, or '' when unchanged."""
    if before == after:
        return ""
    sign = "+" if after > before else ""
    return f"{sign}{after - before} {label} ({before}→{after})"


def build_version(
    process: ProcessGraph, previous: ProcessVersion | None, actor: str
) -> ProcessVersion:
    """Construct the next :class:`ProcessVersion` for a changed graph."""
    return ProcessVersion(
        process_id=process.id,
        version=(previous.version + 1) if previous else 1,
        content_hash=content_hash(process),
        graph=process,
        summary=diff_summary(previous.graph if previous else None, process),
        actor=actor,
    )


def make_event(
    tenant_id: str,
    actor: str,
    action: AuditAction,
    target_type: str,
    target_id: str = "",
    process_id: str = "",
    detail: str = "",
) -> AuditEvent:
    """Build an :class:`AuditEvent` with a fresh id."""
    return AuditEvent(
        id=uuid.uuid4().hex,
        tenant_id=tenant_id,
        actor=actor,
        action=action,
        target_type=target_type,
        target_id=target_id,
        process_id=process_id,
        detail=detail,
    )


__all__ = ["content_hash", "diff_summary", "build_version", "make_event"]
