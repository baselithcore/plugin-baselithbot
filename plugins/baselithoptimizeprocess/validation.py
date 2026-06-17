"""Process-graph structural validation, shared across the service seams.

Extracted so both registration and governed apply validate identically without
either importing the other.
"""

from __future__ import annotations

from .models import ProcessGraph


class ProcessValidationError(ValueError):
    """Raised when a submitted process graph is internally inconsistent."""


def validate_process(process: ProcessGraph) -> None:
    """Reject graphs with duplicate ids or edges referencing unknown nodes."""
    node_ids = [n.id for n in process.nodes]
    if len(node_ids) != len(set(node_ids)):
        raise ProcessValidationError("duplicate node ids in process")
    known = set(node_ids)
    for edge in process.edges:
        if edge.source not in known or edge.target not in known:
            raise ProcessValidationError(
                f"edge {edge.source}->{edge.target} references unknown node"
            )
    kpi_ids = [k.id for k in process.kpis]
    if len(kpi_ids) != len(set(kpi_ids)):
        raise ProcessValidationError("duplicate KPI ids in process")


__all__ = ["ProcessValidationError", "validate_process"]
