"""Differential-scan fingerprint + cache tests."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest

from plugins.red_agent._differential import (
    ScanFingerprint,
    apply_cache,
    record_fingerprints,
)
from plugins.red_agent.models import (
    Finding,
    ScanIntensity,
    ScanResult,
    ScanStatus,
    Severity,
    Target,
    TargetType,
)


def _target(meta: dict | None = None) -> Target:
    return Target(
        type=TargetType.URL, value="https://x.example.com", metadata=meta or {}
    )


def _finding(scanner: str, *, target: str = "https://x.example.com") -> Finding:
    return Finding(
        scanner=scanner,
        title="t",
        description="d",
        severity=Severity.MEDIUM,
        target=target,
    )


# --- Fingerprint stability -------------------------------------------


def test_fingerprint_stable_across_calls() -> None:
    t = _target({"commit_sha": "abc", "asset_criticality": "high"})
    a = ScanFingerprint.compute(
        target=t, scanner="trivy", intensity=ScanIntensity.PASSIVE
    )
    b = ScanFingerprint.compute(
        target=t, scanner="trivy", intensity=ScanIntensity.PASSIVE
    )
    assert a.digest == b.digest


def test_fingerprint_changes_with_intensity() -> None:
    t = _target()
    a = ScanFingerprint.compute(
        target=t, scanner="zap", intensity=ScanIntensity.PASSIVE
    )
    b = ScanFingerprint.compute(target=t, scanner="zap", intensity=ScanIntensity.ACTIVE)
    assert a.digest != b.digest


def test_fingerprint_ignores_volatile_metadata() -> None:
    base = _target({"commit_sha": "abc"})
    noisy = _target({"commit_sha": "abc", "last_scan_at": "2026-04-29T10:00:00Z"})
    a = ScanFingerprint.compute(
        target=base, scanner="trivy", intensity=ScanIntensity.PASSIVE
    )
    b = ScanFingerprint.compute(
        target=noisy, scanner="trivy", intensity=ScanIntensity.PASSIVE
    )
    assert a.digest == b.digest


def test_fingerprint_changes_with_commit_sha() -> None:
    a = ScanFingerprint.compute(
        target=_target({"commit_sha": "abc"}),
        scanner="trivy",
        intensity=ScanIntensity.PASSIVE,
    )
    b = ScanFingerprint.compute(
        target=_target({"commit_sha": "def"}),
        scanner="trivy",
        intensity=ScanIntensity.PASSIVE,
    )
    assert a.digest != b.digest


# --- apply_cache ------------------------------------------------------


class _FpStoreStub:
    def __init__(self, *, hits: dict[tuple[str, str], UUID] | None = None) -> None:
        self.available = True
        self._hits = hits or {}
        self.upserts: list[tuple[str, str, UUID, str | None]] = []

    async def lookup(
        self, *, fingerprint: str, scanner: str, ttl_seconds: int, tenant_id: str | None
    ) -> UUID | None:
        del ttl_seconds, tenant_id
        return self._hits.get((fingerprint, scanner))

    async def upsert(
        self, *, fingerprint: str, scanner: str, scan_id: UUID, tenant_id: str | None
    ) -> None:
        self.upserts.append((fingerprint, scanner, scan_id, tenant_id))


class _PersistenceStub:
    def __init__(self, scans: dict[UUID, ScanResult]) -> None:
        self._scans = scans

    async def get_scan(self, scan_id: UUID) -> ScanResult | None:
        return self._scans.get(scan_id)


class _AuditStub:
    def __init__(self) -> None:
        self.events: list[dict] = []

    async def record(self, **kwargs: object) -> None:
        self.events.append(kwargs)


def _step(scanners: list[str], target: Target | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        scanners=scanners,
        target=target or _target(),
        intensity=ScanIntensity.PASSIVE,
    )


def _request(tenant_id: str | None = None) -> SimpleNamespace:
    return SimpleNamespace(tenant_id=tenant_id)


@pytest.mark.asyncio
async def test_apply_cache_disabled_passthrough() -> None:
    store = _FpStoreStub()
    to_run, reused = await apply_cache(
        fingerprints=store,
        persistence=_PersistenceStub({}),
        audit=_AuditStub(),
        scan_id=uuid4(),
        request=_request(),
        step=_step(["trivy", "zap"]),
        ttl_seconds=3600,
        enabled=False,
    )
    assert to_run == ["trivy", "zap"]
    assert reused == []


@pytest.mark.asyncio
async def test_apply_cache_no_hits_runs_all() -> None:
    store = _FpStoreStub()
    audit = _AuditStub()
    to_run, reused = await apply_cache(
        fingerprints=store,
        persistence=_PersistenceStub({}),
        audit=audit,
        scan_id=uuid4(),
        request=_request(),
        step=_step(["trivy", "zap"]),
        ttl_seconds=3600,
        enabled=True,
    )
    assert to_run == ["trivy", "zap"]
    assert reused == []
    assert audit.events == []


@pytest.mark.asyncio
async def test_apply_cache_hit_reuses_findings_and_audits() -> None:
    target = _target({"commit_sha": "abc"})
    fp = ScanFingerprint.compute(
        target=target, scanner="trivy", intensity=ScanIntensity.PASSIVE
    )
    cached_scan_id = uuid4()
    cached_findings = [_finding("trivy"), _finding("trivy"), _finding("zap")]
    cached_scan = ScanResult(
        scan_id=cached_scan_id,
        status=ScanStatus.COMPLETED,
        started_at=datetime.now(timezone.utc),
        findings=cached_findings,
    )
    store = _FpStoreStub(hits={(fp.digest, "trivy"): cached_scan_id})
    persistence = _PersistenceStub({cached_scan_id: cached_scan})
    audit = _AuditStub()

    to_run, reused = await apply_cache(
        fingerprints=store,
        persistence=persistence,
        audit=audit,
        scan_id=uuid4(),
        request=_request(),
        step=_step(["trivy", "zap"], target=target),
        ttl_seconds=3600,
        enabled=True,
    )
    assert to_run == ["zap"]
    # Two trivy findings reused; zap finding ignored (different scanner).
    assert len(reused) == 2
    assert all(f.scanner == "trivy" for f in reused)
    # IDs renewed so reused findings slot into the new scan cleanly.
    assert {f.id for f in reused} != {
        f.id for f in cached_findings if f.scanner == "trivy"
    }
    assert len(audit.events) == 1
    payload = audit.events[0]["payload"]
    assert payload["kept"] == ["zap"]
    assert payload["skipped"][0]["scanner"] == "trivy"


@pytest.mark.asyncio
async def test_apply_cache_falls_through_when_prior_scan_missing() -> None:
    target = _target()
    fp = ScanFingerprint.compute(
        target=target, scanner="trivy", intensity=ScanIntensity.PASSIVE
    )
    cached_scan_id = uuid4()
    # Hit the lookup but the prior ScanResult is gone (cascade-deleted, etc).
    store = _FpStoreStub(hits={(fp.digest, "trivy"): cached_scan_id})
    persistence = _PersistenceStub({})
    to_run, reused = await apply_cache(
        fingerprints=store,
        persistence=persistence,
        audit=_AuditStub(),
        scan_id=uuid4(),
        request=_request(),
        step=_step(["trivy"], target=target),
        ttl_seconds=3600,
        enabled=True,
    )
    assert to_run == ["trivy"]
    assert reused == []


# --- record_fingerprints ---------------------------------------------


@pytest.mark.asyncio
async def test_record_fingerprints_upserts_each_scanner() -> None:
    store = _FpStoreStub()
    scan_id = uuid4()
    target = _target({"commit_sha": "abc"})
    await record_fingerprints(
        fingerprints=store,
        scan_id=scan_id,
        request=_request(tenant_id="acme"),
        step=_step(["trivy", "zap"], target=target),
        scanners_ran=["trivy", "zap"],
        enabled=True,
    )
    assert len(store.upserts) == 2
    scanners_recorded = {u[1] for u in store.upserts}
    assert scanners_recorded == {"trivy", "zap"}
    assert all(u[3] == "acme" for u in store.upserts)


@pytest.mark.asyncio
async def test_record_fingerprints_disabled_noop() -> None:
    store = _FpStoreStub()
    await record_fingerprints(
        fingerprints=store,
        scan_id=uuid4(),
        request=_request(),
        step=_step(["trivy"]),
        scanners_ran=["trivy"],
        enabled=False,
    )
    assert store.upserts == []


@pytest.mark.asyncio
async def test_record_fingerprints_skips_when_no_scanners_ran() -> None:
    store = _FpStoreStub()
    await record_fingerprints(
        fingerprints=store,
        scan_id=uuid4(),
        request=_request(),
        step=_step(["trivy"]),
        scanners_ran=[],
        enabled=True,
    )
    assert store.upserts == []
