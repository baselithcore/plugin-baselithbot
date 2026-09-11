"""Node.js subprocess supervision for the embedded dbview NestJS API.

Split into a package to honour the 500-LOC cap:

* :mod:`.config`    — :class:`SupervisorConfig` + env-driven composition.
* :mod:`.launcher`  — pre-exec hardening: the child dies with its supervisor
  and inherits none of the host's descriptors.
* :mod:`.portguard` — pre-spawn ownership check on the shared upstream port.
* :mod:`.process`   — :class:`NodeSupervisor` lifecycle (spawn, health gate,
  keep-alive restarts with backoff, graceful SIGTERM→SIGKILL shutdown).
"""

from .config import SupervisorConfig, build_supervisor_config
from .launcher import build_launch_argv
from .portguard import PortUnavailableError
from .process import NodeNotAvailableError, NodeSupervisor, StartupTimeoutError

__all__ = [
    "NodeNotAvailableError",
    "NodeSupervisor",
    "PortUnavailableError",
    "StartupTimeoutError",
    "SupervisorConfig",
    "build_launch_argv",
    "build_supervisor_config",
]
