"""Identity scanner parser + plumbing tests."""

from __future__ import annotations

import json
from typing import Any

import pytest
from pydantic import SecretStr

from plugins.red_agent._credential_resolver import (
    CredentialResolutionError,
    IdentityCredential,
    MetadataBackend,
    get_backend,
    register_backend,
    resolve_credentials,
)
from plugins.red_agent.models import Severity, Target, TargetType
from plugins.red_agent.scanners._identity_base import (
    credentials_to_env,
    passive_blocked,
)
from plugins.red_agent.scanners.bloodhound import BloodHoundScanner
from plugins.red_agent.scanners.certipy import CertipyScanner
from plugins.red_agent.scanners.roadrecon import ROADReconScanner
from plugins.red_agent.models import ScanIntensity


def _ad_target() -> Target:
    return Target(
        type=TargetType.AD_DOMAIN,
        value="corp.example.com",
        metadata={
            "domain_controller": "10.0.0.1",
            "credentials": {
                "username": "svc_audit",
                "password": "p@ss",
                "domain": "CORP",
            },
        },
    )


def _entra_target() -> Target:
    return Target(
        type=TargetType.ENTRA_TENANT,
        value="contoso.onmicrosoft.com",
        metadata={
            "credentials": {
                "username": "audit",
                "password": "p@ss",
            }
        },
    )


def test_passive_blocked() -> None:
    assert passive_blocked(ScanIntensity.PASSIVE) is True
    assert passive_blocked(ScanIntensity.ACTIVE) is False
    assert passive_blocked(ScanIntensity.INTRUSIVE) is False


def test_credentials_to_env_omits_empty_fields() -> None:
    cred = IdentityCredential(
        username="svc",
        password=SecretStr("hunter2"),
        domain="CORP",
        refresh_token=None,
    )
    env = credentials_to_env(cred)
    assert env == {
        "RA_USERNAME": "svc",
        "RA_PASSWORD": "hunter2",
        "RA_DOMAIN": "CORP",
    }


@pytest.mark.asyncio
async def test_metadata_backend_resolves_credentials() -> None:
    cred = await resolve_credentials(
        backend_name="metadata",
        target=_ad_target(),
        credentials_ref=None,
    )
    assert cred.username == "svc_audit"
    assert cred.password is not None and cred.password.get_secret_value() == "p@ss"
    assert cred.domain == "CORP"


@pytest.mark.asyncio
async def test_metadata_backend_raises_when_creds_missing() -> None:
    target = Target(type=TargetType.AD_DOMAIN, value="corp.example.com", metadata={})
    with pytest.raises(CredentialResolutionError):
        await MetadataBackend().resolve(target=target, credentials_ref=None)


def test_get_backend_falls_back_to_metadata() -> None:
    assert isinstance(get_backend("does-not-exist"), MetadataBackend)
    assert isinstance(get_backend(""), MetadataBackend)


def test_register_backend_install_and_resolve() -> None:
    class _Stub(MetadataBackend):
        name = "stub"

    register_backend("stub", _Stub)
    try:
        assert isinstance(get_backend("stub"), _Stub)
    finally:
        register_backend("stub", MetadataBackend)


# --- BloodHound parser ---


def test_bloodhound_parses_kerberoast_and_unconstrained() -> None:
    sc = BloodHoundScanner.__new__(BloodHoundScanner)
    sc.name = "bloodhound"
    blob = json.dumps(
        {
            "data": [
                {
                    "ObjectIdentifier": "S-1-5-21-1-1",
                    "Properties": {
                        "samaccountname": "svc_sql",
                        "enabled": True,
                        "kerberoastable": True,
                        "serviceprincipalnames": ["MSSQLSvc/sql.corp"],
                    },
                },
                {
                    "ObjectIdentifier": "S-1-5-21-1-2",
                    "Properties": {
                        "samaccountname": "legacy",
                        "enabled": True,
                        "dontreqpreauth": True,
                    },
                },
                {
                    "ObjectIdentifier": "S-1-5-21-1-3",
                    "Properties": {
                        "samaccountname": "WORKSTATION$",
                        "enabled": True,
                        "unconstraineddelegation": True,
                    },
                },
                {
                    "ObjectIdentifier": "S-1-5-21-1-4",
                    "Properties": {
                        "samaccountname": "disabled_user",
                        "enabled": False,
                        "kerberoastable": True,
                    },
                },
            ]
        }
    )

    findings = sc._parse_users(blob, _ad_target())  # type: ignore[attr-defined]

    titles = sorted(f.title for f in findings)
    assert "Kerberoastable account: svc_sql" in titles
    assert "AS-REProastable account: legacy" in titles
    assert any(t.startswith("Unconstrained delegation:") for t in titles)
    # disabled user must be excluded
    assert not any("disabled_user" in t for t in titles)


def test_bloodhound_parser_handles_invalid_json() -> None:
    sc = BloodHoundScanner.__new__(BloodHoundScanner)
    sc.name = "bloodhound"
    assert sc._parse_users("not-json", _ad_target()) == []  # type: ignore[attr-defined]
    assert sc._parse_users("", _ad_target()) == []  # type: ignore[attr-defined]


# --- Certipy parser ---


def test_certipy_parses_esc_vulnerabilities() -> None:
    sc = CertipyScanner.__new__(CertipyScanner)
    sc.name = "certipy"
    blob = json.dumps(
        {
            "Certificate Templates": {
                "WebServer": {
                    "Enabled": True,
                    "Certificate Authorities": ["CA-1"],
                    "[!] Vulnerabilities": {
                        "ESC1": "Enrollee supplies subject; client auth EKU.",
                    },
                },
                "PKINIT": {
                    "Enabled": True,
                    "Certificate Authorities": ["CA-1"],
                    "Vulnerabilities": {
                        "ESC9": "No StrongCertBinding enforcement.",
                    },
                },
                "Boring": {"Enabled": True},
            }
        }
    )

    findings = sc._parse(blob, _ad_target())  # type: ignore[attr-defined]
    by_esc = {f.evidence["esc"]: f for f in findings}

    assert by_esc["ESC1"].severity == Severity.CRITICAL
    assert by_esc["ESC9"].severity == Severity.HIGH
    assert all(f.scanner == "certipy" for f in findings)


# --- ROADrecon parser ---


def test_roadrecon_flags_privileged_role_without_mfa() -> None:
    sc = ROADReconScanner.__new__(ROADReconScanner)
    sc.name = "roadrecon"
    payload: dict[str, Any] = {
        "directoryroles": [
            {
                "displayName": "Global Administrator",
                "members": [
                    {"id": "u1", "userPrincipalName": "alice@contoso"},
                    {"id": "u2", "userPrincipalName": "bob@contoso"},
                ],
            }
        ],
        "authmethods": [{"userId": "u1", "isMfaRegistered": True}],
        "applications": [],
    }

    findings = sc._parse(json.dumps(payload), _entra_target())  # type: ignore[attr-defined]

    assert len(findings) == 1
    assert "bob@contoso" in findings[0].title
    assert findings[0].severity == Severity.CRITICAL


def test_roadrecon_flags_over_permissioned_app() -> None:
    sc = ROADReconScanner.__new__(ROADReconScanner)
    sc.name = "roadrecon"
    payload = {
        "directoryroles": [],
        "authmethods": [],
        "applications": [
            {
                "displayName": "LegacyTool",
                "appId": "00000000-0000-0000-0000-000000000001",
                "requiredResourceAccess": [
                    {
                        "resourceAccess": [
                            {"value": "Directory.ReadWrite.All", "type": "Role"},
                            {"value": "User.Read", "type": "Scope"},
                        ]
                    }
                ],
            }
        ],
    }

    findings = sc._parse(json.dumps(payload), _entra_target())  # type: ignore[attr-defined]

    assert len(findings) == 1
    assert "Directory.ReadWrite.All" in findings[0].evidence["permissions"]
    assert findings[0].severity == Severity.HIGH
