"""File-replay telemetry source — deterministic playback for debrief/testing.

Replays a recorded session from a CSV or JSON-Lines file, emitting one payload
per row at a configurable rate (``speed`` scales the inter-frame delay; ``0``
replays as fast as possible). The bus still validates every row, so a malformed
recording is dropped row-by-row rather than aborting the replay. Numeric columns
are coerced from strings (CSV has no types); unknown columns are ignored by the
:class:`TelemetryFrame` boundary.
"""

from __future__ import annotations

import asyncio
import csv
import json
from pathlib import Path
from typing import Any, Awaitable, Callable

from core.observability.logging import get_logger

logger = get_logger(__name__)

# Columns coerced to float when present (CSV strings → numbers).
_FLOAT_FIELDS = (
    "speed_kph",
    "engine_temp_c",
    "oil_temp_c",
    "ers_deploy",
    "fuel_kg",
    "tyre_wear",
    "tyre_temp_c",
    "gap_ahead_s",
    "gap_behind_s",
    "last_lap_s",
)
_INT_FIELDS = ("lap", "position", "sector", "tyre_age_laps")


def _coerce(row: dict[str, Any]) -> dict[str, Any]:
    """Coerce known numeric columns; drop empty strings so defaults apply."""
    out: dict[str, Any] = {}
    for key, value in row.items():
        if value is None or value == "":
            continue
        if key in _FLOAT_FIELDS:
            try:
                out[key] = float(value)
            except (TypeError, ValueError):
                continue
        elif key in _INT_FIELDS:
            try:
                out[key] = int(float(value))
            except (TypeError, ValueError):
                continue
        else:
            out[key] = value
    return out


class FileReplaySource:
    """Replay telemetry rows from a CSV or JSONL recording."""

    def __init__(
        self,
        path: str | Path,
        tick_seconds: float = 0.5,
        speed: float = 1.0,
        loop: bool = False,
    ) -> None:
        self.path = Path(path)
        self.tick_seconds = tick_seconds
        self.speed = max(0.0, speed)
        self.loop = loop

    def _rows(self) -> list[dict[str, Any]]:
        """Parse the recording into a list of raw payload dicts."""
        text = self.path.read_text(encoding="utf-8")
        if self.path.suffix.lower() in (".jsonl", ".ndjson"):
            return [json.loads(line) for line in text.splitlines() if line.strip()]
        if self.path.suffix.lower() == ".json":
            data = json.loads(text)
            return data if isinstance(data, list) else [data]
        reader = csv.DictReader(text.splitlines())
        return [_coerce(row) for row in reader]

    async def run(self, emit: Callable[[dict], Awaitable[None]]) -> None:
        """Emit every recorded row, optionally looping, until cancelled."""
        try:
            rows = self._rows()
        except (OSError, json.JSONDecodeError, ValueError) as exc:
            logger.error(
                "pitwall_replay_parse_failed", path=str(self.path), error=str(exc)
            )
            return
        delay = self.tick_seconds / self.speed if self.speed > 0 else 0.0
        logger.info("pitwall_replay_started", path=str(self.path), rows=len(rows))
        try:
            while True:
                for row in rows:
                    await emit(row)
                    if delay:
                        await asyncio.sleep(delay)
                if not self.loop:
                    break
        except asyncio.CancelledError:
            raise


__all__ = ["FileReplaySource"]
