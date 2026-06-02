"""Row/scalar coercion helpers for FalkorDB ``GRAPH.QUERY --compact`` shape."""

from __future__ import annotations

from typing import Any

from llm_wiki.graphdb.store._models import EntityRecord


def _scalar(cell: Any) -> Any:
    """FalkorDB --compact returns scalars as ``[type_code, value]``."""
    if isinstance(cell, list | tuple) and len(cell) >= 2:
        return cell[1]
    return cell


def _entity_from_row(row: list[Any]) -> EntityRecord:
    eid = str(_scalar(row[0]) if row else "")
    name = str(_scalar(row[1]) if len(row) > 1 else eid)
    kind = str(_scalar(row[2]) if len(row) > 2 else "")
    aliases_raw = _scalar(row[3]) if len(row) > 3 else ""
    aliases = [a for a in str(aliases_raw or "").split(",") if a]
    return EntityRecord(id=eid, name=name, kind=kind, aliases=aliases)


def _rows(result: list[Any]) -> list[list[Any]]:
    """Extract result rows from FalkorDB's ``GRAPH.QUERY --compact`` shape.

    Shape: ``[header, rows, statistics]``. Each row is a list aligned
    with the header. Forgiving of empty / malformed responses.
    """
    try:
        if len(result) > 1 and isinstance(result[1], list):
            return [list(r) if isinstance(r, list | tuple) else [r] for r in result[1]]
    except Exception:
        pass
    return []
