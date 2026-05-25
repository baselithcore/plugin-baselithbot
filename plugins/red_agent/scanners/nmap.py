"""nmap recon scanner adapter.

Profiles tuned for production red-teaming (defined in
:mod:`plugins.red_agent.scanners._nmap_argv`):

* PASSIVE   — low-noise reachability sweep (top 100 TCP, no scripts).
* ACTIVE    — service/version detection + safe NSE categories
              (``default,discovery,version,safe``) over the top 1000 TCP.
* INTRUSIVE — full TCP range with safe vuln-checks (``vuln,auth``) and
              extended version probes. NSE ``exploit``/``dos``/``brute``
              categories are deliberately excluded — they alter state on
              the target and require a separate, explicit RoE flag.

The parser extracts ``<script>`` output (port- and host-level), maps NSE
findings to a real :class:`Severity`, and derives risk for unauth
high-impact services even when no NSE rule fires.
"""

from __future__ import annotations

import json
import re
from typing import Final
from xml.etree.ElementTree import Element

from defusedxml import ElementTree as ET

from plugins.red_agent.models import (
    Finding,
    ScanIntensity,
    Severity,
    Target,
)
from plugins.red_agent.scanners._nmap_argv import (
    PROFILES as _PROFILES,
    build_argv,
    nmap_target as _nmap_target,
)
from plugins.red_agent.scanners.base import Scanner, ScannerKind

# Re-exported so legacy imports (``from .nmap import _PROFILES``) keep
# working without a deprecation cycle. New code should import from
# :mod:`_nmap_argv` directly.
__all__ = ["NmapScanner", "_PROFILES", "_severity_for_script"]

# Services where an *open, unauthenticated* exposure is itself a
# medium-impact misconfiguration on the public internet. NSE may then
# upgrade severity further. Keys are nmap service names (lowercased) or
# explicit port numbers as a fallback.
_HIGH_RISK_SERVICES: Final[frozenset[str]] = frozenset(
    {
        "redis",
        "memcached",
        "mongodb",
        "elasticsearch",
        "kibana",
        "rabbitmq",
        "couchdb",
        "etcd",
        "zookeeper",
        "cassandra",
        "influxdb",
        "kubelet",
        "docker",
        "telnet",
        "rsh",
        "rlogin",
        "vnc",
        "ms-wbt-server",  # rdp
        "microsoft-ds",  # smb 445
        "netbios-ssn",
    }
)
_HIGH_RISK_PORTS: Final[frozenset[int]] = frozenset(
    {
        2375,
        2376,  # docker
        2379,
        2380,  # etcd
        5601,  # kibana
        5900,
        5901,
        5902,  # vnc
        6379,  # redis
        9200,
        9300,  # elasticsearch
        10250,  # kubelet
        11211,  # memcached
        15672,
        25672,  # rabbitmq mgmt
        27017,
        27018,  # mongodb
    }
)

_CVE_RE: Final[re.Pattern[str]] = re.compile(r"CVE-\d{4}-\d{4,7}")
# ``state: VULNERABLE`` is the canonical marker emitted by NSE
# ``vulns`` library when a check confirms a vulnerable host.
_NSE_VULNERABLE_RE: Final[re.Pattern[str]] = re.compile(
    r"\bVULNERABLE\b", re.IGNORECASE
)
_NSE_LIKELY_VULN_RE: Final[re.Pattern[str]] = re.compile(
    r"LIKELY VULNERABLE|POTENTIALLY VULNERABLE", re.IGNORECASE
)


class NmapScanner(Scanner):
    name = "nmap"
    kind = ScannerKind.RECON
    supports_intensity = (
        ScanIntensity.PASSIVE,
        ScanIntensity.ACTIVE,
        ScanIntensity.INTRUSIVE,
    )
    image = "instrumentisto/nmap:latest"
    requires_network = True
    default_timeout = 1200

    async def run(self, target: Target, intensity: ScanIntensity) -> list[Finding]:
        argv = build_argv(target, intensity)
        result = await self.sandbox.execute(
            image=self.image,
            argv=argv,
            timeout=self.timeout,
            network=True,
            scanner=self.name,
        )
        return self._parse(result.stdout, target)

    # Kept as a static method (not just a free function re-export) for
    # backwards compatibility with tests that called
    # ``NmapScanner._nmap_target`` directly.
    @staticmethod
    def _nmap_target(target: Target) -> str:
        return _nmap_target(target)

    def _parse(self, xml_output: str, target: Target) -> list[Finding]:
        findings: list[Finding] = []
        try:
            root = ET.fromstring(xml_output)
        except ET.ParseError:
            return findings

        for host in root.findall("host"):
            addr_el = host.find("address")
            host_addr = addr_el.get("addr") if addr_el is not None else target.value
            findings.extend(self._parse_host(host, host_addr or target.value, target))
        return findings

    def _parse_host(
        self, host: Element, host_addr: str, target: Target
    ) -> list[Finding]:
        out: list[Finding] = []

        for port in host.findall(".//port"):
            state = port.find("state")
            if state is None or state.get("state") != "open":
                continue
            portid = int(port.get("portid", "0"))
            proto = port.get("protocol", "tcp")
            svc = port.find("service")
            svc_name = svc.get("name", "unknown") if svc is not None else "unknown"
            product = svc.get("product") if svc is not None else None
            version = svc.get("version") if svc is not None else None

            out.append(
                self._port_finding(
                    target, host_addr, portid, proto, svc_name, product, version
                )
            )
            for script in port.findall("script"):
                f = self._script_finding(
                    target, host_addr, portid, proto, svc_name, script
                )
                if f is not None:
                    out.append(f)

        for script in host.findall("hostscript/script"):
            f = self._script_finding(target, host_addr, None, None, None, script)
            if f is not None:
                out.append(f)
        return out

    @staticmethod
    def _port_finding(
        target: Target,
        host_addr: str,
        portid: int,
        proto: str,
        svc_name: str,
        product: str | None,
        version: str | None,
    ) -> Finding:
        sev = (
            Severity.MEDIUM
            if svc_name.lower() in _HIGH_RISK_SERVICES or portid in _HIGH_RISK_PORTS
            else Severity.INFO
        )
        return Finding(
            scanner="nmap",
            title=f"Open port {portid}/{proto} ({svc_name})",
            description=(
                f"Service {svc_name} {product or ''} {version or ''} "
                f"exposed on {host_addr}:{portid}/{proto}"
            ).strip(),
            severity=sev,
            target=target.value,
            port=portid,
            service=svc_name,
            evidence={
                "product": product,
                "version": version,
                "protocol": proto,
                "host": host_addr,
            },
            raw=json.loads(json.dumps({"port_id": portid})),
            remediation=(
                "Restrict exposure to authorized networks, enforce "
                "authentication, and patch to the latest stable "
                "version. Treat datastore/admin services on the public "
                "internet as misconfiguration unless explicitly "
                "intended."
                if sev is Severity.MEDIUM
                else "Ensure the exposed service is intentional, "
                "patched, and protected by network ACLs."
            ),
        )

    @staticmethod
    def _script_finding(
        target: Target,
        host_addr: str,
        portid: int | None,
        proto: str | None,
        svc_name: str | None,
        script: Element,
    ) -> Finding | None:
        sid = script.get("id", "")
        output = (script.get("output") or "").strip()
        if not sid or not output:
            return None

        sev = _severity_for_script(sid, output)
        cves = _CVE_RE.findall(output)
        primary_cve = cves[0] if cves else None
        location = f"{host_addr}:{portid}/{proto}" if portid is not None else host_addr
        return Finding(
            scanner="nmap",
            title=f"NSE {sid} on {location}",
            description=(output if len(output) <= 800 else output[:800] + "…"),
            severity=sev,
            cve=primary_cve,
            target=target.value,
            port=portid,
            service=svc_name,
            evidence={
                "nse_script": sid,
                "output": output,
                "host": host_addr,
                "cves": cves,
            },
            raw=json.loads(json.dumps({"nse": sid})),
            remediation=_remediation_for_script(sid, sev),
        )


def _severity_for_script(sid: str, output: str) -> Severity:
    """Map an NSE script id + output to a :class:`Severity`.

    Heuristics, in order of strength:

    1. Output contains ``VULNERABLE`` (case-insensitive) and the script
       id is in the ``vuln`` category → CRITICAL/HIGH.
    2. Output mentions a CVE → HIGH (the enricher pipeline can later
       refine via EPSS/KEV; this is the upper bound at parse time).
    3. ``ssl-*`` weakness scripts (poodle/heartbleed/dh/etc.) → HIGH.
    4. ``ssl-enum-ciphers`` reporting weak grades → MEDIUM.
    5. ``http-vuln-*`` / ``smb-vuln-*`` informational-only output
       (``NOT VULNERABLE``) → INFO.
    6. Default → LOW (information disclosure, fingerprint).
    """
    lo_id = sid.lower()
    is_vuln_script = "-vuln-" in lo_id or lo_id.startswith("vuln")

    if _NSE_VULNERABLE_RE.search(output) and "NOT VULNERABLE" not in output.upper():
        if is_vuln_script:
            return Severity.CRITICAL if _CVE_RE.search(output) else Severity.HIGH
        return Severity.HIGH
    if _NSE_LIKELY_VULN_RE.search(output):
        return Severity.HIGH
    if _CVE_RE.search(output):
        return Severity.HIGH
    if lo_id in {
        "ssl-poodle",
        "ssl-heartbleed",
        "ssl-ccs-injection",
        "ssl-dh-params",
        "ssl-known-key",
    }:
        return Severity.HIGH
    if lo_id == "ssl-enum-ciphers":
        upper = output.upper()
        if any(g in upper for g in ("GRADE: F", "GRADE: D", "GRADE: C")):
            return Severity.MEDIUM
        return Severity.LOW
    if lo_id in {"smb2-security-mode", "smb-security-mode"} and (
        "message_signing: disabled" in output.lower()
    ):
        return Severity.MEDIUM
    if lo_id in {"http-methods"} and "TRACE" in output.upper():
        return Severity.LOW
    if lo_id in {"ftp-anon"} and "anonymous" in output.lower():
        return Severity.MEDIUM
    if "NOT VULNERABLE" in output.upper():
        return Severity.INFO
    return Severity.LOW


def _remediation_for_script(sid: str, sev: Severity) -> str:
    if sev in (Severity.HIGH, Severity.CRITICAL):
        return (
            f"Confirm exposure, patch the affected component, and "
            f"restrict network access. NSE script ``{sid}`` flagged a "
            f"high-impact issue — treat as actionable until verified."
        )
    if sev is Severity.MEDIUM:
        return (
            f"Review the NSE ``{sid}`` output: harden configuration "
            f"(disable weak protocols, enforce auth) and re-scan."
        )
    return (
        f"Information disclosed by NSE ``{sid}``. Reduce surface where "
        f"feasible (banners, verbose errors)."
    )
