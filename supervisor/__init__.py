"""Node.js subprocess supervision for the embedded dbview NestJS API.

Split into a package to honour the 500-LOC cap:

* :mod:`.config`  — :class:`SupervisorConfig` + env-driven composition.
* :mod:`.process` — :class:`NodeSupervisor` lifecycle (spawn, health gate,
  keep-alive restarts with backoff, graceful SIGTERM→SIGKILL shutdown).
"""

from .config import SupervisorConfig, build_supervisor_config
from .process import NodeNotAvailableError, NodeSupervisor, StartupTimeoutError

__all__ = [
    "NodeNotAvailableError",
    "NodeSupervisor",
    "StartupTimeoutError",
    "SupervisorConfig",
    "build_supervisor_config",
]
