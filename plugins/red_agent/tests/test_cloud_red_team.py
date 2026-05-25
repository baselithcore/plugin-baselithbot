"""Cloud red-team scanner parser tests."""

from __future__ import annotations

import json

from plugins.red_agent.models import Severity, Target, TargetType
from plugins.red_agent.scanners.azurehound import AzureHoundScanner
from plugins.red_agent.scanners.pmapper import PMapperScanner
from plugins.red_agent.scanners.scoutsuite import ScoutSuiteScanner


def _aws_target() -> Target:
    return Target(type=TargetType.CLOUD_ACCOUNT, value="123456789012")


def _entra_target() -> Target:
    return Target(type=TargetType.ENTRA_TENANT, value="contoso.onmicrosoft.com")


# --- pmapper ---


def test_pmapper_parses_critical_path() -> None:
    sc = PMapperScanner.__new__(PMapperScanner)
    sc.name = "pmapper"
    blob = json.dumps(
        {
            "privesc_paths": [
                {
                    "source": "arn:aws:iam::1:user/alice",
                    "destination": "arn:aws:iam::1:role/Admin",
                    "edges": [
                        {
                            "action": "iam:*",
                            "via": "AttachUserPolicy",
                        }
                    ],
                }
            ],
            "nodes": [],
        }
    )

    findings = sc._parse(blob, _aws_target())  # type: ignore[attr-defined]

    assert len(findings) == 1
    assert findings[0].severity == Severity.CRITICAL
    assert "iam:*" in findings[0].evidence["risky_actions"]


def test_pmapper_flags_admin_attached_principal() -> None:
    sc = PMapperScanner.__new__(PMapperScanner)
    sc.name = "pmapper"
    blob = json.dumps(
        {
            "privesc_paths": [],
            "nodes": [
                {
                    "arn": "arn:aws:iam::1:user/breakglass",
                    "attached_policies": [
                        "arn:aws:iam::aws:policy/AdministratorAccess"
                    ],
                }
            ],
        }
    )

    findings = sc._parse(blob, _aws_target())  # type: ignore[attr-defined]
    assert len(findings) == 1
    assert (
        "arn:aws:iam::aws:policy/AdministratorAccess"
        in findings[0].evidence["policies"]
    )
    assert findings[0].severity == Severity.HIGH


def test_pmapper_invalid_json_returns_empty() -> None:
    sc = PMapperScanner.__new__(PMapperScanner)
    sc.name = "pmapper"
    assert sc._parse("not-json", _aws_target()) == []  # type: ignore[attr-defined]


# --- scoutsuite ---


def test_scoutsuite_parses_danger_findings_with_items() -> None:
    sc = ScoutSuiteScanner.__new__(ScoutSuiteScanner)
    sc.name = "scoutsuite"
    payload = {
        "services": {
            "iam": {
                "findings": {
                    "iam-no-mfa-on-root": {
                        "level": "danger",
                        "description": "Root MFA missing",
                        "rationale": "Root account without MFA.",
                        "remediation": "Enable MFA.",
                        "items": ["root"],
                    },
                    "iam-info-rule": {
                        "level": "info",
                        "description": "Note",
                        "items": ["x"],
                    },
                    "iam-empty-rule": {
                        "level": "warning",
                        "description": "n/a",
                        "items": [],
                    },
                }
            }
        }
    }
    artifacts = {"x.js": json.dumps(payload)}

    findings = sc._parse(artifacts, _aws_target(), "aws")  # type: ignore[attr-defined]

    severities = {f.title: f.severity for f in findings}
    assert any("Root MFA missing" in t for t in severities)
    danger_titles = [t for t in severities if "Root MFA missing" in t]
    assert severities[danger_titles[0]] == Severity.HIGH
    # info-level rule with non-empty items still emits an INFO finding.
    assert any(f.severity == Severity.INFO for f in findings)
    # warning rule with empty items must NOT emit anything.
    assert not any("n/a" in (f.description or "") for f in findings)


def test_scoutsuite_strips_js_wrapper() -> None:
    sc = ScoutSuiteScanner.__new__(ScoutSuiteScanner)
    sc.name = "scoutsuite"
    payload = {"services": {}}
    blob = "scoutsuite_results = " + json.dumps(payload) + ";"
    artifacts = {"x.js": blob}
    findings = sc._parse(artifacts, _aws_target(), "aws")  # type: ignore[attr-defined]
    assert findings == []


# --- azurehound ---


def test_azurehound_parses_privileged_role_assignment() -> None:
    sc = AzureHoundScanner.__new__(AzureHoundScanner)
    sc.name = "azurehound"
    lines = [
        json.dumps(
            {
                "kind": "AZRoleAssignment",
                "data": {
                    "roleName": "Owner",
                    "principalId": "pid-123",
                    "scope": "/subscriptions/abc",
                },
            }
        ),
        json.dumps(
            {
                "kind": "AZRoleAssignment",
                "data": {
                    "roleName": "Reader",
                    "principalId": "pid-x",
                    "scope": "/subscriptions/abc",
                },
            }
        ),
    ]

    findings = sc._parse("\n".join(lines), _entra_target())  # type: ignore[attr-defined]

    assert len(findings) == 1
    assert "Owner" in findings[0].title
    assert findings[0].severity == Severity.HIGH


def test_azurehound_parses_wildcard_custom_role() -> None:
    sc = AzureHoundScanner.__new__(AzureHoundScanner)
    sc.name = "azurehound"
    line = json.dumps(
        {
            "kind": "AZRoleDefinition",
            "data": {
                "roleName": "BadCustom",
                "permissions": [{"actions": ["*"]}],
            },
        }
    )

    findings = sc._parse(line, _entra_target())  # type: ignore[attr-defined]

    assert len(findings) == 1
    assert "BadCustom" in findings[0].title
    assert "*" in findings[0].evidence["actions"]


def test_azurehound_parser_skips_invalid_jsonl_lines() -> None:
    sc = AzureHoundScanner.__new__(AzureHoundScanner)
    sc.name = "azurehound"
    blob = "{not-json}\n" + json.dumps({"kind": "Other", "data": {"x": 1}})
    findings = sc._parse(blob, _entra_target())  # type: ignore[attr-defined]
    assert findings == []
