"""Deterministic mock sandbox for development and demos.

When the operator opts into ``RED_AGENT_USE_MOCK_SCANNERS=true``, the plugin
swaps the real :class:`SandboxRunner` for :class:`MockSandboxRunner`. The
mock returns canned, scanner-shaped output so the UI lights up with
findings within a few seconds — no docker, no network, no scanner binaries
to install.

This is **not** a security control: it is a productivity affordance for
operators iterating on the UI/lifecycle. Real environments leave the flag
off and run the actual sandboxed binaries.
"""

from __future__ import annotations

import asyncio
import json
import random
from typing import Any, Callable

from core.observability.logging import get_logger
from plugins.red_agent.sandbox_runner import SandboxResult

logger = get_logger(__name__)


_NMAP_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<nmaprun>
  <host>
    <address addr="{host}" addrtype="ipv4"/>
    <ports>
      <port protocol="tcp" portid="22">
        <state state="open"/>
        <service name="ssh" product="OpenSSH" version="8.9"/>
      </port>
      <port protocol="tcp" portid="80">
        <state state="open"/>
        <service name="http" product="nginx" version="1.24"/>
      </port>
      <port protocol="tcp" portid="443">
        <state state="open"/>
        <service name="https" product="nginx" version="1.24"/>
      </port>
    </ports>
  </host>
</nmaprun>
"""


def _nuclei_findings(host: str) -> str:
    items = [
        {
            "template-id": "tech-detect:nginx",
            "info": {"name": "Nginx detected", "severity": "info"},
            "matched-at": f"https://{host}/",
        },
        {
            "template-id": "ssl-issuer",
            "info": {"name": "Self-signed certificate", "severity": "low"},
            "matched-at": f"https://{host}/",
        },
        {
            "template-id": "exposed-panels:phpmyadmin",
            "info": {
                "name": "phpMyAdmin exposed",
                "severity": "high",
                "classification": {"cve-id": ["CVE-2022-23808"], "cvss-score": 7.2},
            },
            "matched-at": f"https://{host}/phpmyadmin/",
        },
    ]
    return "\n".join(json.dumps(x) for x in items)


def _zap_findings(host: str) -> str:
    return json.dumps(
        {
            "site": [
                {
                    "@host": host,
                    "alerts": [
                        {
                            "name": "Missing X-Frame-Options header",
                            "riskdesc": "Medium",
                            "cweid": "1021",
                            "instances": [{"uri": f"https://{host}/"}],
                            "solution": "Set X-Frame-Options: DENY or SAMEORIGIN.",
                        },
                        {
                            "name": "Cross-Origin Resource Sharing misconfiguration",
                            "riskdesc": "High",
                            "cweid": "942",
                            "instances": [{"uri": f"https://{host}/api"}],
                            "solution": "Restrict Access-Control-Allow-Origin.",
                        },
                    ],
                }
            ]
        }
    )


def _trivy_findings() -> str:
    return json.dumps(
        {
            "Results": [
                {
                    "Target": "image:latest",
                    "Vulnerabilities": [
                        {
                            "VulnerabilityID": "CVE-2024-1234",
                            "PkgName": "openssl",
                            "Severity": "CRITICAL",
                            "Title": "OpenSSL buffer overflow",
                            "CVSS": {"nvd": {"V3Score": 9.8}},
                        },
                        {
                            "VulnerabilityID": "CVE-2024-5678",
                            "PkgName": "libxml2",
                            "Severity": "MEDIUM",
                            "Title": "libxml2 use-after-free",
                            "CVSS": {"nvd": {"V3Score": 5.5}},
                        },
                    ],
                }
            ]
        }
    )


def _checkov_findings() -> str:
    return json.dumps(
        {
            "results": {
                "failed_checks": [
                    {
                        "check_id": "CKV_AWS_20",
                        "bc_check_id": "BC_AWS_S3_19",
                        "check_name": "S3 Bucket has an ACL defined which allows public READ access",
                        "severity": "HIGH",
                        "resource": "aws_s3_bucket.public",
                        "file_path": "/main.tf",
                        "file_line_range": [12, 18],
                        "guideline": "https://docs.bridgecrew.io/docs/s3_1-acl-read-permissions-everyone",
                    }
                ]
            }
        }
    )


def _prowler_findings() -> str:
    return json.dumps(
        [
            {
                "finding_info": {
                    "uid": "prowler-finding-001",
                    "title": "S3 buckets should have versioning enabled",
                    "desc": "All S3 buckets should have versioning enabled to recover from unintended overwrites.",
                },
                "severity": "MEDIUM",
                "compliance": {"CIS-1.5": "2.1.3"},
                "resources": [{"uid": "arn:aws:s3:::demo-bucket"}],
                "cloud": {"region": "us-east-1", "account": {"uid": "123456789012"}},
            }
        ]
    )


def _schemathesis_findings(host: str) -> str:
    return (
        "================================ FAILED: GET /pets ================================\n"
        "1. Test Case ID: 8c8ef3...\n"
        "    Check: not_a_server_error\n"
        '    Body: {"id": -1}\n'
        f"    [Server] {host}\n"
        "================================ FAILED: POST /pets ================================\n"
        "1. Test Case ID: a4c102...\n"
        "    Check: response_schema_conformance\n"
        '    Body: {"name": null}\n'
    )


def _kube_bench_findings() -> str:
    return json.dumps(
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
                                    "test_desc": "Ensure that the --kubelet-certificate-authority argument is set as appropriate",
                                    "status": "FAIL",
                                    "audit": "ps -ef | grep kube-apiserver",
                                    "expected_result": "--kubelet-certificate-authority is set",
                                    "actual_value": "not set",
                                    "remediation": "Edit kube-apiserver manifest and set --kubelet-certificate-authority",
                                    "scored": True,
                                }
                            ]
                        }
                    ],
                }
            ]
        }
    )


_FIXTURES: dict[str, Callable[[str], str] | None] = {
    "nmap": lambda h: _NMAP_XML.format(host=h),
    "nuclei": _nuclei_findings,
    "zap": _zap_findings,
    "trivy": lambda _h: _trivy_findings(),
    "sqlmap": lambda _h: "",
    "checkov": lambda _h: _checkov_findings(),
    "prowler": lambda _h: _prowler_findings(),
    "kube_bench": lambda _h: _kube_bench_findings(),
    "schemathesis": _schemathesis_findings,
}


def _extract_host(argv: list[str]) -> str:
    """Best-effort recovery of the target hostname from a scanner argv."""
    for token in reversed(argv):
        if token.startswith(("http://", "https://")):
            return token.split("://", 1)[1].split("/", 1)[0]
        if token and not token.startswith("-") and "=" not in token:
            return token
    return "example.com"


class MockSandboxRunner:
    """Drop-in replacement for :class:`SandboxRunner` returning canned output."""

    def __init__(self, *, latency_seconds: float = 0.6) -> None:
        self.latency_seconds = latency_seconds

    async def execute(
        self,
        *,
        image: str,
        argv: list[str],
        timeout: int,
        network: bool,
        scanner: str,
        artifacts: list[str] | None = None,
    ) -> SandboxResult:
        del image, network, timeout, artifacts
        await asyncio.sleep(self.latency_seconds + random.uniform(0, 0.4))
        host = _extract_host(argv)
        builder = _FIXTURES.get(scanner)
        stdout = builder(host) if builder else ""
        logger.info(
            "mock_sandbox.executed",
            extra={"scanner": scanner, "argv_len": len(argv), "out_bytes": len(stdout)},
        )
        return SandboxResult(
            exit_code=0,
            stdout=stdout,
            stderr="",
            duration_seconds=self.latency_seconds,
        )

    @staticmethod
    def quote_argv(argv: list[str]) -> str:
        return " ".join(argv)

    @staticmethod
    def normalize_json(payload: Any) -> str:
        return json.dumps(payload, default=str)
