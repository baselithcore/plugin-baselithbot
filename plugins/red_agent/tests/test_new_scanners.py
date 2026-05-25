"""Parser tests for the new enterprise scanners (no sandbox dependency)."""

from __future__ import annotations

import pytest

from plugins.red_agent.models import ScanIntensity, Severity, Target, TargetType
from plugins.red_agent.scanners.gitleaks import GitleaksScanner
from plugins.red_agent.scanners.secure_headers import SecureHeadersScanner
from plugins.red_agent.scanners.semgrep import SemgrepScanner
from plugins.red_agent.scanners.sslyze import SslyzeScanner
from plugins.red_agent.scanners.syft_grype import GrypeScanner, SyftScanner


class _StubSandbox:
    pass


@pytest.fixture()
def url_target() -> Target:
    return Target(type=TargetType.URL, value="https://example.com")


@pytest.fixture()
def repo_target() -> Target:
    return Target(type=TargetType.REPO, value="/work/repo")


def test_sslyze_flags_legacy_protocols(url_target: Target) -> None:
    payload = """
    {
      "server_scan_results": [
        {
          "scan_result": {
            "tls_1_0_cipher_suites": {
              "result": {
                "accepted_cipher_suites": [
                  {"cipher_suite": {"name": "TLS_RSA_WITH_AES_128_CBC_SHA"}}
                ]
              }
            },
            "tls_1_3_cipher_suites": {"result": {"accepted_cipher_suites": []}},
            "http_headers": {"result": {"strict_transport_security_header": null}}
          }
        }
      ]
    }
    """
    s = SslyzeScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]
    findings = s._parse(payload, url_target)
    titles = [f.title for f in findings]
    assert any("TLS 1 0" in t for t in titles)
    assert any("HSTS header missing" in t for t in titles)
    assert any("TLS 1.3 not enabled" in t for t in titles)


def test_sslyze_flags_weak_cipher(url_target: Target) -> None:
    payload = """
    {
      "server_scan_results": [
        {
          "scan_result": {
            "tls_1_2_cipher_suites": {
              "result": {
                "accepted_cipher_suites": [
                  {"cipher_suite": {"name": "TLS_RSA_WITH_RC4_128_SHA"}}
                ]
              }
            },
            "tls_1_3_cipher_suites": {
              "result": {
                "accepted_cipher_suites": [
                  {"cipher_suite": {"name": "TLS_AES_256_GCM_SHA384"}}
                ]
              }
            },
            "http_headers": {
              "result": {
                "strict_transport_security_header": {"max_age": 63072000}
              }
            }
          }
        }
      ]
    }
    """
    s = SslyzeScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]
    findings = s._parse(payload, url_target)
    titles = [f.title for f in findings]
    assert any("Weak cipher suite" in t for t in titles)
    assert not any("HSTS header missing" in t for t in titles)
    assert not any("TLS 1.3 not enabled" in t for t in titles)


def test_secure_headers_flags_missing(url_target: Target) -> None:
    raw = "HTTP/1.1 200 OK\r\nServer: nginx/1.25\r\nContent-Type: text/html\r\n\r\n"
    s = SecureHeadersScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]
    findings = s._parse(raw, url_target, "https://example.com/")
    titles = [f.title for f in findings]
    assert any(
        "Missing security header: strict-transport-security" in t for t in titles
    )
    assert any("Missing security header: content-security-policy" in t for t in titles)
    assert any("Information-disclosure header present: server" in t for t in titles)


def test_secure_headers_csp_unsafe_inline(url_target: Target) -> None:
    raw = (
        "HTTP/1.1 200 OK\r\n"
        "Strict-Transport-Security: max-age=63072000\r\n"
        "X-Content-Type-Options: nosniff\r\n"
        "X-Frame-Options: DENY\r\n"
        "Referrer-Policy: strict-origin\r\n"
        "Permissions-Policy: geolocation=()\r\n"
        "Cross-Origin-Opener-Policy: same-origin\r\n"
        "Cross-Origin-Resource-Policy: same-site\r\n"
        "Content-Security-Policy: default-src 'self'; script-src 'self' 'unsafe-inline'\r\n"
        "\r\n"
    )
    s = SecureHeadersScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]
    findings = s._parse(raw, url_target, "https://example.com/")
    titles = [f.title for f in findings]
    assert any("CSP allows unsafe-inline" in t for t in titles)
    assert any("CSP missing frame-ancestors" in t for t in titles)


def test_secure_headers_extracts_last_redirect_block() -> None:
    raw = (
        "HTTP/1.1 301 Moved\r\n"
        "Location: https://final.example/\r\n"
        "\r\n"
        "HTTP/1.1 200 OK\r\n"
        "Strict-Transport-Security: max-age=63072000\r\n"
        "\r\n"
    )
    headers = SecureHeadersScanner._extract_last_response_headers(raw)
    assert "strict-transport-security" in headers
    assert "location" not in headers


def test_semgrep_parses_match(repo_target: Target) -> None:
    payload = (
        '{"results":[{"check_id":"python.lang.security.audit.path-traversal",'
        '"path":"app.py","start":{"line":42,"col":1},'
        '"extra":{"severity":"ERROR","message":"path traversal sink",'
        '"metadata":{"cwe":["CWE-22: Path Traversal"],'
        '"owasp":"A01:2021","category":"security"},'
        '"lines":"open(user_path)"}}]}'
    )
    s = SemgrepScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]
    findings = s._parse(payload, repo_target)
    assert len(findings) == 1
    assert findings[0].cwe == "CWE-22"
    assert findings[0].severity == Severity.HIGH
    assert findings[0].endpoint == "app.py"


def test_gitleaks_parses_leak(repo_target: Target) -> None:
    payload = (
        '[{"RuleID":"aws-key","Description":"AWS Access Key",'
        '"File":"src/config.py","StartLine":7,"Match":"AKIAEXAMPLE",'
        '"Secret":"AKIAEXAMPLE12345","Commit":"abc123","Author":"alice"}]'
    )
    s = GitleaksScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]
    findings = s._parse(payload, repo_target)
    assert len(findings) == 1
    assert findings[0].cwe == "CWE-798"
    assert findings[0].severity == Severity.HIGH
    assert findings[0].evidence["redacted_secret"].startswith("AKIA")
    assert "AKIAEXAMPLE12345" not in str(findings[0].raw)


def test_gitleaks_redacts_short_secret() -> None:
    s = GitleaksScanner
    assert s._redact("abcd") == "****"
    assert s._redact("abcdefgh12345") == "abcd*****2345"


def test_syft_aggregates_packages(repo_target: Target) -> None:
    payload = (
        '{"spdxVersion":"SPDX-2.3","packages":['
        '{"name":"requests","versionInfo":"2.32.0","licenseConcluded":"Apache-2.0"},'
        '{"name":"flask","versionInfo":"3.0.0","licenseConcluded":"BSD-3-Clause"}]}'
    )
    s = SyftScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]
    findings = s._parse(payload, repo_target)
    assert len(findings) == 1
    assert findings[0].evidence["package_count"] == 2
    assert findings[0].severity == Severity.INFO


def test_grype_parses_match(repo_target: Target) -> None:
    payload = (
        '{"matches":[{"vulnerability":{"id":"CVE-2024-1234",'
        '"severity":"High","description":"RCE in lib",'
        '"fix":{"versions":["1.2.3"],"state":"fixed"},'
        '"cvss":[{"metrics":{"baseScore":8.1}}],'
        '"advisories":[{"link":"https://example/adv"}]},'
        '"artifact":{"name":"libfoo","version":"1.0.0","type":"python"}}]}'
    )
    s = GrypeScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]
    findings = s._parse(payload, repo_target)
    assert len(findings) == 1
    assert findings[0].cve == "CVE-2024-1234"
    assert findings[0].cvss_score == 8.1
    assert findings[0].severity == Severity.HIGH
    assert "Upgrade `libfoo`" in (findings[0].remediation or "")


def test_new_scanners_registered() -> None:
    from plugins.red_agent.scanners import REGISTRY

    for name in (
        "sslyze",
        "secure_headers",
        "semgrep",
        "gitleaks",
        "syft",
        "grype",
    ):
        assert name in REGISTRY, f"{name} missing from REGISTRY"


def test_intensity_supports() -> None:
    assert ScanIntensity.PASSIVE in SslyzeScanner.supports_intensity
    assert ScanIntensity.PASSIVE in SemgrepScanner.supports_intensity
