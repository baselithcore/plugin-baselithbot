"""Shared JSONB adapter for the Postgres-backed pit-wall store.

One canonical serialization seam so every write round-trips a Pydantic model
through JSONB identically rather than duplicating ``model_dump`` calls.
"""

from __future__ import annotations

from typing import Any

from psycopg.types.json import Jsonb


def _blob(model: Any) -> Jsonb:
    """Adapt a Pydantic model to a JSON-safe JSONB parameter."""
    return Jsonb(model.model_dump(mode="json"))


__all__ = ["_blob"]
