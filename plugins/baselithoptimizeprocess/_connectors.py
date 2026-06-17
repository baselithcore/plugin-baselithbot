"""Connector mixin: ingest event logs / metrics from text or a remote URL.

Lets BOP pull real data instead of hand-typed input. Text payloads (CSV/JSON)
are parsed by :mod:`.connectors`; remote pulls fetch over HTTP behind the same
SSRF guard the webhook actions use (loopback/private hosts blocked, redirects
disabled), then flow through the normal mining / metric-ingestion paths — so
versioning, audit, monitoring, and guards all apply unchanged.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from core.observability.logging import get_logger

from .connectors import ConnectorParseError, parse_events, parse_samples
from .event_models import MiningResult
from .webhook_security import validate_webhook_url

if TYPE_CHECKING:  # avoid a runtime import cycle with service.py
    from .service import BopService

logger = get_logger(__name__)

# Cap on a pulled payload to avoid unbounded memory from a hostile/huge source.
_MAX_PULL_BYTES = 16 * 1024 * 1024


async def _fetch(url: str) -> str:
    """Fetch text from a URL, SSRF-guarded, size-capped, no redirect following."""
    await validate_webhook_url(url)  # reuse the webhook SSRF guard
    import httpx

    async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
        response = await client.get(url)
        response.raise_for_status()
        body = response.content[:_MAX_PULL_BYTES]
    return body.decode("utf-8", errors="replace")


class ConnectorMixin:
    """Text/URL ingestion behaviour mixed into the BOP service."""

    async def ingest_event_text(
        self, process_id: str, text: str, name: str = "", min_frequency: int = 0
    ) -> MiningResult:
        """Parse a CSV/JSON event log and mine it into the process."""
        events = parse_events(text)
        if not events:
            raise ConnectorParseError("no events parsed from source")
        svc = cast("BopService", self)
        return await svc.import_event_log(process_id, events, name, min_frequency)

    async def ingest_metric_text(self, process_id: str, text: str) -> int:
        """Parse a CSV/JSON metric stream and ingest it as samples."""
        samples = parse_samples(process_id, text)
        if not samples:
            raise ConnectorParseError("no samples parsed from source")
        svc = cast("BopService", self)
        return await svc.ingest_metrics(samples)

    async def pull_events(
        self, process_id: str, url: str, name: str = "", min_frequency: int = 0
    ) -> MiningResult:
        """Fetch a remote event log and mine it into the process."""
        text = await _fetch(url)
        result = await self.ingest_event_text(process_id, text, name, min_frequency)
        logger.info("bop_connector_pull", process_id=process_id, kind="events", url=url)
        return result

    async def pull_metrics(self, process_id: str, url: str) -> int:
        """Fetch a remote metric stream and ingest it as samples."""
        text = await _fetch(url)
        accepted = await self.ingest_metric_text(process_id, text)
        logger.info(
            "bop_connector_pull", process_id=process_id, kind="metrics", url=url
        )
        return accepted


__all__ = ["ConnectorMixin"]
