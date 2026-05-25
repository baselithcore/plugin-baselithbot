"""Unit tests for CVE Hunter Pydantic models."""

from datetime import timezone

import pytest

from plugins.cve_hunter.models import (
    CVERecord,
    CVESeverity,
    CVESource,
    VulnerabilityAlert,
)


pytestmark = pytest.mark.unit


def _make_cve(cve_id: str = "CVE-2099-0001") -> CVERecord:
    return CVERecord(
        cve_id=cve_id,
        title="Sample",
        description="Demo CVE used for unit tests.",
        severity=CVESeverity.HIGH,
        source=CVESource.NVD,
    )


def test_alert_default_created_at_is_utc_aware():
    alert = VulnerabilityAlert(alert_id="a1", cve=_make_cve())
    assert alert.created_at.tzinfo is not None
    assert alert.created_at.utcoffset() == timezone.utc.utcoffset(alert.created_at)


def test_cve_record_severity_enum_value():
    cve = _make_cve()
    assert cve.severity.value == "high"
    assert cve.cvss_score == 0.0  # No CVSS attached.
