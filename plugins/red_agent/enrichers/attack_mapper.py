"""CWE → MITRE ATT&CK technique mapper enricher.

Annotates each finding's ``evidence`` with the most likely ATT&CK
technique IDs derived from the CWE. The mapping is a curated subset
based on the official MITRE CWE/CAPEC → ATT&CK published cross-references
(https://attack.mitre.org/resources/relationships/) and the OWASP Top 10
mapping. Coverage is intentionally conservative: when a CWE has no
canonical mapping the enricher is a no-op for that finding.

Pure local lookup — no network, no external dependencies. Always safe to
run; never raises.
"""

from __future__ import annotations

from plugins.red_agent.models import Finding


# Curated CWE -> ATT&CK techniques. Format: technique-id, technique-name.
# Source: MITRE ATT&CK Enterprise (v15+), CWE-CAPEC-ATTACK relationships,
# and OWASP Top 10:2021 ↔ ATT&CK alignment.
_CWE_TO_ATTACK: dict[str, list[tuple[str, str]]] = {
    # Injection
    "CWE-79": [("T1059.007", "Command and Scripting Interpreter: JavaScript")],
    "CWE-89": [("T1190", "Exploit Public-Facing Application")],
    "CWE-77": [("T1059", "Command and Scripting Interpreter")],
    "CWE-78": [("T1059", "Command and Scripting Interpreter")],
    "CWE-91": [("T1190", "Exploit Public-Facing Application")],
    "CWE-94": [("T1059", "Command and Scripting Interpreter")],
    "CWE-95": [("T1059", "Command and Scripting Interpreter")],
    "CWE-611": [("T1190", "Exploit Public-Facing Application")],
    # Broken Access Control
    "CWE-22": [("T1083", "File and Directory Discovery")],
    "CWE-284": [("T1078", "Valid Accounts")],
    "CWE-285": [("T1078", "Valid Accounts")],
    "CWE-639": [("T1078", "Valid Accounts")],
    "CWE-862": [("T1078", "Valid Accounts")],
    "CWE-863": [("T1078", "Valid Accounts")],
    # Authentication / credentials
    "CWE-287": [("T1078", "Valid Accounts")],
    "CWE-306": [("T1078", "Valid Accounts")],
    "CWE-307": [("T1110", "Brute Force")],
    "CWE-521": [("T1110", "Brute Force")],
    "CWE-798": [("T1552.001", "Unsecured Credentials: Credentials In Files")],
    "CWE-256": [("T1552", "Unsecured Credentials")],
    "CWE-522": [("T1552", "Unsecured Credentials")],
    # Cryptography / TLS
    "CWE-326": [("T1040", "Network Sniffing")],
    "CWE-327": [("T1040", "Network Sniffing")],
    "CWE-295": [("T1557", "Adversary-in-the-Middle")],
    "CWE-523": [("T1557", "Adversary-in-the-Middle")],
    # Information disclosure
    "CWE-200": [("T1083", "File and Directory Discovery")],
    "CWE-209": [("T1592", "Gather Victim Host Information")],
    "CWE-538": [("T1083", "File and Directory Discovery")],
    "CWE-532": [("T1552.001", "Unsecured Credentials: Credentials In Files")],
    # SSRF / open redirect
    "CWE-918": [("T1090", "Proxy")],
    "CWE-601": [("T1566.002", "Phishing: Spearphishing Link")],
    # Misconfig / supply chain
    "CWE-1021": [("T1185", "Browser Session Hijacking")],
    "CWE-829": [("T1195", "Supply Chain Compromise")],
    "CWE-915": [("T1195", "Supply Chain Compromise")],
    "CWE-1104": [
        ("T1195.002", "Supply Chain Compromise: Compromise Software Supply Chain")
    ],
    # Deserialization / file upload
    "CWE-502": [("T1190", "Exploit Public-Facing Application")],
    "CWE-434": [("T1505.003", "Server Software Component: Web Shell")],
    # DoS
    "CWE-400": [("T1499", "Endpoint Denial of Service")],
    "CWE-770": [("T1499", "Endpoint Denial of Service")],
    # Vulnerable component (CVE-bearing) — generic exploitation path
    "CWE-1035": [("T1190", "Exploit Public-Facing Application")],
    "CWE-1330": [
        ("T1195.002", "Supply Chain Compromise: Compromise Software Supply Chain")
    ],
    # Recon (open ports / leaked info)
    "CWE-430": [("T1592.002", "Gather Victim Host Information: Software")],
}


class AttackMapperEnricher:
    """Annotate findings with MITRE ATT&CK technique IDs derived from CWE.

    The mapper is enabled by default and pure-local; the ``enabled`` flag
    exists only to let operators turn it off if they prefer scanner-native
    output.
    """

    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled

    def enrich(self, findings: list[Finding]) -> list[Finding]:
        if not self.enabled or not findings:
            return findings
        for f in findings:
            if not f.cwe:
                continue
            mapping = _CWE_TO_ATTACK.get(f.cwe.upper())
            if not mapping:
                continue
            if not isinstance(f.evidence, dict):
                continue
            f.evidence["attack_techniques"] = [
                {"id": tid, "name": tname} for tid, tname in mapping
            ]
        return findings
