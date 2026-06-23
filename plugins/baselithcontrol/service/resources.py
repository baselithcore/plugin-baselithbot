"""Process- and host-level resource sampling for the control plane.

The framework and every plugin run **in one Python process**, so per-plugin
CPU/RAM cannot be honestly isolated (the OS only accounts the whole process).
This sampler therefore reports truthful *framework-wide* resource usage via
``psutil`` — process CPU/RSS, host CPU/memory, threads, open file descriptors,
network throughput (rate-derived between samples), and host uptime (since the
machine booted, via ``psutil.boot_time()`` — not since the dashboard opened).
Per-plugin signal
is exposed separately as request telemetry (see :mod:`plugin_meter`).

A single long-lived :class:`ResourceSampler` is kept so CPU-percent and network
rates are computed as deltas across successive polls. Everything degrades to
``None`` when ``psutil`` is unavailable — the dashboard simply hides the gauges.
"""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from typing import Any

try:  # psutil is a hard dep, but never let a probe failure break the dashboard
    import psutil

    _PROC: Any = psutil.Process(os.getpid())
except Exception:  # noqa: BLE001 — optional/degraded environments
    psutil = None  # type: ignore[assignment]
    _PROC = None


@dataclass(frozen=True)
class _NetSnap:
    t: float
    sent: int
    recv: int


class ResourceSampler:
    """Stateful sampler computing process/host gauges and rates across polls."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._net: _NetSnap | None = None
        self._started = time.time()
        # Prime CPU-percent counters so the first real sample is meaningful
        # (psutil's first cpu_percent() call always returns 0.0).
        if _PROC is not None:
            try:
                _PROC.cpu_percent(None)
                psutil.cpu_percent(None)  # type: ignore[union-attr]
            except Exception:  # noqa: BLE001
                pass

    @property
    def available(self) -> bool:
        return _PROC is not None

    def _net_rates(self) -> tuple[float | None, float | None, int | None, int | None]:
        """Return (sent_bps, recv_bps, total_sent, total_recv) since last poll."""
        if psutil is None:
            return None, None, None, None
        try:
            io = psutil.net_io_counters()
        except Exception:  # noqa: BLE001 — not all platforms expose this
            return None, None, None, None
        now = time.time()
        with self._lock:
            prev = self._net
            self._net = _NetSnap(now, io.bytes_sent, io.bytes_recv)
        if prev is None:
            return 0.0, 0.0, io.bytes_sent, io.bytes_recv
        dt = max(now - prev.t, 1e-3)
        sent_bps = max(0.0, (io.bytes_sent - prev.sent) / dt)
        recv_bps = max(0.0, (io.bytes_recv - prev.recv) / dt)
        return sent_bps, recv_bps, io.bytes_sent, io.bytes_recv

    def _host_uptime_seconds(self) -> float:
        """Seconds since the **host** booted (not the dashboard/process start).

        Falls back to this process's own uptime when ``psutil.boot_time()`` is
        unavailable, so the gauge degrades gracefully instead of vanishing.
        """
        if psutil is not None:
            try:
                return max(0.0, time.time() - float(psutil.boot_time()))
            except Exception:  # noqa: BLE001 — sandboxed/unsupported platforms
                pass
        return time.time() - self._started

    def sample(self) -> dict[str, float | int | None]:
        """Take one resource snapshot. All fields are ``None`` when unavailable."""
        out: dict[str, float | int | None] = {
            "available": self.available,
            "uptime_seconds": round(self._host_uptime_seconds(), 1),
        }
        if _PROC is None or psutil is None:
            return out

        try:
            with _PROC.oneshot():
                out["cpu_percent"] = round(_PROC.cpu_percent(None), 1)
                mem = _PROC.memory_info()
                out["rss_bytes"] = int(mem.rss)
                out["threads"] = int(_PROC.num_threads())
                try:
                    out["open_fds"] = int(_PROC.num_fds())  # POSIX only
                except Exception:  # noqa: BLE001 — Windows/macOS sandbox
                    out["open_fds"] = None
        except Exception:  # noqa: BLE001
            pass

        try:
            vm = psutil.virtual_memory()
            out["mem_total_bytes"] = int(vm.total)
            out["mem_available_bytes"] = int(vm.available)
            out["mem_percent"] = round(float(vm.percent), 1)
            rss = out.get("rss_bytes")
            if isinstance(rss, int) and vm.total:
                out["rss_percent"] = round(rss / vm.total * 100, 1)
        except Exception:  # noqa: BLE001
            pass

        try:
            out["host_cpu_percent"] = round(float(psutil.cpu_percent(None)), 1)
            out["cpu_count"] = int(psutil.cpu_count(logical=True) or 0)
        except Exception:  # noqa: BLE001
            pass

        sent_bps, recv_bps, tx, rx = self._net_rates()
        out["net_sent_bps"] = round(sent_bps, 1) if sent_bps is not None else None
        out["net_recv_bps"] = round(recv_bps, 1) if recv_bps is not None else None
        out["net_sent_bytes"] = tx
        out["net_recv_bytes"] = rx
        return out


_SAMPLER: ResourceSampler | None = None
_SAMPLER_LOCK = threading.Lock()


def get_resource_sampler() -> ResourceSampler:
    """Return the process-wide singleton sampler (built on first use)."""
    global _SAMPLER
    if _SAMPLER is None:
        with _SAMPLER_LOCK:
            if _SAMPLER is None:
                _SAMPLER = ResourceSampler()
    return _SAMPLER


__all__ = ["ResourceSampler", "get_resource_sampler"]
