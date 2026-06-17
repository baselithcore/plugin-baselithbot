"""Shared helpers for the Postgres-backed store and its mixins.

Holds the single JSONB adapter used by every Postgres write so the store class
and its extracted mixins (kept apart only to respect the file-size cap) share one
canonical serialization seam rather than duplicating it.
"""

from __future__ import annotations

from typing import Any

from psycopg.types.json import Jsonb


def _blob(model: Any) -> Jsonb:
    """Adapt a Pydantic model to a JSON-safe JSONB parameter."""
    return Jsonb(model.model_dump(mode="json"))


__all__ = ["_blob"]
