"""Telemetry ingestion package: the validated async fan-in plus its adapters.

The :class:`TelemetryBus` owns the trust boundary; every adapter implements the
:class:`TelemetrySource` Protocol and stays dumb (it only produces raw dicts).
:func:`build_source` maps a session's :class:`~..session_models.TelemetrySourceKind`
to a concrete adapter using the plugin config, so the session manager never
hard-codes a source type.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..session_models import TelemetrySourceKind
from ._bus import FrameHandler, TelemetryBus, TelemetrySource
from ._file_replay import FileReplaySource
from ._simulated import SimulatedSource
from ._udp import UdpSource
from ._websocket import WebSocketSource

if TYPE_CHECKING:
    from ..config import PitwallConfig


def build_source(
    kind: TelemetrySourceKind, config: "PitwallConfig", *, car_id: str = "BC44"
) -> TelemetrySource | None:
    """Construct the telemetry adapter for a session, or None for manual feeds.

    ``MANUAL`` sessions receive no producer — frames arrive only via the REST
    ingest endpoint. Unknown/unconfigured kinds degrade to None rather than
    raising, so a misconfigured session still serves its read surface.
    """
    if kind is TelemetrySourceKind.SIMULATED:
        return SimulatedSource(
            car_id=car_id,
            total_laps=config.sim_total_laps,
            tick_seconds=config.sim_tick_seconds,
        )
    if kind is TelemetrySourceKind.FILE_REPLAY:
        if not config.replay_path:
            return None
        return FileReplaySource(
            config.replay_path,
            tick_seconds=config.sim_tick_seconds,
            speed=config.replay_speed,
            loop=config.replay_loop,
        )
    if kind is TelemetrySourceKind.WEBSOCKET:
        if not config.websocket_url:
            return None
        return WebSocketSource(config.websocket_url)
    if kind is TelemetrySourceKind.UDP:
        return UdpSource(host=config.udp_host, port=config.udp_port)
    return None


__all__ = [
    "TelemetrySource",
    "TelemetryBus",
    "FrameHandler",
    "SimulatedSource",
    "FileReplaySource",
    "WebSocketSource",
    "UdpSource",
    "build_source",
]
