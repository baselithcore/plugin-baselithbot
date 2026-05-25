"""Zero-Day Detector Constants."""

# Known exploit patterns (for baseline comparison)
KNOWN_PATTERNS = {
    # SQL Injection variants
    "sql_injection": [
        r"(?i)(union\s+select|or\s+1\s*=\s*1|'\s*or\s*'|--\s*$)",
        r"(?i)(select\s+.*\s+from|insert\s+into|update\s+.*\s+set)",
        r"(?i)(drop\s+table|truncate\s+table|delete\s+from)",
    ],
    # Command Injection
    "command_injection": [
        r"[;&|`$]\s*(cat|ls|id|whoami|uname|pwd)",
        r"(?i)(;|\||&&)\s*(nc|netcat|bash|sh|curl|wget)",
        r"\$\((.*)\)|\`(.*)\`",
    ],
    # Path Traversal
    "path_traversal": [
        r"\.\./\.\./",
        r"(?i)(\.\./|\.\.\\){3,}",
        r"(?i)/etc/(passwd|shadow|hosts)",
    ],
    # Remote Code Execution
    "rce": [
        r"(?i)(eval|exec|system|passthru|shell_exec)\s*\(",
        r"(?i)base64_decode\s*\(",
        r"(?i)\$\{.*\}",  # JNDI/Log4j style
    ],
    # XSS
    "xss": [
        r"<script[^>]*>",
        r"(?i)javascript:",
        r"(?i)on(error|load|click|mouse)\s*=",
    ],
    # Buffer Overflow indicators
    "buffer_overflow": [
        r"(?:\\x[0-9a-fA-F]{2}){10,}",  # Long hex sequences
        r"A{100,}",  # Long repeated chars
        r"(?i)(?:%[0-9a-f]{2}){10,}",  # URL-encoded shellcode
    ],
    # Deserialization attacks
    "deserialization": [
        r"(?i)java\.lang\.Runtime",
        r"(?i)rO0AB",  # Java serialized object
        r"(?i)O:\d+:\"[^\"]+\"",  # PHP serialized
    ],
    # SSRF
    "ssrf": [
        r"(?i)(http|https|ftp|gopher|dict)://",
        r"(?i)@(127\.0\.0\.1|localhost|0\.0\.0\.0)",
        r"(?i)file:///",
    ],
}

# Shellcode signatures (common patterns)
SHELLCODE_PATTERNS = [
    r"\\x90{4,}",  # NOP sled
    r"\\xcc",  # INT3 breakpoint
    r"\\xeb.\\xe8",  # JMP/CALL pattern
    r"\\x31\\xc0",  # XOR EAX, EAX
    r"\\x68.{4}\\xff\\xd",  # PUSH/CALL pattern
]

# Built-in CVE pattern checks
DEFAULT_CVE_PATTERNS = {
    "CVE-2021-44228": [r"(?i)\$\{jndi:", r"(?i)\$\{lower:"],  # Log4j
    "CVE-2017-5638": [r"(?i)content-type.*ognl"],  # Struts
    "CVE-2019-11510": [r"(?i)/dana-na/"],  # Pulse VPN
    "CVE-2021-26855": [r"(?i)/ecp/"],  # Exchange ProxyLogon
    "CVE-2021-22986": [r"(?i)/mgmt/tm/"],  # F5 BIG-IP
    "CVE-2020-5902": [r"(?i)/hsqldb"],  # F5 BIG-IP
    "CVE-2021-21972": [r"(?i)/ui/vropspluginui/"],  # VMware vCenter
    "CVE-2020-14882": [r"(?i)/console/"],  # WebLogic
}

# Common obfuscation techniques
OBFUSCATION_INDICATORS = [
    r"(?i)base64",
    r"(?i)chr\(\d+\)",  # chr() encoding
    r"(?i)fromcharcode",  # JS encoding
    r"(?:\\x[0-9a-f]{2}){5,}",  # Hex encoding
    r"(?i)rot13",
    r"(?i)gzinflate|gzuncompress",
    r"\+\s*\+",  # String concatenation obfuscation
]
