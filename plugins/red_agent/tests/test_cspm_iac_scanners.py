"""Parser tests for the CSPM/IaC scanner adapters (Checkov, Prowler, kube-bench)."""

from __future__ import annotations

import json

import pytest

from plugins.red_agent.models import Severity, Target, TargetType
from plugins.red_agent.scanners.checkov import CheckovScanner
from plugins.red_agent.scanners.kube_bench import KubeBenchScanner
from plugins.red_agent.scanners.prowler import ProwlerScanner


class _StubSandbox:
    pass


@pytest.fixture()
def iac_target() -> Target:
    return Target(type=TargetType.IAC, value="/repo/main.tf")


@pytest.fixture()
def cloud_target() -> Target:
    return Target(
        type=TargetType.CLOUD_ACCOUNT,
        value="aws:123456789012",
        metadata={"provider": "aws"},
    )


@pytest.fixture()
def k8s_target() -> Target:
    return Target(type=TargetType.K8S_CLUSTER, value="kube-control-plane")


# --- Checkov ----------------------------------------------------------


def test_checkov_parses_failed_check(iac_target: Target) -> None:
    payload = json.dumps(
        {
            "results": {
                "failed_checks": [
                    {
                        "check_id": "CKV_AWS_18",
                        "bc_check_id": "BC_AWS_S3_15",
                        "check_name": "Ensure S3 bucket has access logging",
                        "severity": "MEDIUM",
                        "resource": "aws_s3_bucket.demo",
                        "file_path": "/main.tf",
                        "file_line_range": [3, 9],
                        "guideline": "https://docs.bridgecrew.io/docs/s3_13",
                    }
                ]
            }
        }
    )
    s = CheckovScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]
    findings = s._parse(payload, iac_target)
    assert len(findings) == 1
    f = findings[0]
    assert f.scanner == "checkov"
    assert f.severity == Severity.MEDIUM
    assert "CKV_AWS_18" in f.title
    assert f.endpoint == "/main.tf#L3-9"
    assert f.evidence["resource"] == "aws_s3_bucket.demo"


def test_checkov_handles_multi_framework_array(iac_target: Target) -> None:
    payload = json.dumps(
        [
            {
                "results": {
                    "failed_checks": [{"check_id": "CKV_K8S_1", "severity": "HIGH"}]
                }
            },
            {
                "results": {
                    "failed_checks": [{"check_id": "CKV_DOCKER_1", "severity": "LOW"}]
                }
            },
        ]
    )
    s = CheckovScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]
    findings = s._parse(payload, iac_target)
    assert len(findings) == 2
    assert {f.severity for f in findings} == {Severity.HIGH, Severity.LOW}


def test_checkov_returns_empty_on_garbage(iac_target: Target) -> None:
    s = CheckovScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]
    assert s._parse("<not-json>", iac_target) == []


# --- Prowler ----------------------------------------------------------


def test_prowler_parses_ocsf_event(cloud_target: Target) -> None:
    payload = json.dumps(
        [
            {
                "finding_info": {
                    "uid": "prowler-001",
                    "title": "S3 bucket missing encryption",
                    "desc": "Buckets should enable SSE-KMS",
                },
                "severity": "HIGH",
                "compliance": {"CIS-1.5": "2.1.1"},
                "resources": [{"uid": "arn:aws:s3:::demo"}],
                "cloud": {"region": "us-east-1", "account": {"uid": "123456789012"}},
            }
        ]
    )
    s = ProwlerScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]
    findings = s._parse(payload, cloud_target)
    assert len(findings) == 1
    f = findings[0]
    assert f.severity == Severity.HIGH
    assert f.scanner == "prowler"
    assert f.evidence["account"] == "123456789012"
    assert f.evidence["region"] == "us-east-1"
    assert f.evidence["compliance"] == {"CIS-1.5": "2.1.1"}


def test_prowler_parses_legacy_shape(cloud_target: Target) -> None:
    payload = json.dumps(
        [
            {
                "CheckID": "iam_password_policy",
                "CheckTitle": "Password policy requires minimum length",
                "StatusExtended": "Length is 8",
                "Severity": "medium",
                "ServiceName": "iam",
                "Region": "us-east-1",
                "ResourceName": "policy",
                "Compliance": ["CIS-1.5/1.8"],
                "Remediation": {
                    "Recommendation": {"Text": "Increase password length to 14"}
                },
            }
        ]
    )
    s = ProwlerScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]
    findings = s._parse(payload, cloud_target)
    assert len(findings) == 1
    assert findings[0].severity == Severity.MEDIUM
    assert findings[0].remediation == "Increase password length to 14"
    assert findings[0].evidence["service"] == "iam"


def test_prowler_resolves_provider_from_target_value() -> None:
    s = ProwlerScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]
    aws_t = Target(type=TargetType.CLOUD_ACCOUNT, value="aws:123")
    azure_t = Target(type=TargetType.CLOUD_ACCOUNT, value="azure:tenant")
    gcp_t = Target(type=TargetType.CLOUD_ACCOUNT, value="gcp:proj")
    k8s_t = Target(type=TargetType.K8S_CLUSTER, value="prod")

    from plugins.red_agent.scanners.prowler import _resolve_provider

    assert _resolve_provider(aws_t) == "aws"
    assert _resolve_provider(azure_t) == "azure"
    assert _resolve_provider(gcp_t) == "gcp"
    assert _resolve_provider(k8s_t) == "kubernetes"
    del s  # keep ruff happy on unused fixture-side stub


# --- kube-bench -------------------------------------------------------


def test_kube_bench_parses_fail_only(k8s_target: Target) -> None:
    payload = json.dumps(
        {
            "Controls": [
                {
                    "id": "1",
                    "version": "cis-1.7",
                    "tests": [
                        {
                            "results": [
                                {
                                    "test_number": "1.2.6",
                                    "test_desc": "kubelet certificate authority",
                                    "status": "FAIL",
                                    "audit": "ps -ef",
                                    "expected_result": "set",
                                    "actual_value": "not set",
                                    "remediation": "Edit manifest",
                                    "scored": True,
                                },
                                {
                                    "test_number": "1.2.7",
                                    "test_desc": "always pull images",
                                    "status": "PASS",
                                },
                                {
                                    "test_number": "1.2.8",
                                    "test_desc": "anonymous auth disabled",
                                    "status": "WARN",
                                },
                            ]
                        }
                    ],
                }
            ]
        }
    )
    s = KubeBenchScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]
    findings = s._parse(payload, k8s_target)
    # PASS dropped, FAIL + WARN kept
    assert len(findings) == 2
    severities = {f.severity for f in findings}
    assert Severity.HIGH in severities
    assert Severity.LOW in severities


def test_kube_bench_returns_empty_on_garbage(k8s_target: Target) -> None:
    s = KubeBenchScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]
    assert s._parse("not-json", k8s_target) == []
