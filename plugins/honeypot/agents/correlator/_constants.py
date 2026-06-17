"""Constants for HoneypotCVECorrelator: CWE mappings."""

# CWE to CVE pattern mapping
CWE_TO_ATTACK_PATTERNS = {
    "CWE-89": ["sql_injection", "sqli", "union select"],
    "CWE-78": ["command_injection", "os command", "shell injection"],
    "CWE-79": ["xss", "cross-site scripting", "script injection"],
    "CWE-22": ["path_traversal", "directory traversal", "../"],
    "CWE-307": ["brute_force", "credential stuffing"],
    "CWE-200": ["information_disclosure", "reconnaissance"],
}

# CWE to MITRE ATT&CK Technique Mapping
CWE_TO_MITRE = {
    "CWE-89": ["T1190", "T1059"],  # SQL Injection -> Exploit Public-Facing App
    "CWE-78": ["T1059.004"],  # OS Command Injection -> Unix Shell
    "CWE-79": ["T1059.007"],  # XSS -> JavaScript
    "CWE-22": ["T1083", "T1006"],  # Path Traversal -> File Discovery
    "CWE-307": ["T1110"],  # Brute Force
    "CWE-200": ["T1592", "T1040"],  # Info Disclosure
    "CWE-434": ["T1190", "T1505.003"],  # File Upload -> Web Shell
    "CWE-918": ["T1190"],  # SSRF
}
