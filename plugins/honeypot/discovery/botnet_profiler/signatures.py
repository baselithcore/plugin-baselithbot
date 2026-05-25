"""Malware Signatures Database."""

from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class MalwareSignature:
    """Signature for known malware family identification."""

    family: str
    description: str
    patterns: List[str]  # Regex patterns in payloads/commands
    ports: List[int]  # Common target ports
    protocols: List[str]  # SSH, HTTP, telnet, etc.
    user_agents: List[str]  # HTTP user agents
    default_credentials: List[Tuple[str, str]]  # (username, password)
    keywords: List[str]  # Keywords in payload
    tactics: List[str]  # DDoS, spam, cryptomining, etc.


# Known malware family signatures
MALWARE_SIGNATURES: Dict[str, MalwareSignature] = {
    "mirai": MalwareSignature(
        family="Mirai",
        description="IoT botnet targeting Linux-based devices",
        patterns=[
            r"busybox",
            r"/bin/busybox",
            r"wget\s+http://",
            r"tftp\s+-g",
            r"chmod\s+777",
            r"rm\s+-rf\s+/tmp/",
            r"/dev/null\s+2>&1",
            r"echo\s+-e\s+'\\x",
        ],
        ports=[23, 22, 80, 8080, 2323],
        protocols=["telnet", "ssh"],
        user_agents=[],
        default_credentials=[
            ("root", "root"),
            ("admin", "admin"),
            ("root", ""),
            ("admin", "password"),
            ("root", "vizxv"),
            ("root", "xc3511"),
            ("root", "888888"),
            ("root", "xmhdipc"),
            ("root", "default"),
            ("root", "juantech"),
            ("root", "123456"),
            ("root", "54321"),
            ("support", "support"),
            ("user", "user"),
        ],
        keywords=["mirai", "botnet", "dvrhelper", "nippon", "scanner"],
        tactics=["DDoS", "brute_force", "lateral_movement"],
    ),
    "emotet": MalwareSignature(
        family="Emotet",
        description="Banking trojan and malware loader",
        patterns=[
            r"powershell.*-enc",
            r"powershell.*downloadstring",
            r"\\AppData\\Local\\",
            r"wscript\.shell",
            r"regsvr32",
            r"cmd\.exe\s+/c",
        ],
        ports=[80, 443, 8080, 7080],
        protocols=["http", "https"],
        user_agents=["Mozilla/4.0", "Mozilla/5.0 (compatible;"],
        default_credentials=[],
        keywords=["exe", "dll", "invoice", "payment", "document"],
        tactics=["malware_delivery", "credential_theft", "banking_fraud"],
    ),
    "qakbot": MalwareSignature(
        family="Qakbot",
        description="Banking trojan with worm capabilities",
        patterns=[
            r"wmic\s+",
            r"net\s+view",
            r"net\s+group",
            r"\\windows\\temp\\",
            r"ping\s+-n\s+\d+\s+127\.0\.0\.1",
        ],
        ports=[80, 443, 995, 2222],
        protocols=["http", "https"],
        user_agents=[],
        default_credentials=[],
        keywords=["qbot", "qakbot", "pinkslipbot"],
        tactics=["credential_theft", "lateral_movement", "banking_fraud"],
    ),
    "trickbot": MalwareSignature(
        family="TrickBot",
        description="Modular banking trojan",
        patterns=[
            r"mworm",
            r"tabdll",
            r"mshare",
            r"/imgs/",
            r"\\system32\\cmd\.exe",
        ],
        ports=[80, 443, 447, 449],
        protocols=["http", "https"],
        user_agents=[],
        default_credentials=[],
        keywords=["trick", "anchor"],
        tactics=["credential_theft", "banking_fraud", "ransomware_delivery"],
    ),
    "cryptominer": MalwareSignature(
        family="Cryptominer",
        description="Cryptocurrency mining malware",
        patterns=[
            r"stratum\+tcp://",
            r"xmrig",
            r"minerd",
            r"cpuminer",
            r"nicehash",
            r"--donate-level",
            r"-o\s+.*:\d+",
            r"pool\.",
        ],
        ports=[3333, 4444, 5555, 14444, 45700],
        protocols=["tcp"],
        user_agents=[],
        default_credentials=[],
        keywords=["monero", "xmr", "bitcoin", "btc", "crypto", "miner", "pool"],
        tactics=["cryptomining", "resource_hijacking"],
    ),
    "ddos_agent": MalwareSignature(
        family="DDoS Agent",
        description="Generic DDoS attack tool",
        patterns=[
            r"syn\s+flood",
            r"udp\s+flood",
            r"http\s+flood",
            r"slowloris",
            r"hoic",
            r"loic",
            r"\d+\s+packets",
            r"attack\s+\d+\.\d+\.\d+\.\d+",
        ],
        ports=[80, 443],
        protocols=["tcp", "udp", "http"],
        user_agents=[],
        default_credentials=[],
        keywords=["attack", "flood", "ddos", "dos", "amplification"],
        tactics=["DDoS", "network_disruption"],
    ),
    "cobalt_strike": MalwareSignature(
        family="Cobalt Strike",
        description="Commercial penetration testing tool (often abused)",
        patterns=[
            r"beacon",
            r"powershell.*iex",
            r"whoami\s*/all",
            r"net\s+user\s+/domain",
            r"mimikatz",
            r"sekurlsa",
        ],
        ports=[80, 443, 50050],
        protocols=["http", "https"],
        user_agents=["Mozilla/5.0"],
        default_credentials=[],
        keywords=["beacon", "cobalt", "c2"],
        tactics=["lateral_movement", "credential_theft", "persistence"],
    ),
}
