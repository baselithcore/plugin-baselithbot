"""Fingerprint cache store for differential scans.

Looks up the most recent successful scan with a given input fingerprint
and returns its ``scan_id`` so the orchestrator can reuse findings
without re-running the scanner.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from core.observability.logging import get_logger

from ._conn import acquire

logger = get_logger(__name__)


class FingerprintStore:
    """Async store for ``red_agent_scan_fingerprints``."""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn

    @property
    def available(self) -> bool:
        return bool(self.dsn)

    async def lookup(
        self,
        *,
        fingerprint: str,
        scanner: str,
        ttl_seconds: int,
        tenant_id: str | None = None,
    ) -> UUID | None:
        """Return the cached scan_id when the fingerprint is still fresh.

        ``tenant_id`` filter prevents cache leakage across tenants when
        two scans coincidentally share inputs (e.g. publicly hosted
        target value).
        """
        if not self.available:
            return None
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=max(0, ttl_seconds))
        try:
            async with acquire(self.dsn) as conn:
                row = await (
                    await conn.execute(
                        """
                        SELECT scan_id FROM red_agent_scan_fingerprints
                        WHERE fingerprint = %s
                          AND scanner = %s
                          AND completed_at >= %s
                          AND (tenant_id IS NOT DISTINCT FROM %s)
                        ORDER BY completed_at DESC
                        LIMIT 1
                        """,
                        (fingerprint, scanner, cutoff, tenant_id),
                    )
                ).fetchone()
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.fingerprint.lookup_failed",
                extra={"err": str(e), "scanner": scanner},
            )
            return None
        if not row:
            return None
        scan_id = row["scan_id"]
        if isinstance(scan_id, UUID):
            return scan_id
        try:
            return UUID(str(scan_id))
        except ValueError:
            return None

    async def upsert(
        self,
        *,
        fingerprint: str,
        scanner: str,
        scan_id: UUID,
        tenant_id: str | None = None,
    ) -> None:
        if not self.available:
            return
        try:
            async with acquire(self.dsn) as conn:
                await conn.execute(
                    """
                    INSERT INTO red_agent_scan_fingerprints
                      (fingerprint, scanner, scan_id, tenant_id, completed_at)
                    VALUES (%s, %s, %s, %s, now())
                    ON CONFLICT (fingerprint, scanner) DO UPDATE
                      SET scan_id = EXCLUDED.scan_id,
                          tenant_id = EXCLUDED.tenant_id,
                          completed_at = now()
                    """,
                    (fingerprint, scanner, str(scan_id), tenant_id),
                )
                await conn.commit()
        except Exception as e:  # noqa: BLE001
            logger.warning(
                "red_agent.fingerprint.upsert_failed",
                extra={"err": str(e), "scanner": scanner},
            )
