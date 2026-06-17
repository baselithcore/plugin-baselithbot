"""Data connectors: parse external event logs / metric streams into BOP models.

Enterprise event data rarely arrives hand-typed — it lives in CSV exports, JSON
APIs, or warehouse queries. This module turns either format into the plugin's
domain models so a connector can feed the engine from a real source. Parsing is
pure and deterministic; fetching (HTTP pull) lives in the service layer behind
the SSRF guard.

Format is auto-detected: text starting with ``[`` or ``{`` is parsed as JSON,
otherwise as CSV (header row, case-insensitive column names).
"""

from __future__ import annotations

import csv
import io
import json
from typing import Any

from .event_models import Event
from .models import MetricSample


class ConnectorParseError(ValueError):
    """Raised when source text cannot be parsed into the expected records."""


def _rows(text: str) -> list[dict[str, Any]]:
    """Parse CSV or JSON text into a list of plain dict rows."""
    stripped = text.strip()
    if not stripped:
        return []
    if stripped[0] in "[{":
        try:
            data = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise ConnectorParseError(f"invalid JSON: {exc}") from exc
        records = data if isinstance(data, list) else [data]
        return [r for r in records if isinstance(r, dict)]
    reader = csv.DictReader(io.StringIO(stripped))
    return [{(k or "").strip().lower(): v for k, v in row.items()} for row in reader]


def _get(row: dict[str, Any], *names: str) -> Any:
    """Case-insensitive lookup of the first present column among ``names``."""
    lowered = {str(k).lower(): v for k, v in row.items()}
    for name in names:
        if name in lowered and lowered[name] not in (None, ""):
            return lowered[name]
    return None


def parse_events(text: str) -> list[Event]:
    """Parse a CSV/JSON event log into :class:`Event` records.

    Recognised columns (case-insensitive): ``case_id``/``case``,
    ``activity``/``task``, ``timestamp``/``time``, optional ``resource``.
    """
    events: list[Event] = []
    for row in _rows(text):
        case_id = _get(row, "case_id", "case", "caseid")
        activity = _get(row, "activity", "task", "step", "event")
        timestamp = _get(row, "timestamp", "time", "datetime", "ts")
        if case_id is None or activity is None or timestamp is None:
            continue
        try:
            events.append(
                Event(
                    case_id=str(case_id),
                    activity=str(activity),
                    timestamp=timestamp,
                    resource=str(_get(row, "resource", "actor", "user") or ""),
                )
            )
        except Exception as exc:  # noqa: BLE001 — skip malformed rows, report at end
            raise ConnectorParseError(f"bad event row {row}: {exc}") from exc
    return events


def parse_samples(process_id: str, text: str) -> list[MetricSample]:
    """Parse a CSV/JSON metric stream into :class:`MetricSample` records.

    Recognised columns (case-insensitive): ``kpi_id``/``kpi``, ``value``,
    optional ``node_id``/``node`` and ``timestamp``. ``process_id`` is taken
    from the target, not the payload.
    """
    samples: list[MetricSample] = []
    for row in _rows(text):
        kpi_id = _get(row, "kpi_id", "kpi", "metric")
        value = _get(row, "value", "val", "measure")
        if kpi_id is None or value is None:
            continue
        try:
            fields: dict[str, Any] = {
                "process_id": process_id,
                "kpi_id": str(kpi_id),
                "value": float(value),
            }
            node_id = _get(row, "node_id", "node", "step")
            if node_id is not None:
                fields["node_id"] = str(node_id)
            timestamp = _get(row, "timestamp", "time", "ts")
            if timestamp is not None:
                fields["timestamp"] = timestamp
            samples.append(MetricSample.model_validate(fields))
        except Exception as exc:  # noqa: BLE001 — surface a clear parse error
            raise ConnectorParseError(f"bad sample row {row}: {exc}") from exc
    return samples


__all__ = ["ConnectorParseError", "parse_events", "parse_samples"]
