"""Detection-guidance enricher (purple-team output).

For each finding with a known CWE, attaches a short detection hint
describing the Sigma logsource and pattern most likely to surface the
attack in a SIEM. The output is intentionally compact — one block per
finding under ``evidence["detection_guidance"]`` — so it lives next to
the rest of the enrichment context without bloating the report.

Pure local lookup, no network. Fail-open at the call site.
"""

from __future__ import annotations

from dataclasses import dataclass

from plugins.red_agent.models import Finding


@dataclass(frozen=True)
class DetectionHint:
    """Minimal detection guidance bundle the UI / report can render."""

    logsource: dict[str, str]
    detection: str
    mitigations: tuple[str, ...] = ()


# Curated CWE → detection-guidance map. Conservative coverage: only
# CWEs that have a clear high-confidence detection lane. Reusing the
# CWE root (e.g. CWE-89 covers any sub-class of SQLi) keeps the table
# small without losing recall.
_CWE_TO_HINT: dict[str, DetectionHint] = {
    # SQL injection
    "CWE-89": DetectionHint(
        logsource={"product": "webserver", "category": "webserver"},
        detection=(
            "Look for HTTP requests where query/body parameters carry SQL "
            "tokens such as UNION SELECT, sleep(, benchmark(, OR 1=1, or "
            "stacked queries (`;`) immediately followed by SQL keywords."
        ),
        mitigations=(
            "Parameterized queries / prepared statements",
            "Strict input allowlist on identifiers and ORDER BY columns",
            "Database account least privilege",
        ),
    ),
    # Reflected/stored XSS
    "CWE-79": DetectionHint(
        logsource={"product": "webserver", "category": "webserver"},
        detection=(
            "Detect HTTP request parameters that contain `<script`, "
            "`onerror=`, `javascript:`, or encoded variants reaching "
            "endpoints that render user input."
        ),
        mitigations=(
            "Context-aware output encoding",
            "Strict Content-Security-Policy with no unsafe-inline",
            "Trusted Types where supported",
        ),
    ),
    # OS / shell command injection
    "CWE-78": DetectionHint(
        logsource={"product": "linux", "category": "process_creation"},
        detection=(
            "Process spawned by a webserver / app-server parent (nginx, "
            "uwsgi, gunicorn, java, node) with shell metacharacters "
            "(``;``, ``&&``, ``|``, backticks) in the command line."
        ),
        mitigations=(
            "Use exec-style APIs without shell=True",
            "Allowlist permitted binaries via AppArmor/SELinux",
        ),
    ),
    # Path traversal
    "CWE-22": DetectionHint(
        logsource={"product": "webserver", "category": "webserver"},
        detection=(
            "URL or parameter contains `..%2f`, `..\\`, or absolute file "
            "system paths reaching file-read endpoints."
        ),
        mitigations=(
            "Canonicalize paths and reject `..` segments",
            "Serve static assets via dedicated, chrooted handler",
        ),
    ),
    # Server-Side Request Forgery
    "CWE-918": DetectionHint(
        logsource={"product": "webserver", "category": "webserver"},
        detection=(
            "Outbound connections from app-server processes targeting "
            "RFC1918, link-local (169.254.0.0/16), or cloud metadata IPs "
            "(169.254.169.254, fd00:ec2::254) shortly after an inbound "
            "request carrying a URL parameter."
        ),
        mitigations=(
            "Strict outbound egress allowlist / proxy",
            "IMDSv2 with hop limit = 1 on AWS",
            "Block reserved/private IPs at SSRF boundary",
        ),
    ),
    # Auth bypass / broken access control
    "CWE-285": DetectionHint(
        logsource={"product": "auth", "category": "application"},
        detection=(
            "Privileged action audit events (role grants, admin endpoints) "
            "where the requesting principal does not hold the corresponding "
            "role or session is unauthenticated."
        ),
        mitigations=(
            "Centralized authorization checks at the boundary",
            "Deny-by-default IDOR test in CI",
        ),
    ),
    # Hard-coded / leaked credentials
    "CWE-798": DetectionHint(
        logsource={"product": "linux", "category": "file_event"},
        detection=(
            "Files in repos / containers matching credential patterns "
            "(``AKIA``, ``ghp_``, private keys, JWT signing secrets) and "
            "git push events containing them."
        ),
        mitigations=(
            "Pre-commit secret scanner (gitleaks/trufflehog)",
            "Rotate exposed credentials immediately on detection",
        ),
    ),
    # Vulnerable dependency
    "CWE-1035": DetectionHint(
        logsource={"product": "edr", "category": "process_creation"},
        detection=(
            "Exploitation attempts targeting the affected component: "
            "spike of POST/PUT to its endpoints, abnormal user-agents, "
            "or specific exploit payloads from public PoCs."
        ),
        mitigations=(
            "Patch / upgrade the affected dependency",
            "Virtual-patch via WAF rule until rollout",
        ),
    ),
    # Weak / outdated TLS
    "CWE-326": DetectionHint(
        logsource={"product": "tls", "category": "network"},
        detection=(
            "TLS handshakes negotiating SSLv3, TLS1.0/1.1, or "
            "weak/export ciphers (RC4, DES, NULL, EXPORT)."
        ),
        mitigations=(
            "Disable TLS < 1.2 server-side",
            "Move to ECDHE + AES-GCM/CHACHA20 cipher suites",
        ),
    ),
    # XXE / external entity
    "CWE-611": DetectionHint(
        logsource={"product": "webserver", "category": "webserver"},
        detection=(
            "Inbound XML payloads containing ``<!DOCTYPE`` with ``ENTITY`` "
            "declarations, especially referencing ``SYSTEM`` or ``file://``."
        ),
        mitigations=(
            "Disable DOCTYPE processing in XML parsers",
            "Use defusedxml / equivalent hardened parser",
        ),
    ),
}


class SigmaHintEnricher:
    """Annotate findings with detection guidance derived from CWE.

    Output shape under ``finding.evidence['detection_guidance']``::

        {
          "logsource": {"product": "...", "category": "..."},
          "detection": "<text>",
          "mitigations": ["...", "..."],
        }
    """

    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled

    def enrich(self, findings: list[Finding]) -> list[Finding]:
        if not self.enabled or not findings:
            return findings
        for f in findings:
            if not f.cwe or not isinstance(f.evidence, dict):
                continue
            hint = _CWE_TO_HINT.get(f.cwe.upper())
            if hint is None:
                continue
            f.evidence["detection_guidance"] = {
                "logsource": dict(hint.logsource),
                "detection": hint.detection,
                "mitigations": list(hint.mitigations),
            }
        return findings
