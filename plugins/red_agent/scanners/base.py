"""Scanner abstract interface."""

from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from plugins.red_agent.models import Finding, ScanIntensity, Target

if TYPE_CHECKING:
    from plugins.red_agent.sandbox_runner import SandboxRunner


class ScannerKind(str, enum.Enum):
    RECON = "recon"
    DAST = "dast"
    SAST = "sast"
    SCA = "sca"
    SECRET = "secret"
    CSPM = "cspm"
    CONFIG = "config"
    THREAT_INTEL = "threat_intel"
    TLS = "tls"
    HEADERS = "headers"
    SBOM = "sbom"
    OSINT = "osint"
    IDENTITY = "identity"


class Scanner(ABC):
    """
    Abstract scanner interface. Every concrete scanner runs inside a
    SandboxRunner — adapters never call subprocess directly.
    """

    name: str = ""
    kind: ScannerKind = ScannerKind.RECON
    supports_intensity: tuple[ScanIntensity, ...] = (ScanIntensity.PASSIVE,)
    image: str = ""
    requires_network: bool = True
    default_timeout: int = 600

    def __init__(self, sandbox: SandboxRunner, timeout: int | None = None) -> None:
        self.sandbox = sandbox
        self.timeout = timeout if timeout is not None else self.default_timeout

    @abstractmethod
    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        """Execute scan and return normalized findings."""

    def supports(self, intensity: ScanIntensity) -> bool:
        return intensity in self.supports_intensity
