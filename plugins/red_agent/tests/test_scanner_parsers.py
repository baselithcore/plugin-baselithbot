"""Parser tests for scanner adapters (no sandbox dependency)."""

from __future__ import annotations

import pytest

from plugins.red_agent.models import ScanIntensity, Severity, Target, TargetType
from plugins.red_agent.scanners._nmap_argv import (
    DANGEROUS_NSE_CATEGORIES,
    SAFE_NSE_CATEGORIES,
    build_argv,
)
from plugins.red_agent.scanners.nmap import (
    _PROFILES,
    NmapScanner,
    _severity_for_script,
)
from plugins.red_agent.scanners.nuclei import NucleiScanner
from plugins.red_agent.scanners.trivy import TrivyScanner


class _StubSandbox:
    def __init__(self) -> None:
        self.calls: list[dict] = []


@pytest.fixture()
def target_url() -> Target:
    return Target(type=TargetType.URL, value="http://example.com")


def test_nmap_parses_open_port(target_url: Target) -> None:
    xml = """<?xml version="1.0"?>
<nmaprun>
  <host><address addr="93.184.216.34"/>
    <ports>
      <port portid="443" protocol="tcp">
        <state state="open"/>
        <service name="https" product="nginx" version="1.25"/>
      </port>
    </ports>
  </host>
</nmaprun>"""
    s = NmapScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]
    findings = s._parse(xml, target_url)
    assert len(findings) == 1
    assert findings[0].port == 443
    assert findings[0].severity == Severity.INFO


def test_nmap_high_risk_service_promoted_to_medium(target_url: Target) -> None:
    xml = """<?xml version="1.0"?>
<nmaprun>
  <host><address addr="10.0.0.5"/>
    <ports>
      <port portid="6379" protocol="tcp">
        <state state="open"/>
        <service name="redis"/>
      </port>
    </ports>
  </host>
</nmaprun>"""
    s = NmapScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]
    findings = s._parse(xml, target_url)
    assert len(findings) == 1
    assert findings[0].severity == Severity.MEDIUM
    assert findings[0].service == "redis"


def test_nmap_extracts_nse_vuln_with_cve(target_url: Target) -> None:
    xml = """<?xml version="1.0"?>
<nmaprun>
  <host><address addr="10.0.0.7"/>
    <ports>
      <port portid="445" protocol="tcp">
        <state state="open"/>
        <service name="microsoft-ds"/>
        <script id="smb-vuln-ms17-010" output="VULNERABLE: Remote Code Execution vulnerability in Microsoft SMBv1 servers (ms17-010) State: VULNERABLE References: CVE-2017-0143"/>
      </port>
    </ports>
  </host>
</nmaprun>"""
    s = NmapScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]
    findings = s._parse(xml, target_url)
    titles = [f.title for f in findings]
    assert any("Open port 445" in t for t in titles)
    nse = next(f for f in findings if "smb-vuln-ms17-010" in f.title)
    assert nse.severity == Severity.CRITICAL
    assert nse.cve == "CVE-2017-0143"
    assert nse.evidence["nse_script"] == "smb-vuln-ms17-010"


def test_nmap_nse_not_vulnerable_stays_info(target_url: Target) -> None:
    xml = """<?xml version="1.0"?>
<nmaprun>
  <host><address addr="10.0.0.8"/>
    <ports>
      <port portid="80" protocol="tcp">
        <state state="open"/>
        <service name="http"/>
        <script id="http-vuln-cve2017-5638" output="NOT VULNERABLE"/>
      </port>
    </ports>
  </host>
</nmaprun>"""
    s = NmapScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]
    findings = s._parse(xml, target_url)
    nse = [f for f in findings if "http-vuln" in f.title]
    assert nse and nse[0].severity == Severity.INFO


def test_nmap_ssl_enum_weak_grade_medium(target_url: Target) -> None:
    xml = """<?xml version="1.0"?>
<nmaprun>
  <host><address addr="10.0.0.9"/>
    <ports>
      <port portid="443" protocol="tcp">
        <state state="open"/>
        <service name="https"/>
        <script id="ssl-enum-ciphers" output="TLSv1.0:   ciphers:    weak  Least strength: D  Grade: D"/>
      </port>
    </ports>
  </host>
</nmaprun>"""
    s = NmapScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]
    findings = s._parse(xml, target_url)
    nse = next(f for f in findings if "ssl-enum-ciphers" in f.title)
    assert nse.severity == Severity.MEDIUM


def test_nmap_host_level_script_parsed(target_url: Target) -> None:
    xml = """<?xml version="1.0"?>
<nmaprun>
  <host><address addr="10.0.0.10"/>
    <hostscript>
      <script id="smb-os-discovery" output="OS: Windows 7 Service Pack 1"/>
    </hostscript>
  </host>
</nmaprun>"""
    s = NmapScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]
    findings = s._parse(xml, target_url)
    assert any(f.title.startswith("NSE smb-os-discovery") for f in findings)


def test_nmap_supports_all_intensities() -> None:
    s = NmapScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]
    for intensity in ScanIntensity:
        assert s.supports(intensity)


def test_nmap_intrusive_profile_includes_vuln_scripts() -> None:
    intrusive = _PROFILES[ScanIntensity.INTRUSIVE]
    assert "vuln" in intrusive and "auth" in intrusive
    assert "-p-" in intrusive
    # Exploitation/DoS/brute categories must NOT be enabled by default.
    assert "exploit" not in intrusive
    assert ",dos" not in intrusive and "dos," not in intrusive
    assert "brute" not in intrusive


def test_nmap_active_profile_uses_safe_categories_only() -> None:
    active = _PROFILES[ScanIntensity.ACTIVE]
    assert "-sV" in active and "default,discovery,version,safe" in active
    assert "vuln" not in active and "exploit" not in active


def test_severity_for_script_likely_vulnerable_high() -> None:
    assert (
        _severity_for_script(
            "http-vuln-cve2014-3704", "LIKELY VULNERABLE: SQL injection"
        )
        == Severity.HIGH
    )


def test_severity_for_script_ftp_anon_medium() -> None:
    assert (
        _severity_for_script("ftp-anon", "Anonymous FTP login allowed (FTP code 230)")
        == Severity.MEDIUM
    )


def test_argv_default_active_profile_target_url(target_url: Target) -> None:
    argv = build_argv(target_url, ScanIntensity.ACTIVE)
    # URL must be reduced to hostname.
    assert argv[-1] == "example.com"
    # Safe categories present, no exploit/brute/dos.
    script_idx = argv.index("--script")
    cats = argv[script_idx + 1].split(",")
    assert {"default", "discovery", "version", "safe"}.issubset(cats)
    assert not (DANGEROUS_NSE_CATEGORIES & set(cats))


def test_argv_extra_safe_category_merged(target_url: Target) -> None:
    target_url.metadata["nmap"] = {"extra_scripts": ["auth"]}
    argv = build_argv(target_url, ScanIntensity.ACTIVE)
    cats = argv[argv.index("--script") + 1].split(",")
    assert "auth" in cats and "default" in cats
    # SAFE_NSE_CATEGORIES sanity — auth must be in the allowlist.
    assert "auth" in SAFE_NSE_CATEGORIES


def test_argv_dangerous_category_dropped_when_active(target_url: Target) -> None:
    target_url.metadata["nmap"] = {
        "extra_scripts": ["exploit", "brute"],
        "allow_dangerous_categories": True,
    }
    argv = build_argv(target_url, ScanIntensity.ACTIVE)
    cats = argv[argv.index("--script") + 1].split(",")
    assert "exploit" not in cats and "brute" not in cats


def test_argv_dangerous_category_requires_explicit_consent(
    target_url: Target,
) -> None:
    target_url.metadata["nmap"] = {"extra_scripts": ["exploit"]}
    argv = build_argv(target_url, ScanIntensity.INTRUSIVE)
    cats = argv[argv.index("--script") + 1].split(",")
    assert "exploit" not in cats


def test_argv_dangerous_category_allowed_at_intrusive_with_consent(
    target_url: Target,
) -> None:
    target_url.metadata["nmap"] = {
        "extra_scripts": ["exploit", "brute"],
        "allow_dangerous_categories": True,
    }
    argv = build_argv(target_url, ScanIntensity.INTRUSIVE)
    cats = argv[argv.index("--script") + 1].split(",")
    assert "exploit" in cats and "brute" in cats


def test_argv_port_spec_override_replaces_top_ports(target_url: Target) -> None:
    target_url.metadata["nmap"] = {"port_spec": "1-1024,3306,5432"}
    argv = build_argv(target_url, ScanIntensity.ACTIVE)
    # --top-ports + value removed, -p <spec> appended.
    assert "--top-ports" not in argv
    assert argv[argv.index("-p") + 1] == "1-1024,3306,5432"


def test_argv_port_spec_invalid_dropped(target_url: Target) -> None:
    # Shell-metacharacter injection attempt — must be rejected.
    target_url.metadata["nmap"] = {"port_spec": "80;rm -rf /"}
    argv = build_argv(target_url, ScanIntensity.ACTIVE)
    assert "80;rm" not in argv
    # Default ACTIVE selector preserved.
    assert "--top-ports" in argv


def test_argv_version_intensity_override(target_url: Target) -> None:
    target_url.metadata["nmap"] = {"version_intensity": 9}
    argv = build_argv(target_url, ScanIntensity.ACTIVE)
    assert argv[argv.index("--version-intensity") + 1] == "9"


def test_argv_version_intensity_ignored_at_passive(target_url: Target) -> None:
    target_url.metadata["nmap"] = {"version_intensity": 9}
    argv = build_argv(target_url, ScanIntensity.PASSIVE)
    assert "--version-intensity" not in argv


def test_argv_specific_script_id_allowed(target_url: Target) -> None:
    target_url.metadata["nmap"] = {"extra_scripts": ["http-title"]}
    argv = build_argv(target_url, ScanIntensity.ACTIVE)
    cats = argv[argv.index("--script") + 1].split(",")
    assert "http-title" in cats


def test_argv_specific_script_id_metachar_rejected(target_url: Target) -> None:
    target_url.metadata["nmap"] = {"extra_scripts": ["http;ls"]}
    argv = build_argv(target_url, ScanIntensity.ACTIVE)
    cats = argv[argv.index("--script") + 1].split(",")
    assert "http;ls" not in cats


def test_nmap_ignores_non_open_ports(target_url: Target) -> None:
    xml = """<?xml version="1.0"?>
<nmaprun>
  <host><address addr="10.0.0.11"/>
    <ports>
      <port portid="22" protocol="tcp">
        <state state="filtered"/>
        <service name="ssh"/>
      </port>
    </ports>
  </host>
</nmaprun>"""
    s = NmapScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]
    assert s._parse(xml, target_url) == []


def test_nuclei_parses_jsonl(target_url: Target) -> None:
    line = (
        '{"info":{"name":"XSS","severity":"high","description":"reflected xss",'
        '"classification":{"cwe-id":["CWE-79"],"cvss-score":7.5}},'
        '"matched-at":"http://example.com/?q=<script>"}'
    )
    s = NucleiScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]
    findings = s._parse(line, target_url)
    assert len(findings) == 1
    assert findings[0].severity == Severity.HIGH
    assert findings[0].cvss_score == 7.5
    assert findings[0].cwe == "CWE-79"


def test_trivy_parses_vuln() -> None:
    payload = (
        '{"Results":[{"Vulnerabilities":[{"VulnerabilityID":"CVE-2024-1234",'
        '"PkgName":"requests","Severity":"HIGH","InstalledVersion":"2.30.0",'
        '"FixedVersion":"2.32.0","Description":"RCE",'
        '"CVSS":{"nvd":{"V3Score":8.1}}}]}]}'
    )
    repo_target = Target(type=TargetType.REPO, value="github.com/foo/bar")
    s = TrivyScanner(sandbox=_StubSandbox())  # type: ignore[arg-type]
    findings = s._parse(payload, repo_target)
    assert len(findings) == 1
    assert findings[0].severity == Severity.HIGH
    assert findings[0].cve == "CVE-2024-1234"
    assert findings[0].cvss_score == 8.1


@pytest.mark.parametrize("intensity", list(ScanIntensity))
def test_intensity_enum_round_trip(intensity: ScanIntensity) -> None:
    assert ScanIntensity(intensity.value) is intensity
