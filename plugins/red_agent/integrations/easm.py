"""External EASM connector interface.

The Red Agent ships two built-in OSINT scanners (subfinder, crt.sh)
that produce *passive discovery findings*. Many enterprise customers
already operate a dedicated External Attack Surface Management
product — Microsoft Defender EASM, Tenable ASM, Cycognito, Randori —
and want its inventory merged into the Red Agent's target catalog
rather than rebuilding the same enumeration in-house.

This module defines the strategy interface so future connectors can
be plugged in without touching the orchestrator. None ship today; the
``NoneEASMConnector`` is the no-op default and the only implementation
``OSINTConfig.osint_external_easm_provider`` resolves to.

A connector returns a list of :class:`DiscoveredAsset` records. The
ingestion path (``integrations.osint_ingestion``) is responsible for
deduping against existing targets and gating auto-promotion behind
the operator policy.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class DiscoveredAsset:
    """A single host/asset surfaced by an EASM source.

    Discovery sources are heterogeneous (CT logs, Shodan banners,
    cloud asset graphs); the shape is deliberately minimal so every
    backend can map onto it without bespoke conversion logic in the
    orchestrator.
    """

    host: str
    """Lowercased FQDN. The primary key."""

    source: str
    """Connector / scanner identifier (e.g. ``subfinder``, ``crtsh``,
    ``defender_easm``). Useful for provenance + UI filtering."""

    discovered_at: datetime
    """First time this connector saw the host."""

    confidence: float = 1.0
    """In ``[0, 1]``. ``1.0`` for direct CT/DNS evidence; lower values
    let probabilistic sources (search engine scrape, OSINT aggregator
    inference) flag uncertainty."""

    apex: str | None = None
    """Apex this host rolls up to, if known."""

    metadata: dict[str, Any] = field(default_factory=dict)
    """Connector-specific bag — ip addresses, open ports, ASN, tags."""


class EASMConnector(ABC):
    """Strategy interface for an external EASM ingestion source."""

    name: str = ""

    @abstractmethod
    async def discover(self, *, apex: str) -> list[DiscoveredAsset]:
        """Return assets the upstream EASM associates with ``apex``.

        Implementations must be fail-open: any HTTP / auth / parse
        error converts to an empty list (with a warning log). The
        orchestrator merges the result with built-in scanner output;
        a flaky connector must never break a scan.
        """


class NoneEASMConnector(EASMConnector):
    """No-op connector returned when no provider is configured."""

    name = "none"

    async def discover(self, *, apex: str) -> list[DiscoveredAsset]:
        return []


_REGISTRY: dict[str, type[EASMConnector]] = {
    "none": NoneEASMConnector,
}


def register_easm_connector(name: str, cls: type[EASMConnector]) -> None:
    """Register a connector class under ``name``.

    Used by future built-in implementations and by tests to install
    fakes. The default registry only contains the no-op connector.
    """

    _REGISTRY[name] = cls


def get_easm_connector(name: str | None) -> EASMConnector:
    """Resolve a connector instance by name; falls back to no-op.

    Unknown names emit a warning via the caller (kept here as a hard
    fallback so misconfiguration cannot crash a scan).
    """

    if not name:
        return NoneEASMConnector()
    cls = _REGISTRY.get(name.lower(), NoneEASMConnector)
    return cls()
